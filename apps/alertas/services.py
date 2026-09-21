from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List


def _ks(clausula_from: str) -> str:
    s = (clausula_from or "").strip()
    if s.upper().startswith("FROM "):
        s = s[5:].strip()
    if not s.endswith("."):
        s += "."
    return s


def contar_alertas_pendientes(cluster, clausula_from: str) -> int:
    """Cuenta incidencias de nivel 3 o 4 que no han sido revisadas."""
    total, _ = contar_alertas_resumen(cluster, clausula_from)
    return total


def contar_alertas_resumen(cluster, clausula_from: str) -> tuple:
    """
    Devuelve (total_incidencias, total_fechas_distintas) en una sola query.
    Evita dos round-trips al cluster para obtener ambos conteos.
    """
    ks = _ks(clausula_from)
    query = f"""
    SELECT COUNT(1) AS total_inc,
           COUNT(DISTINCT i.fecha) AS total_fechas
    FROM {ks}`Incidencias` AS i
    WHERE (i.nivel = 3 OR i.nivel = 4)
      AND (i.revision IS MISSING OR i.revision = false)
      AND i.fecha IS NOT MISSING
    """
    try:
        rows = list(cluster.query(query).rows())
        if rows:
            row = rows[0]
            return int(row.get("total_inc", 0)), int(row.get("total_fechas", 0))
        return 0, 0
    except Exception:
        return 0, 0


def contar_fechas_alertas(cluster, clausula_from: str) -> int:
    """Cuenta el número de fechas distintas con incidencias nivel 3/4 pendientes."""
    _, total_fechas = contar_alertas_resumen(cluster, clausula_from)
    return total_fechas


POR_PAGINA_ALERTAS = 20


def buscar_alertas_agrupadas(
    cluster,
    clausula_from: str,
    pagina: int = 1,
    por_pagina: int = POR_PAGINA_ALERTAS,
) -> List[Dict[str, Any]]:
    """
    Devuelve incidencias de nivel 3/4 pendientes de revisión,
    agrupadas por fecha (desc) y dentro de cada fecha por tramo+vía.
    Paginado: devuelve `por_pagina` fechas a partir de la página indicada.
    Una sola query N1QL con subquery para evitar dos round-trips.
    """
    ks = _ks(clausula_from)
    offset = (max(1, pagina) - 1) * por_pagina

    query = f"""
    SELECT
        META(i).id   AS doc_id,
        i.id_tramo,
        i.id_via,
        i.fecha,
        i.hora,
        i.pto_km,
        i.nivel,
        i.poste,
        i.tipo,
        i.subtipo,
        i.valor_medido,
        i.valor_referencia,
        i.coordenadas_GPS,
        i.revision,
        i.revision_fecha
    FROM {ks}`Incidencias` AS i
    WHERE i.fecha IN (
        SELECT RAW sub.fecha
        FROM (
            SELECT DISTINCT i2.fecha
            FROM {ks}`Incidencias` AS i2
            WHERE (i2.nivel = 3 OR i2.nivel = 4)
              AND (i2.revision IS MISSING OR i2.revision = false)
              AND i2.fecha IS NOT MISSING
            ORDER BY i2.fecha DESC
            LIMIT {por_pagina} OFFSET {offset}
        ) AS sub
    )
    AND (i.nivel = 3 OR i.nivel = 4)
    AND (i.revision IS MISSING OR i.revision = false)
    ORDER BY i.fecha DESC, i.id_tramo, i.id_via, i.hora
    """
    try:
        rows = [dict(r) for r in cluster.query(query).rows()]
    except Exception:
        return []

    if not rows:
        return []

    # Preservar el orden de fechas de la subquery (desc)
    fechas_vistas: List[str] = []
    por_fecha: Dict[str, Dict[str, Dict[str, Any]]] = OrderedDict()
    for row in rows:
        fecha = row.get("fecha") or "—"
        if fecha not in por_fecha:
            por_fecha[fecha] = OrderedDict()
            fechas_vistas.append(fecha)
        tramo = row.get("id_tramo") or "—"
        via   = row.get("id_via") or "—"
        clave = f"{tramo}|{via}"
        if clave not in por_fecha[fecha]:
            por_fecha[fecha][clave] = {
                "id_tramo": tramo,
                "id_via": via,
                "incidencias": [],
            }
        por_fecha[fecha][clave]["incidencias"].append(row)

    result = []
    for fecha in fechas_vistas:
        tv = por_fecha[fecha]
        tramos = []
        for grupo in tv.values():
            grupo["incidencias"].sort(
                key=lambda i: int(i.get("nivel") or 0), reverse=True
            )
            tramos.append(grupo)
        result.append({"fecha": fecha, "tramos": tramos})
    return result


def marcar_revision_incidencia(
    cluster,
    bucket_name: str,
    scope_name: str,
    doc_id: str,
    revisado: bool,
) -> None:
    """
    Actualiza el campo revision (y revision_fecha) de una incidencia
    y recalcula NAlertas en las actuaciones asociadas (mismo tramo/vía/fecha).
    """
    coll_inc = cluster.bucket(bucket_name).scope(scope_name).collection("Incidencias")
    doc = coll_inc.get(doc_id).content_as[dict]

    doc["revision"] = revisado
    if revisado:
        doc["revision_fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        doc.pop("revision_fecha", None)
    coll_inc.replace(doc_id, doc)

    id_tramo = doc.get("id_tramo")
    id_via = doc.get("id_via")
    fecha = doc.get("fecha")
    if id_tramo and id_via and fecha:
        _recalcular_nalertas(cluster, bucket_name, scope_name, id_tramo, id_via, fecha)


def _recalcular_nalertas(
    cluster,
    bucket_name: str,
    scope_name: str,
    id_tramo: str,
    id_via: str,
    fecha: str,
) -> None:
    """Recalcula y persiste NAlertas en las actuaciones del tramo/vía/fecha dado."""
    ks = f"`{bucket_name}`.`{scope_name}`."

    count_query = f"""
    SELECT COUNT(1) AS total
    FROM {ks}`Incidencias` AS i
    WHERE i.id_tramo = $tramo AND i.id_via = $via AND i.fecha = $fecha
      AND (i.nivel = 3 OR i.nivel = 4)
      AND (i.revision IS MISSING OR i.revision = false)
    """
    try:
        count_rows = list(
            cluster.query(count_query, tramo=id_tramo, via=id_via, fecha=fecha).rows()
        )
        n_alertas = int(count_rows[0].get("total", 0)) if count_rows else 0
    except Exception:
        return

    act_query = f"""
    SELECT META(a).id AS doc_id, a.*
    FROM {ks}`Actuaciones` AS a
    WHERE a.id_tramo = $tramo AND a.id_via = $via AND a.fecha = $fecha
    """
    try:
        act_rows = [
            dict(r)
            for r in cluster.query(act_query, tramo=id_tramo, via=id_via, fecha=fecha).rows()
        ]
    except Exception:
        return

    coll_act = cluster.bucket(bucket_name).scope(scope_name).collection("Actuaciones")
    for row in act_rows:
        act_doc_id = row.pop("doc_id", None)
        if act_doc_id:
            row["NAlertas"] = n_alertas
            try:
                coll_act.replace(act_doc_id, row)
            except Exception:
                pass
