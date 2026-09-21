import configparser
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, text
from couchbase.exceptions import DocumentNotFoundException, DocumentExistsException


def _valor_fecha_a_yyyymmdd(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "year") and hasattr(val, "month") and hasattr(val, "day"):
        return f"{int(val.year):04d}{int(val.month):02d}{int(val.day):02d}"
    s = str(val).strip()
    if len(s) >= 10 and s[4] in "-/" and s[7] in "-/":
        s = s.replace("/", "-")
        parts = s.split("-")[:3]
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return f"{int(parts[0]):04d}{int(parts[1]):02d}{int(parts[2]):02d}"
    if len(s) == 8 and s.isdigit():
        return s
    return ""


def _ymd_a_iso_inicio_fin(ymd_min: str, ymd_max: str) -> Tuple[str, str]:
    if len(ymd_min) != 8 or len(ymd_max) != 8 or not ymd_min.isdigit() or not ymd_max.isdigit():
        return "", ""
    y1, m1, d1 = int(ymd_min[0:4]), int(ymd_min[4:6]), int(ymd_min[6:8])
    y2, m2, d2 = int(ymd_max[0:4]), int(ymd_max[4:6]), int(ymd_max[6:8])
    start = datetime(y1, m1, d1, 0, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(y2, m2, d2, 23, 59, 59, 999000, tzinfo=timezone.utc)
    return (
        start.isoformat().replace("+00:00", "Z"),
        end.isoformat().replace("+00:00", "Z"),
    )


def _pg_connection_candidates() -> List[str]:
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "config.ini"
    candidates: List[str] = []

    cfg = configparser.ConfigParser()
    if config_path.exists():
        cfg.read(config_path, encoding="utf-8")
        if cfg.has_section("postgres"):
            user = cfg.get("postgres", "user", fallback="postgres")
            password = cfg.get("postgres", "password", fallback="")
            host = cfg.get("postgres", "host", fallback="localhost")
            port = cfg.get("postgres", "port", fallback="5432")
            database = cfg.get("postgres", "database", fallback="catenaria")
            candidates.append(f"postgresql://{user}:{password}@{host}:{port}/{database}")

    env_user = os.getenv("PG_USER") or os.getenv("POSTGRES_USER")
    env_password = os.getenv("PG_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    env_host = os.getenv("PG_HOST") or os.getenv("POSTGRES_HOST")
    env_port = os.getenv("PG_PORT") or os.getenv("POSTGRES_PORT")
    env_database = os.getenv("PG_DB") or os.getenv("PG_DATABASE") or os.getenv("POSTGRES_DB")
    if env_user and env_password and env_host and env_port and env_database:
        candidates.insert(0, f"postgresql://{env_user}:{env_password}@{env_host}:{env_port}/{env_database}")

    candidates.extend(
        [
            "postgresql://postgres:1234@catenaria_postgres:5432/catenaria",
            "postgresql://postgres:admin1234@localhost:5432/catenaria",
        ]
    )

    deduplicated: List[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduplicated:
            deduplicated.append(candidate)
    return deduplicated


def _pg_engine():
    last_error: Exception | None = None
    for connection_string in _pg_connection_candidates():
        try:
            return create_engine(connection_string, pool_pre_ping=True)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise RuntimeError("No se pudo construir una conexion a PostgreSQL")


def obtener_rango_fechas_incidencias_postgres() -> Tuple[str, str, str, str]:
    query = text(
        """
        SELECT
            MIN(fecha::text) AS fecha_min,
            MAX(fecha::text) AS fecha_max
        FROM mediciones.incidencias
        WHERE fecha IS NOT NULL AND TRIM(fecha::text) <> '';
        """
    )
    row = None
    for connection_string in _pg_connection_candidates():
        try:
            engine = create_engine(connection_string, pool_pre_ping=True)
            with engine.connect() as conn:
                row = conn.execute(query).mappings().first()
            if row:
                break
        except Exception:  # noqa: BLE001
            continue

    if not row:
        return "", "", "", ""

    y_min = _valor_fecha_a_yyyymmdd(row.get("fecha_min"))
    y_max = _valor_fecha_a_yyyymmdd(row.get("fecha_max"))
    if not y_min or not y_max:
        return "", "", "", ""

    f_from, f_to = _ymd_a_iso_inicio_fin(y_min, y_max)
    return y_min, y_max, f_from, f_to

def obtener_tramos_crud(cluster, clausula_FROM) -> List[Dict[str, Any]]:
    """Esta funcion es para la consulta de tramos"""
    consulta = f'''
        SELECT
            META(t).id AS doc_id,
            t.id_tramo,
            t.id_via,
            t.pto_km_ini,
            t.pto_km_fin,
            t.descripcion,
            t.tipologia,
            t.velocidad_max
        {clausula_FROM}`Maestro_Tramos` t
        ORDER BY t.id_tramo, t.id_via, t.pto_km_ini;
    '''
    resultado = cluster.query(consulta)
    tramos = []
    for fila in resultado:
        tramos.append({
            "doc_id": fila.get("doc_id"),
            "id_tramo": fila.get("id_tramo", ""),
            "id_via": fila.get("id_via", ""),
            "pto_km_ini": fila.get("pto_km_ini", ""),
            "pto_km_fin": fila.get("pto_km_fin", ""),
            "descripcion": fila.get("descripcion", ""),
            "tipologia": fila.get("tipologia", ""),
            "velocidad_max": fila.get("velocidad_max", "")
        })
    return tramos

def obtener_tramos(cluster, clausula_FROM):
    consulta = "SELECT DISTINCT id_tramo " + clausula_FROM + "`Maestro_Tramos`" + "WHERE id_tramo IS NOT MISSING AND id_tramo IS NOT NULL;"
    resultado = cluster.query(consulta)
    return [row["id_tramo"] for row in resultado]


def obtener_tramos_con_incidencias(cluster, clausula_FROM):
    consulta = (
        "SELECT DISTINCT i.id_tramo "
        + clausula_FROM
        + "`Incidencias` i "
        + "WHERE i.id_tramo IS NOT MISSING AND i.id_tramo IS NOT NULL;"
    )
    resultado = cluster.query(consulta)
    return [row["id_tramo"] for row in resultado]

def obtener_vias_por_tramo(cluster, tramo, clausula_FROM):
    consulta = "SELECT DISTINCT id_via " + clausula_FROM + "`Maestro_Tramos`" + f' WHERE id_tramo = "{tramo}" AND id_via IS NOT MISSING AND id_via IS NOT NULL;'
    resultado = cluster.query(consulta)
    return sorted([row["id_via"] for row in resultado])


def crear_tramo(cluster, bucket_name, scope_name, documento):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Tramos")
    from uuid import uuid4
    coll.insert(str(uuid4()), documento)

def actualizar_tramo(cluster, bucket_name, scope_name, doc_id, datos_actualizados):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Tramos")
    coll.get(doc_id)
    coll.upsert(doc_id, datos_actualizados)

def eliminar_tramo(cluster, bucket_name, scope_name, doc_id):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Tramos")
    coll.remove(doc_id)





