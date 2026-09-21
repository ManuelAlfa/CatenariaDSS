from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

# ---------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------
def normalizar_fecha(fecha_str: Optional[str]) -> Optional[str]:
    if not fecha_str:
        return None

    fecha_str = fecha_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(fecha_str, fmt).strftime("%Y%m%d")
        except ValueError:
            continue

    return None


def _validar_obligatorios(tramo: Optional[str], via: Optional[str]) -> None:
    if not tramo:
        raise ValueError("El tramo es obligatorio")
    if not via:
        raise ValueError("La vía es obligatoria")


def _validar_rango_km(pto_km_ini: Optional[float], pto_km_fin: Optional[float]) -> None:
    if pto_km_ini is None or pto_km_fin is None:
        return

    if float(pto_km_fin) < float(pto_km_ini):
        raise ValueError("El punto km fin no puede ser menor que el punto km inicio")


def _validar_rango_fechas(fecha_inicio: Optional[str], fecha_fin: Optional[str]) -> None:
    if not fecha_inicio or not fecha_fin:
        return

    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    # Si alguna fecha no se puede normalizar, se mantiene el comportamiento actual
    # (el filtro de esa fecha no se aplica).
    if not f_ini or not f_fin:
        return

    if f_fin < f_ini:
        raise ValueError("La fecha fin no puede ser menor que la fecha inicio")


def _construir_where_y_params(
    alias: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    pto_km_ini: Optional[float] = None,
    pto_km_fin: Optional[float] = None,
) -> Tuple[str, Dict[str, Any]]:

    _validar_rango_km(pto_km_ini, pto_km_fin)
    _validar_rango_fechas(fecha_inicio, fecha_fin)

    filtros = [f"{alias}.id_tramo = $tramo", f"{alias}.id_via = $via"]
    params: Dict[str, Any] = {"tramo": tramo, "via": via}

    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    if f_ini:
        filtros.append(f"{alias}.fecha >= $fecha_inicio")
        params["fecha_inicio"] = f_ini

    if f_fin:
        filtros.append(f"{alias}.fecha <= $fecha_fin")
        params["fecha_fin"] = f_fin

    if pto_km_ini is not None:
        filtros.append(f"{alias}.pto_km >= $pto_km_ini")
        params["pto_km_ini"] = float(pto_km_ini)

    if pto_km_fin is not None:
        filtros.append(f"{alias}.pto_km <= $pto_km_fin")
        params["pto_km_fin"] = float(pto_km_fin)

    return " AND ".join(filtros), params

# Normaliza clausula_FROM para poder reutilizarla en FROM/JOIN sin duplicar 'FROM'
def _keyspace_prefix(clausula_FROM: str) -> str:
    """Devuelve el prefijo `bucket`.`scope`. (con punto final) sin la palabra FROM.
    Ejemplos de entrada válidos:
      - 'FROM `MyBucket`.`MyScope`.'
      - '`MyBucket`.`MyScope`.'
    """
    s = (clausula_FROM or "").strip()
    if not s:
        return ""
    if s.upper().startswith("FROM "):
        s = s[5:].strip()
    # Asegura que termina en punto
    if not s.endswith("."):
        s = s + "."
    return s


