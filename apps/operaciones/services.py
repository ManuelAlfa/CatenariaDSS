# operaciones_service.py

from typing import List, Dict, Any, Optional
from couchbase.exceptions import DocumentNotFoundException, DocumentExistsException



def obtener_partes(cluster, clausula_FROM: str) -> List[str]:
    """
    Devuelve las partes disponibles (conductores, postes, poleas, ...).
    """
    q = f"""
        SELECT DISTINCT m.parte
        {clausula_FROM}`Maestro_Operaciones` m
        WHERE m.parte IS NOT MISSING AND m.parte IS NOT NULL
        ORDER BY m.parte;
    """
    return [row["parte"] for row in cluster.query(q).rows()]


def obtener_grupos_por_parte(cluster, parte: str, clausula_FROM: str) -> List[Dict[str, Any]]:
    """
    Devuelve los grupos (id, nombre) de una parte.
    """
    q = f"""
        SELECT DISTINCT g.id AS id, g.nombre AS nombre
        {clausula_FROM}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        WHERE m.parte = $parte
        ORDER BY TO_NUMBER(g.id), g.nombre;
    """
    res = cluster.query(q, parte=parte).rows()
    return [{"id": r.get("id"), "nombre": r.get("nombre")} for r in res]


def obtener_subgrupos(cluster, parte: str, id_grupo: str, clausula_FROM: str,
                      filtro_codigo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Devuelve los subgrupos (codigo, descripcion) de un grupo dentro de una parte.
    Permite filtrar por 'codigo' (LIKE).
    """
    where_filtro = " AND LOWER(s.codigo) LIKE LOWER($like)" if filtro_codigo else ""
    params = {"parte": parte, "id_grupo": id_grupo}
    if filtro_codigo:
        params["like"] = f"%{filtro_codigo}%"

    q = f"""
        SELECT g.id AS id_grupo, g.nombre AS nombre_grupo,
               s.codigo AS codigo, s.descripcion AS descripcion
        {clausula_FROM}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        UNNEST g.subgrupos AS s
        WHERE m.parte = $parte
          AND g.id = $id_grupo
          {where_filtro}
        ORDER BY TO_NUMBER(s.codigo), s.codigo;
    """
    return [dict(r) for r in cluster.query(q, **params).rows()]


def obtener_todas_operaciones(cluster, clausula_FROM: str,
                              filtro_codigo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Devuelve TODAS las operaciones (subgrupos) aplanadas con su contexto:
    [{parte, id_grupo, nombre_grupo, codigo, descripcion}, ...]

    Permite filtrar por 'codigo' (LIKE, case-insensitive).
    Útil para la vista "ver todas las operaciones" que muestra el catálogo
    completo sin tener que seleccionar parte y grupo.
    """
    where_filtro = " WHERE LOWER(s.codigo) LIKE LOWER($like)" if filtro_codigo else ""
    params: Dict[str, Any] = {}
    if filtro_codigo:
        params["like"] = f"%{filtro_codigo}%"

    q = f"""
        SELECT m.parte           AS parte,
               g.id              AS id_grupo,
               g.nombre          AS nombre_grupo,
               s.codigo          AS codigo,
               s.descripcion     AS descripcion
        {clausula_FROM}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        UNNEST g.subgrupos AS s
        {where_filtro}
        ORDER BY m.parte, TO_NUMBER(g.id), g.id, TO_NUMBER(s.codigo), s.codigo;
    """
    return [dict(r) for r in cluster.query(q, **params).rows()]


def _clausula_from(bucket_name: str, scope_name: str) -> str:
    return f"FROM `{bucket_name}`.`{scope_name}`."


def existe_subgrupo(cluster, bucket_name: str, scope_name: str,
                    parte: str, id_grupo: str, codigo: str) -> bool:
    """
    Devuelve True si existe un subgrupo con ese código dentro de (parte, grupo).
    Usa .rows() (QueryResult no es iterador).
    """
    q = f"""
        SELECT COUNT(1) AS n
        {_clausula_from(bucket_name, scope_name)}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        UNNEST g.subgrupos AS s
        WHERE m.parte = $parte AND g.id = $id_grupo AND s.codigo = $codigo;
    """
    rows = list(cluster.query(q, parte=parte, id_grupo=id_grupo, codigo=codigo).rows())
    n = rows[0].get("n", 0) if rows else 0
    return (n or 0) > 0


def existe_grupo(cluster, bucket_name: str, scope_name: str,
                 parte: str, id_grupo: str) -> bool:
    """Devuelve True si existe un grupo con ese id dentro de la parte indicada."""
    q = f"""
        SELECT COUNT(1) AS n
        {_clausula_from(bucket_name, scope_name)}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        WHERE m.parte = $parte AND g.id = $id_grupo;
    """
    rows = list(cluster.query(q, parte=parte, id_grupo=id_grupo).rows())
    n = rows[0].get("n", 0) if rows else 0
    return (n or 0) > 0


def existe_grupo_global(cluster, bucket_name: str, scope_name: str,
                        id_grupo: str) -> bool:
    """Devuelve True si existe un grupo con ese id en CUALQUIER parte."""
    q = f"""
        SELECT COUNT(1) AS n
        {_clausula_from(bucket_name, scope_name)}`Maestro_Operaciones` m
        UNNEST m.grupos AS g
        WHERE g.id = $id_grupo;
    """
    rows = list(cluster.query(q, id_grupo=id_grupo).rows())
    n = rows[0].get("n", 0) if rows else 0
    return (n or 0) > 0


def existe_parte(cluster, bucket_name: str, scope_name: str, parte: str) -> bool:
    """Devuelve True si existe el documento Maestro_Operaciones para esa parte."""
    q = f"""
        SELECT COUNT(1) AS n
        {_clausula_from(bucket_name, scope_name)}`Maestro_Operaciones` m
        WHERE m.parte = $parte;
    """
    rows = list(cluster.query(q, parte=parte).rows())
    n = rows[0].get("n", 0) if rows else 0
    return (n or 0) > 0


def crear_grupo(cluster, bucket_name: str, scope_name: str,
                parte: str, id_grupo: str, nombre: str) -> None:
    """
    Inserta un nuevo grupo (sin subgrupos) al final del array 'grupos' de la
    parte indicada. Valida que la parte exista y que no haya un grupo con ese
    mismo id en esa parte.
    """
    parte = (parte or "").strip()
    id_grupo = (id_grupo or "").strip()
    nombre = (nombre or "").strip()
    if not parte:
        raise ValueError("La parte es obligatoria.")
    if not id_grupo:
        raise ValueError("El id del grupo es obligatorio.")
    if not nombre:
        raise ValueError("El nombre del grupo es obligatorio.")

    if not existe_parte(cluster, bucket_name, scope_name, parte):
        raise ValueError(f"La parte '{parte}' no existe en Maestro_Operaciones.")

    if existe_grupo_global(cluster, bucket_name, scope_name, id_grupo):
        raise DocumentExistsException(
            f"Ya existe un grupo con id '{id_grupo}' en el catálogo de operaciones."
        )

    q = f"""
        UPDATE `{bucket_name}`.`{scope_name}`.`Maestro_Operaciones` AS m
        SET m.grupos = ARRAY_APPEND(
            COALESCE(m.grupos, []),
            {{"id": $id_grupo, "nombre": $nombre, "subgrupos": []}}
        )
        WHERE m.parte = $parte;
    """
    cluster.query(q, parte=parte, id_grupo=id_grupo, nombre=nombre).rows()


def crear_subgrupo(cluster, bucket_name: str, scope_name: str,
                   parte: str, id_grupo: str, codigo: str, descripcion: str):
    """
    Inserta un nuevo subgrupo al final del array 'subgrupos' del grupo.
    """
    if existe_subgrupo(cluster, bucket_name, scope_name, parte, id_grupo, codigo):
        raise ValueError("El código ya existe en ese grupo.")

    q = f"""
        UPDATE `{bucket_name}`.`{scope_name}`.`Maestro_Operaciones` AS m
        SET g.subgrupos = ARRAY_APPEND(g.subgrupos, {{"codigo": $codigo, "descripcion": $descripcion}})
        FOR g IN m.grupos WHEN g.id = $id_grupo END
        WHERE m.parte = $parte;
    """
    cluster.query(q, parte=parte, id_grupo=id_grupo, codigo=codigo, descripcion=descripcion).rows()


def actualizar_subgrupo(cluster, bucket_name: str, scope_name: str,
                        parte: str, id_grupo: str,
                        codigo_original: str, codigo: str, descripcion: str):
    """
    Actualiza código y/o descripción de un subgrupo.
    """
    if codigo != codigo_original and existe_subgrupo(cluster, bucket_name, scope_name, parte, id_grupo, codigo):
        raise ValueError("Ya existe otro subgrupo con ese código en el grupo.")

    q = f"""
        UPDATE `{bucket_name}`.`{scope_name}`.`Maestro_Operaciones` AS m
        SET g.subgrupos = ARRAY
              CASE WHEN v.codigo = $codigo_original
                   THEN {{"codigo": $codigo, "descripcion": $descripcion}}
                   ELSE v END
            FOR v IN g.subgrupos END
        FOR g IN m.grupos WHEN g.id = $id_grupo END
        WHERE m.parte = $parte;
    """
    cluster.query(q, parte=parte, id_grupo=id_grupo,
                  codigo_original=codigo_original, codigo=codigo, descripcion=descripcion).rows()


def eliminar_subgrupo(cluster, bucket_name: str, scope_name: str,
                      parte: str, id_grupo: str, codigo: str):
    """
    Elimina el subgrupo cuyo 'codigo' coincida.
    """
    q = f"""
        UPDATE `{bucket_name}`.`{scope_name}`.`Maestro_Operaciones` AS m
        SET g.subgrupos = ARRAY v FOR v IN g.subgrupos WHEN v.codigo != $codigo END
        FOR g IN m.grupos WHEN g.id = $id_grupo END
        WHERE m.parte = $parte;
    """
    cluster.query(q, parte=parte, id_grupo=id_grupo, codigo=codigo).rows()
