from typing import Optional, Dict, Any, List
from datetime import datetime

# Lista válida para usar en N1QL (IMPORTANTE: sintaxis EXACTA)
TIPOS_FORMULARIO_N1QL = "['poleas','conductores','postes']"


# ---------------------------------------------------------
# Normaliza fechas: de 'YYYY-MM-DD' -> 'YYYYMMDD'
# ---------------------------------------------------------
def normalizar_fecha(fecha_str: Optional[str]) -> Optional[str]:
    if not fecha_str:
        return None
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").strftime("%Y%m%d")
    except Exception:
        return fecha_str


# ---------------------------------------------------------
#   INDICADORES DE OPERATIVA (Inspecciones, Formularios, Km, Errores)
# ---------------------------------------------------------
def obtener_indicadores_operativa(
    cluster,
    clausula_FROM: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
) -> Dict[str, Any]:

    # Normalización de fechas al formato de Couchbase
    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    # Filtros obligatorios y opcionales
    filtros = [
        "a.id_tramo = $tramo",
        "a.id_via   = $via"
    ]

    if f_ini:
        filtros.append("a.fecha >= $fecha_inicio")
    if f_fin:
        filtros.append("a.fecha <= $fecha_fin")

    where_clause = " AND ".join(filtros)

    # ---------------------------------------------------------
    #  QUERY N1QL FINAL (SINTAXIS 100% CORRECTA)
    # ---------------------------------------------------------
    query = f"""
        SELECT
            /* Inspecciones: actuaciones que NO son poleas/conductores/postes */
                SUM(
                    CASE
                        WHEN a.tipo_formulario IS MISSING
                        OR LOWER(a.tipo_formulario) NOT IN ['poleas','conductores','postes']
                        THEN 1
                        ELSE 0
                    END
                ) AS inspecciones,

            /* Km = suma total de num_km */
            COALESCE(SUM(a.num_km), 0) AS km,

            /* Formularios = tipo_formulario en poleas/conductores/postes */
            COALESCE(
                SUM(
                    CASE
                        WHEN a.tipo_formulario IS NOT MISSING
                         AND LOWER(a.tipo_formulario) IN {TIPOS_FORMULARIO_N1QL}
                        THEN 1
                        ELSE 0
                    END
                ),
            0) AS formularios,

            /* Errores = suma total num_errores */
            COALESCE(SUM(a.num_errores), 0) AS errores

        {clausula_FROM}`Actuaciones` a
        WHERE {where_clause};
    """

    # Parámetros de la query
    params = {
        "tramo": tramo,
        "via": via,
        "fecha_inicio": f_ini,
        "fecha_fin": f_fin
    }

    print("\n🟦 [DEBUG] Ejecutando Indicadores Operativa")
    print("QUERY:", query)
    print("PARAMS:", params)

    try:
        rows = list(cluster.query(query, **{k: v for k, v in params.items() if v is not None}).rows())
        print("RESULTADO:", rows)
    except Exception as e:
        print("❌ ERROR Query Indicadores Operativa:", e)
        raise

    if not rows:
        return {"inspecciones": 0, "formularios": 0, "km": 0.0, "errores": 0}

    fila = rows[0]

    return {
        "inspecciones": int(fila.get("inspecciones") or 0),
        "formularios": int(fila.get("formularios") or 0),
        "km": float(fila.get("km") or 0.0),
        "errores": int(fila.get("errores") or 0),
    }

# ---------------------------------------------------------
#   DETALLE DE INSPECCIONES (si algún día se usa en tablas)
# ---------------------------------------------------------
def obtener_inspecciones_detalle(
    cluster,
    clausula_FROM: str,
    tramo: str,
    via: str,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None
) -> List[Dict[str, Any]]:

    f_ini = normalizar_fecha(fecha_inicio)
    f_fin = normalizar_fecha(fecha_fin)

    filtros = [
        "a.id_tramo = $tramo",
        "a.id_via   = $via",
        "a.tipo_formulario IS NOT MISSING",
        f"LOWER(a.tipo_formulario) NOT IN {TIPOS_FORMULARIO_N1QL}"
    ]

    if f_ini:
        filtros.append("a.fecha >= $fecha_inicio")
    if f_fin:
        filtros.append("a.fecha <= $fecha_fin")

    where_clause = " AND ".join(filtros)

    query = f"""
        SELECT
            META(a).id AS id,
            a.id_tramo,
            a.id_via,
            a.fecha,
            a.tipo_formulario,
            a.num_km,
            a.num_errores,
            a.estado,
            a.created_by,
            a.updated_by
        {clausula_FROM}`Actuaciones` a
        WHERE {where_clause}
        ORDER BY a.fecha DESC;
    """

    params = {
        "tramo": tramo,
        "via": via,
        "fecha_inicio": f_ini,
        "fecha_fin": f_fin
    }

    try:
        rows = cluster.query(query, **{k: v for k, v in params.items() if v is not None}).rows()
        return [dict(r) for r in rows]
    except Exception as e:
        print("❌ Error obteniendo detalle:", e)
        return []