def contar_resultados_consulta(
    cluster,
    clausula_FROM: str,
    tipo_busqueda: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    pto_km_ini: Optional[float] = None,
    pto_km_fin: Optional[float] = None,
) -> int:
    """Cuenta cuántos resultados devolvería una búsqueda sin traer todo el detalle."""
    _validar_obligatorios(tramo, via)
    _validar_rango_km(pto_km_ini, pto_km_fin)
    _validar_rango_fechas(fecha_inicio, fecha_fin)

    tipo = (tipo_busqueda or "").strip().lower()

    if tipo == "mediciones":
        where_clause, params = _construir_where_y_params(
            "m", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT COUNT(1) AS total
        {clausula_FROM}`Medicion_Individual` AS m
        WHERE {where_clause};
        """

    elif tipo == "inspecciones":
        filtros = ["a.id_tramo = $tramo", "a.id_via = $via"]
        params: Dict[str, Any] = {"tramo": tramo, "via": via}

        f_ini = normalizar_fecha(fecha_inicio)
        f_fin = normalizar_fecha(fecha_fin)

        if f_ini:
            filtros.append("a.fecha >= $fecha_inicio")
            params["fecha_inicio"] = f_ini

        if f_fin:
            filtros.append("a.fecha <= $fecha_fin")
            params["fecha_fin"] = f_fin

        if pto_km_ini is not None:
            filtros.append("TO_NUMBER(a.num_km) >= $pto_km_ini")
            params["pto_km_ini"] = float(pto_km_ini)

        if pto_km_fin is not None:
            filtros.append("TO_NUMBER(a.num_km) <= $pto_km_fin")
            params["pto_km_fin"] = float(pto_km_fin)

        where_clause = " AND ".join(filtros)
        where_clause += f" AND (a.tipo IS MISSING OR LOWER(a.tipo) NOT IN {TIPOS_FORMULARIO_N1QL})"

        query = f"""
        SELECT COUNT(1) AS total
        {clausula_FROM}`Actuaciones` AS a
        WHERE {where_clause};
        """

    elif tipo == "formularios":
        where_clause, params = _construir_where_y_params(
            "f", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT COUNT(1) AS total
        {clausula_FROM}`Formularios` AS f
        WHERE {where_clause};
        """

    elif tipo == "incidencias":
        where_clause, params = _construir_where_y_params(
            "i", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT COUNT(1) AS total
        FROM (
            SELECT 1
            {clausula_FROM}`Incidencias` AS i
            WHERE {where_clause}
            GROUP BY i.id_tramo, i.id_via, i.pto_km, i.fecha, i.hora
        ) AS grupos;
        """

    else:
        raise ValueError(f"Tipo de búsqueda no soportado: {tipo_busqueda}")

    rows = [dict(r) for r in cluster.query(query, **params).rows()]
    if not rows:
        return 0

    return int(rows[0].get("total", 0) or 0)


def consulta_supera_limite(
    cluster,
    clausula_FROM: str,
    tipo_busqueda: str,
    tramo: str,
    via: str,
    limite: int,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    pto_km_ini: Optional[float] = None,
    pto_km_fin: Optional[float] = None,
) -> bool:
    """Devuelve True si la consulta potencial supera el limite indicado."""
    _validar_obligatorios(tramo, via)
    _validar_rango_km(pto_km_ini, pto_km_fin)
    _validar_rango_fechas(fecha_inicio, fecha_fin)

    tipo = (tipo_busqueda or "").strip().lower()
    limite_check = int(limite) + 1

    if tipo == "mediciones":
        where_clause, params = _construir_where_y_params(
            "m", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT RAW 1
        {clausula_FROM}`Medicion_Individual` AS m
        WHERE {where_clause}
        LIMIT $limite_check;
        """

    elif tipo == "inspecciones":
        filtros = ["a.id_tramo = $tramo", "a.id_via = $via"]
        params: Dict[str, Any] = {"tramo": tramo, "via": via}

        f_ini = normalizar_fecha(fecha_inicio)
        f_fin = normalizar_fecha(fecha_fin)

        if f_ini:
            filtros.append("a.fecha >= $fecha_inicio")
            params["fecha_inicio"] = f_ini

        if f_fin:
            filtros.append("a.fecha <= $fecha_fin")
            params["fecha_fin"] = f_fin

        if pto_km_ini is not None:
            filtros.append("TO_NUMBER(a.num_km) >= $pto_km_ini")
            params["pto_km_ini"] = float(pto_km_ini)

        if pto_km_fin is not None:
            filtros.append("TO_NUMBER(a.num_km) <= $pto_km_fin")
            params["pto_km_fin"] = float(pto_km_fin)

        where_clause = " AND ".join(filtros)
        where_clause += f" AND (a.tipo IS MISSING OR LOWER(a.tipo) NOT IN {TIPOS_FORMULARIO_N1QL})"

        query = f"""
        SELECT RAW 1
        {clausula_FROM}`Actuaciones` AS a
        WHERE {where_clause}
        LIMIT $limite_check;
        """

    elif tipo == "formularios":
        where_clause, params = _construir_where_y_params(
            "f", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT RAW 1
        {clausula_FROM}`Formularios` AS f
        WHERE {where_clause}
        LIMIT $limite_check;
        """

    elif tipo == "incidencias":
        where_clause, params = _construir_where_y_params(
            "i", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
        )
        query = f"""
        SELECT RAW 1
        {clausula_FROM}`Incidencias` AS i
        WHERE {where_clause}
        GROUP BY i.id_tramo, i.id_via, i.pto_km, i.fecha, i.hora
        LIMIT $limite_check;
        """

    else:
        raise ValueError(f"Tipo de búsqueda no soportado: {tipo_busqueda}")

    params["limite_check"] = limite_check
    rows = [r for r in cluster.query(query, **params).rows()]
    return len(rows) > int(limite)


# ======================================================
#   1) MEDICIONES
# ======================================================
def buscar_mediciones(
    cluster,
    clausula_FROM: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    pto_km_ini: Optional[float] = None,
    pto_km_fin: Optional[float] = None,
) -> List[Dict[str, Any]]:

    _validar_obligatorios(tramo, via)

    where_clause, params = _construir_where_y_params(
        "m", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
    )

    query = f"""
    SELECT META(m).id AS doc_id, m.*,
        (
            SELECT RAW META(i).id
            {clausula_FROM}`Incidencias` AS i
            WHERE i.id_tramo = m.id_tramo
              AND i.id_via = m.id_via
              AND i.pto_km = m.pto_km
              AND i.fecha = m.fecha
              AND i.hora = m.hora
        ) AS incidencias_ids
    {clausula_FROM}`Medicion_Individual` AS m
    WHERE {where_clause}
    ORDER BY m.fecha, m.hora;
    """

    return [dict(r) for r in cluster.query(query, **params).rows()]


def buscar_medicion_por_clave(
    cluster, clausula_FROM, id_tramo, id_via, pto_km, fecha, hora
):
    query = f"""
    SELECT META(m).id AS doc_id, m.*
    {clausula_FROM}`Medicion_Individual` AS m
    WHERE m.id_tramo=$id_tramo AND m.id_via=$id_via
      AND m.pto_km=$pto_km AND m.fecha=$fecha AND m.hora=$hora
    LIMIT 1;
    """
    rows = cluster.query(
        query,
        id_tramo=id_tramo,
        id_via=id_via,
        pto_km=float(pto_km),
        fecha=fecha,
        hora=hora,
    ).rows()

    for r in rows:
        return dict(r)
    return None


# ======================================================
#   2) INSPECCIONES
# ======================================================
TIPOS_FORMULARIO_N1QL = "['poleas','conductores','postes']"

def buscar_inspecciones(
    cluster, clausula_FROM, tramo, via,
    fecha_inicio=None, fecha_fin=None,
    pto_km_ini=None, pto_km_fin=None
):
    _validar_obligatorios(tramo, via)
    _validar_rango_km(pto_km_ini, pto_km_fin)
    _validar_rango_fechas(fecha_inicio, fecha_fin)

    # ⚠️ No usamos _construir_where_y_params aquí porque filtra por a.pto_km
    filtros = ["a.id_tramo = $tramo", "a.id_via = $via"]
    params: Dict[str, Any] = {"tramo": tramo, "via": via}

    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    if f_ini:
        filtros.append("a.fecha >= $fecha_inicio")
        params["fecha_inicio"] = f_ini

    if f_fin:
        filtros.append("a.fecha <= $fecha_fin")
        params["fecha_fin"] = f_fin

    # ✅ En Actuaciones (inspecciones) el PK es num_km
    if pto_km_ini is not None:
        filtros.append("TO_NUMBER(a.num_km) >= $pto_km_ini")
        params["pto_km_ini"] = float(pto_km_ini)

    if pto_km_fin is not None:
        filtros.append("TO_NUMBER(a.num_km) <= $pto_km_fin")
        params["pto_km_fin"] = float(pto_km_fin)

    where_clause = " AND ".join(filtros)

    # Mantienes el filtro para excluir formularios
    where_clause += f" AND (a.tipo IS MISSING OR LOWER(a.tipo) NOT IN {TIPOS_FORMULARIO_N1QL})"

    query = f"""
    SELECT META(a).id AS doc_id, a.*
    {clausula_FROM}`Actuaciones` AS a
    WHERE {where_clause}
    ORDER BY a.fecha DESC, a.hora DESC;
    """

    resultados = [dict(r) for r in cluster.query(query, **params).rows()]

    for row in resultados:
        raw = row.get("num_errores", 0)
        try:
            row["num_errores"] = int(raw) if raw not in (None, "") else 0
        except (TypeError, ValueError):
            row["num_errores"] = 0

    return resultados


# ======================================================
#   3) FORMULARIOS
# ======================================================
def buscar_formularios(
    cluster, clausula_FROM, tramo, via,
    fecha_inicio=None, fecha_fin=None,
    pto_km_ini=None, pto_km_fin=None
):
    _validar_obligatorios(tramo, via)

    where_clause, params = _construir_where_y_params(
        "f", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
    )

    query = f"""
    SELECT META(f).id AS doc_id, f.*
    {clausula_FROM}`Formularios` AS f
    WHERE {where_clause}
    ORDER BY f.fecha DESC;
    """

    return [dict(r) for r in cluster.query(query, **params).rows()]


# ======================================================
#   4) INCIDENCIAS
# ======================================================
def buscar_incidencias(
    cluster, clausula_FROM, tramo, via,
    fecha_inicio=None, fecha_fin=None,
    pto_km_ini=None, pto_km_fin=None
):
    _validar_obligatorios(tramo, via)

    where_clause, params = _construir_where_y_params(
        "i", tramo, via, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin
    )

    query = f"""
    SELECT META(i).id AS doc_id, i.*
    {clausula_FROM}`Incidencias` AS i
    WHERE {where_clause}
    ORDER BY i.fecha DESC, i.hora DESC;
    """

    return [dict(r) for r in cluster.query(query, **params).rows()]


def buscar_incidencias_por_medicion(
    cluster, clausula_FROM, id_tramo, id_via, pto_km, fecha, hora
):
    query = f"""
    SELECT META(i).id AS doc_id, i.*
    {clausula_FROM}`Incidencias` AS i
    WHERE i.id_tramo=$id_tramo AND i.id_via=$id_via
      AND i.pto_km=$pto_km AND i.fecha=$fecha AND i.hora=$hora
    ORDER BY i.nivel DESC;
    """

    return [
        dict(r)
        for r in cluster.query(
            query,
            id_tramo=id_tramo,
            id_via=id_via,
            pto_km=float(pto_km),
            fecha=fecha,
            hora=hora,
        ).rows()
    ]


def buscar_incidencia_por_doc_id(cluster, clausula_FROM, doc_id):
    query = f"""
    SELECT META(i).id AS doc_id, i.*
    {clausula_FROM}`Incidencias` AS i
    USE KEYS $doc_id;
    """
    rows = cluster.query(query, doc_id=doc_id).rows()
    for r in rows:
        return dict(r)
    return None


def buscar_incidencias_agrupadas(
    cluster,
    clausula_FROM: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    pto_km_ini: Optional[float] = None,
    pto_km_fin: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Devuelve incidencias agrupadas por (tramo, vía, pto_km, fecha, hora)
    e indica si existe una medición relacionada (tiene_medicion) y su doc_id (medicion_doc_id).
    """
    _validar_obligatorios(tramo, via)
    _validar_rango_km(pto_km_ini, pto_km_fin)
    _validar_rango_fechas(fecha_inicio, fecha_fin)

    # Normaliza prefijo de keyspace: `Bucket`.`Scope`.
    ks = _keyspace_prefix(clausula_FROM)
    if not ks:
        raise ValueError("clausula_FROM no puede estar vacía")

    condiciones = ["i.id_tramo = $tramo", "i.id_via = $via"]
    params: Dict[str, Any] = {"tramo": tramo, "via": via}

    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    if f_ini:
        condiciones.append("i.fecha >= $fecha_inicio")
        params["fecha_inicio"] = f_ini

    if f_fin:
        condiciones.append("i.fecha <= $fecha_fin")
        params["fecha_fin"] = f_fin

    if pto_km_ini is not None:
        condiciones.append("i.pto_km >= $pto_km_ini")
        params["pto_km_ini"] = float(pto_km_ini)

    if pto_km_fin is not None:
        condiciones.append("i.pto_km <= $pto_km_fin")
        params["pto_km_fin"] = float(pto_km_fin)

    where_clause = " AND ".join(condiciones)

    # Nota N1QL:
    # - FROM <keyspace>  (no "FROM FROM")
    # - LEFT JOIN <keyspace> (no "LEFT JOIN FROM")
    query = f"""
    SELECT
        i.id_tramo,
        i.id_via,
        i.pto_km,
        i.fecha,
        i.hora,

        COUNT(1) AS num_incidencias,
        MAX(i.coordenadas_GPS) AS coordenadas_GPS,

        /* hay medición relacionada a ese (tramo,vía,pk,fecha,hora) */
        MAX(m IS NOT MISSING) AS tiene_medicion,
        MAX(META(m).id)       AS medicion_doc_id,

        ARRAY_AGG({{
            "nivel": i.nivel,
            "poste": i.poste,
            "tipo": i.tipo,
            "subtipo": i.subtipo,
            "valor_medido": i.valor_medido,
            "valor_referencia": i.valor_referencia,
            "coordenadas_GPS": i.coordenadas_GPS,
            "revision": i.revision,
            "revision_fecha": i.revision_fecha
        }}) AS incidencias

    FROM {ks}`Incidencias` AS i

    LEFT JOIN {ks}`Medicion_Individual` AS m
        ON  m.id_tramo = i.id_tramo
        AND m.id_via   = i.id_via
        AND m.pto_km   = i.pto_km
        AND m.fecha    = i.fecha
        AND REPLACE(m.hora, ".", ":") = REPLACE(i.hora, ".", ":")

    WHERE {where_clause}

    GROUP BY
        i.id_tramo,
        i.id_via,
        i.pto_km,
        i.fecha,
        i.hora

    ORDER BY
        i.fecha DESC,
        REPLACE(i.hora, ".", ":") DESC
    """

    # Debug opcional (ASCII-safe para Windows)
    print("QUERY INCIDENCIAS - VERSION FINAL OK")
    print("QUERY FINAL:\n", query)

    result = cluster.query(query, **params)
    return [dict(row) for row in result.rows()]

