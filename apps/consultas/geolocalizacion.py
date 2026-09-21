"""
geo_tramos.py
=============
Resolución de tramos de vía por ámbito geográfico.

Lógica (según especificación):
  1. Recibir coordenada GPS + radio en km.
  2. Localizar el cuadrante que contiene ese punto consultando Cuadrantes
     (esquina_NO / esquina_SE).
  3. Calcular cuántos anillos de cuadrantes cubre el radio (~0.98 km alto,
     ~1.02 km ancho) y consultar todos los cuadrantes vecinos.
  4. Obtener todos los tramos asociados a esos cuadrantes via Tramos_Cuadrantes
     → Maestro_Tramos.
  5. Para cada tramo candidato calcular la distancia real (haversine al
     segmento) y filtrar los que están dentro del radio.
  6. Devolver:
       - El tramo MÁS CERCANO como resultado principal (ResultadoTramo).
       - La lista COMPLETA de tramos encontrados (todos_los_tramos).

Estructura de cuadrantes:
  id_cuadrante = (fila - 1) * COLS + col + 999   (COLS = 79)
  Tamaño aproximado: ~0.98 km alto × ~1.02 km ancho.
"""

from __future__ import annotations

import logging
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de la cuadrícula
# ---------------------------------------------------------------------------
COLS: int = 79         # columnas por fila
BASE_ID: int = 999        # id_cuadrante = (fila-1)*COLS + col + BASE_ID
KM_POR_FILA: float = 0.981
KM_POR_COL:  float = 1.018

_KEYSPACE_RE = re.compile(r'^[\w.\`\s-]+$')


# ---------------------------------------------------------------------------
# Tipos de salida
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TramoEncontrado:
    """Un tramo encontrado en la zona de búsqueda con su distancia."""
    id_tramo:     str
    id_via:       Optional[str]
    distancia_km: float


@dataclass
class ResultadoBusqueda:
    """
    Resultado completo de la búsqueda geográfica.

    Atributos
    ---------
    tramo_principal : TramoEncontrado
        El tramo más cercano al punto GPS dentro del radio.
    todos_los_tramos : list[TramoEncontrado]
        Todos los tramos encontrados, ordenados de menor a mayor distancia.
    coordenada_gps : tuple[float, float]
        (lat, lon) del punto de búsqueda.
    radio_km : float
        Radio de búsqueda utilizado.
    """
    tramo_principal:  TramoEncontrado
    todos_los_tramos: List[TramoEncontrado]
    coordenada_gps:   Tuple[float, float]
    radio_km:         float

    # ── Compatibilidad con código legado que espera un dict ──────────────────
    def _as_dict(self) -> Dict[str, Any]:
        return {
            "id_tramo":     self.tramo_principal.id_tramo,
            "id_via":       self.tramo_principal.id_via,
            "distancia_km": self.tramo_principal.distancia_km,
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._as_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._as_dict()[key]

    def __contains__(self, key: object) -> bool:
        return key in self._as_dict()

    def keys(self):   return self._as_dict().keys()
    def values(self): return self._as_dict().values()
    def items(self):  return self._as_dict().items()


# Alias para retrocompatibilidad
ResultadoTramo = ResultadoBusqueda


# ---------------------------------------------------------------------------
# Validación y parsing
# ---------------------------------------------------------------------------

def _validar_keyspace(clausula_FROM: str) -> None:
    s = (clausula_FROM or "").strip()
    if s and not _KEYSPACE_RE.match(s):
        raise ValueError(f"clausula_FROM contiene caracteres no permitidos: {s!r}")


def _parsear_coordenada_gps(coordenada_gps: str) -> Tuple[float, float]:
    """Parsea 'lat, lon' → (lat, lon). Acepta coma, punto y coma o espacio."""
    if not coordenada_gps:
        raise ValueError("La coordenada GPS es obligatoria")

    texto = "".join(
        c if unicodedata.category(c) != "Zs" else " "
        for c in coordenada_gps.strip()
    )
    texto = texto.replace(";", ",").replace(" ,", ",").replace(", ", ",")
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    if len(partes) == 1:
        partes = [p.strip() for p in texto.split() if p.strip()]
    if len(partes) != 2:
        raise ValueError(
            f"Formato de coordenada inválido ({coordenada_gps!r}). Use: latitud, longitud"
        )
    try:
        lat, lon = float(partes[0]), float(partes[1])
    except ValueError as exc:
        raise ValueError("La coordenada GPS debe contener números decimales válidos") from exc

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError(f"Coordenada fuera de rango: lat={lat}, lon={lon}")
    return lat, lon


def _keyspace_prefix(clausula_FROM: str) -> str:
    s = (clausula_FROM or "").strip()
    if not s:
        return ""
    if s.upper().startswith("FROM "):
        s = s[5:].strip()
    return s if s.endswith(".") else s + "."


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en km entre dos puntos (fórmula haversine)."""
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _distancia_punto_a_segmento_km(
    lat_p: float, lon_p: float,
    lat_a: float, lon_a: float,
    lat_b: float, lon_b: float,
) -> float:
    """Distancia mínima en km del punto P al segmento AB."""
    lat_ref  = (lat_a + lat_b) / 2.0
    km_lat   = 111.32
    km_lon   = 111.32 * math.cos(math.radians(lat_ref))

    ax = (lat_a - lat_p) * km_lat;  ay = (lon_a - lon_p) * km_lon
    bx = (lat_b - lat_p) * km_lat;  by = (lon_b - lon_p) * km_lon
    dx = bx - ax;  dy = by - ay
    len_sq = dx * dx + dy * dy

    if len_sq == 0.0:
        return _haversine_km(lat_p, lon_p, lat_a, lon_a)

    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / len_sq))
    return _haversine_km(lat_p, lon_p,
                         lat_a + t * (lat_b - lat_a),
                         lon_a + t * (lon_b - lon_a))


def _punto_dentro_cuadrante(
    lat: float, lon: float,
    esquina_no: List[float],
    esquina_se: List[float],
) -> bool:
    """True si el punto (lat, lon) está dentro del cuadrante."""
    lat_max = float(esquina_no[0]);  lat_min = float(esquina_se[0])
    lon_min = float(esquina_no[1]);  lon_max = float(esquina_se[1])
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


# ---------------------------------------------------------------------------
# Paso 1: localizar cuadrante que contiene el punto GPS
# ---------------------------------------------------------------------------

def _localizar_cuadrante_central(
    cluster: Any,
    keyspace: str,
    lat: float,
    lon: float,
) -> Dict[str, Any]:
    """
    Devuelve la fila del cuadrante que contiene (lat, lon).

    Consulta Cuadrantes filtrando por las esquinas NO/SE.
    Si el punto cae justo en la frontera entre dos cuadrantes se elige
    el primero que devuelva la BD (diferencia de metros, irrelevante).
    """
    query = f"""
        SELECT c.id_cuadrante, c.fila, c.col, c.esquina_NO, c.esquina_SE
        FROM {keyspace}`Cuadrantes` AS c
        WHERE c.esquina_NO[0] >= $lat
          AND c.esquina_SE[0] <= $lat
          AND c.esquina_NO[1] <= $lon
          AND c.esquina_SE[1] >= $lon
        LIMIT 1;
    """
    filas = list(cluster.query(query, lat=lat, lon=lon).rows())
    if not filas:
        query_todos = f"""
            SELECT c.id_cuadrante, c.fila, c.col, c.esquina_NO, c.esquina_SE
            FROM {keyspace}`Cuadrantes` AS c;
        """
        candidatos = [dict(r) for r in cluster.query(query_todos).rows()]
        if not candidatos:
            raise ValueError("No hay cuadrantes disponibles en la base de datos")

        def distancia_a_cuadrante(cuad: Dict[str, Any]) -> float:
            esquina_no = cuad.get("esquina_NO") or []
            esquina_se = cuad.get("esquina_SE") or []
            if len(esquina_no) < 2 or len(esquina_se) < 2:
                return float("inf")
            lat_max = float(esquina_no[0])
            lat_min = float(esquina_se[0])
            lon_min = float(esquina_no[1])
            lon_max = float(esquina_se[1])
            lat_cercana = min(max(lat, lat_min), lat_max)
            lon_cercana = min(max(lon, lon_min), lon_max)
            return _haversine_km(lat, lon, lat_cercana, lon_cercana)

        filas = [min(candidatos, key=distancia_a_cuadrante)]
    return dict(filas[0])


# ---------------------------------------------------------------------------
# Paso 2: calcular rango de vecinos según radio
# ---------------------------------------------------------------------------

def _rango_vecinos(
    fila_centro: int,
    col_centro: int,
    radio_km: float,
    cols_max: int = COLS,
) -> Tuple[int, int, int, int]:
    """
    Devuelve (fila_min, fila_max, col_min, col_max) de cuadrantes
    que pueden estar dentro del radio.

    Se añade +1 de margen para cubrir cuadrantes en el borde.
    """
    delta_filas = math.ceil(radio_km / KM_POR_FILA) + 1
    delta_cols  = math.ceil(radio_km / KM_POR_COL)  + 1

    return (
        max(1, fila_centro - delta_filas),
        fila_centro + delta_filas,
        max(1, col_centro  - delta_cols),
        min(cols_max, col_centro + delta_cols),
    )


# ---------------------------------------------------------------------------
# Paso 3: obtener tramos en el rango de cuadrantes
# ---------------------------------------------------------------------------

def _consultar_tramos_en_rango(
    cluster: Any,
    keyspace: str,
    fila_min: int,
    fila_max: int,
    col_min:  int,
    col_max:  int,
) -> List[Dict[str, Any]]:
    """
    Devuelve todos los segmentos de tramo asociados a cuadrantes
    en el rango fila/col indicado.
    """
    query = f"""
        SELECT DISTINCT
            mt.id_tramo        AS id_tramo,
            mt.id_via          AS id_via,
            mt.punto_inicial   AS punto_inicial,
            mt.punto_final     AS punto_final,
            mt.punto_centroide AS punto_centroide
        FROM {keyspace}`Cuadrantes` AS c
        JOIN {keyspace}`Tramos_Cuadrantes` AS tc
            ON tc.id_cuadrante = c.id_cuadrante
        JOIN {keyspace}`Maestro_Tramos` AS mt
            ON mt.id = tc.id_tramo
        WHERE c.fila >= $fila_min AND c.fila <= $fila_max
          AND c.col  >= $col_min  AND c.col  <= $col_max
          AND mt.id_tramo IS NOT MISSING;
    """
    logger.debug(
        "Consultando tramos: filas [%s-%s] cols [%s-%s]",
        fila_min, fila_max, col_min, col_max,
    )
    return [dict(r) for r in cluster.query(
        query,
        fila_min=fila_min, fila_max=fila_max,
        col_min=col_min,   col_max=col_max,
    ).rows()]


# ---------------------------------------------------------------------------
# Paso 4: filtrar por distancia real y construir lista de candidatos
# ---------------------------------------------------------------------------

def _calcular_candidatos(
    segmentos: List[Dict[str, Any]],
    lat_ref: float,
    lon_ref: float,
    radio_km: float,
) -> List[TramoEncontrado]:
    """
    Para cada segmento calcula la distancia real al punto GPS.
    Acumula la distancia MÍNIMA por (id_tramo, id_via) y filtra por radio.

    Devuelve lista de TramoEncontrado ordenada de menor a mayor distancia.
    """
    distancias: Dict[Tuple[str, str], float] = {}

    for seg in segmentos:
        id_tramo        = seg.get("id_tramo")
        id_via          = seg.get("id_via")
        punto_inicial   = seg.get("punto_inicial")
        punto_final     = seg.get("punto_final")
        punto_centroide = seg.get("punto_centroide")

        if not id_tramo or not punto_inicial or not punto_final:
            continue
        if len(punto_inicial) < 2 or len(punto_final) < 2:
            continue

        if not punto_centroide or len(punto_centroide) < 2:
            punto_centroide = [
                (float(punto_inicial[0]) + float(punto_final[0])) / 2.0,
                (float(punto_inicial[1]) + float(punto_final[1])) / 2.0,
            ]

        dist_seg = _distancia_punto_a_segmento_km(
            lat_ref, lon_ref,
            float(punto_inicial[0]),   float(punto_inicial[1]),
            float(punto_final[0]),     float(punto_final[1]),
        )
        dist_cent = _haversine_km(
            lat_ref, lon_ref,
            float(punto_centroide[0]), float(punto_centroide[1]),
        )
        distancia = min(dist_seg, dist_cent)

        if distancia > radio_km:
            continue

        key = (str(id_tramo), str(id_via) if id_via is not None else "")
        if key not in distancias or distancia < distancias[key]:
            distancias[key] = distancia

    resultado = [
        TramoEncontrado(
            id_tramo=k[0],
            id_via=k[1] or None,
            distancia_km=round(v, 4),
        )
        for k, v in distancias.items()
    ]
    resultado.sort(key=lambda t: t.distancia_km)

    logger.debug("Tramos dentro del radio (%.2f km): %d", radio_km, len(resultado))
    return resultado


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def resolver_tramo_por_ambito_geografico(
    cluster: Any,
    clausula_FROM: str,
    coordenada_gps: str,
    radio_km: float,
) -> ResultadoBusqueda:
    """
    Resuelve el/los tramos de vía dentro de un radio geográfico.

    Algoritmo
    ---------
    1. Localizar el cuadrante que contiene la coordenada GPS.
    2. Calcular el rango de cuadrantes vecinos que cubre el radio.
    3. Obtener todos los tramos asociados a esos cuadrantes.
    4. Calcular la distancia real a cada segmento y filtrar por radio.
    5. Devolver el más cercano como tramo principal + lista completa.

    Parámetros
    ----------
    cluster        : Conexión activa al cluster Couchbase.
    clausula_FROM  : Keyspace N1QL, p. ej. ``"my_bucket.my_scope"``.
    coordenada_gps : ``"latitud, longitud"`` (coma, punto y coma o espacio).
    radio_km       : Radio de búsqueda en km (> 0).

    Retorna
    -------
    ResultadoBusqueda
        .tramo_principal  → tramo más cercano
        .todos_los_tramos → lista completa ordenada por distancia
        .coordenada_gps   → (lat, lon) del punto buscado
        .radio_km         → radio usado

    Lanza
    -----
    ValueError  si los parámetros son inválidos o no hay tramos en el radio.
    """
    # ── Validaciones ─────────────────────────────────────────────────────────
    if radio_km is None or float(radio_km) <= 0:
        raise ValueError("El radio debe ser mayor que 0")
    _validar_keyspace(clausula_FROM)
    lat_ref, lon_ref = _parsear_coordenada_gps(coordenada_gps)
    radio_km = float(radio_km)
    keyspace = _keyspace_prefix(clausula_FROM)

    logger.info(
        "Búsqueda geográfica: lat=%.6f lon=%.6f radio=%.2f km",
        lat_ref, lon_ref, radio_km,
    )

    # ── 1. Cuadrante central ──────────────────────────────────────────────────
    cuadrante_central = _localizar_cuadrante_central(cluster, keyspace, lat_ref, lon_ref)
    fila_c = int(cuadrante_central["fila"])
    col_c  = int(cuadrante_central["col"])
    logger.debug("Cuadrante central: id=%s fila=%s col=%s",
                 cuadrante_central["id_cuadrante"], fila_c, col_c)

    # ── 2. Rango de vecinos ───────────────────────────────────────────────────
    try:                                                         # ← AQUÍ
        cols_result = cluster.query(
            f"SELECT MAX(c.col) AS max_col FROM {keyspace}`Cuadrantes` AS c"
        ).rows()
        cols_max = int(cols_result[0]["max_col"])
    except Exception:
        cols_max = COLS
        logger.warning("No se pudo obtener MAX(col) de BD, usando COLS=%s", COLS)

    fila_min, fila_max, col_min, col_max = _rango_vecinos(fila_c, col_c, radio_km, cols_max)

    # ── 3. Tramos en el rango ─────────────────────────────────────────────────
    segmentos = _consultar_tramos_en_rango(
        cluster, keyspace, fila_min, fila_max, col_min, col_max
    )
    if not segmentos:
        raise ValueError(
            "No se encontraron tramos en los cuadrantes del ámbito indicado"
        )

    # ── 4. Filtrar por distancia real ─────────────────────────────────────────
    candidatos = _calcular_candidatos(segmentos, lat_ref, lon_ref, radio_km)
    if not candidatos:
        raise ValueError(
            f"No se encontró ningún tramo dentro del radio de {radio_km} km "
            f"desde ({lat_ref:.6f}, {lon_ref:.6f})"
        )

    # ── 5. Resultado ──────────────────────────────────────────────────────────
    resultado = ResultadoBusqueda(
        tramo_principal=candidatos[0],
        todos_los_tramos=candidatos,
        coordenada_gps=(lat_ref, lon_ref),
        radio_km=radio_km,
    )
    logger.info(
        "Tramo principal: %s (vía %s) a %.4f km. Total tramos encontrados: %d",
        resultado.tramo_principal.id_tramo,
        resultado.tramo_principal.id_via,
        resultado.tramo_principal.distancia_km,
        len(candidatos),
    )
    return resultado


# ---------------------------------------------------------------------------
# Helper para interfaz.py: construir el bloque HTML de parámetros
# ---------------------------------------------------------------------------

def construir_mensaje_parametros(resultado: ResultadoBusqueda) -> str:
    """
    Genera el bloque HTML de parámetros para mostrar en la página de resultados.

    Muestra SOLO coordenadas GPS y radio. Debajo lista todos los tramos
    encontrados con un <details> colapsable si hay más de 3.
    """
    lat, lon   = resultado.coordenada_gps
    radio      = resultado.radio_km
    tramos     = resultado.todos_los_tramos
    n          = len(tramos)
    principal  = resultado.tramo_principal

    # ── Cabecera de parámetros ────────────────────────────────────────────────
    html = (
        "<div class='alert alert-info mb-2'>"
        "<strong>Parámetros de búsqueda:</strong> "
        f"Coordenadas GPS: {lat:.6f}, {lon:.6f} &nbsp;|&nbsp; Radio: {radio} km"
        "</div>"
    )
# ── Lista de tramos encontrados ───────────────────────────────────────────
    filas_tramos = "".join(
        f"<li class='list-group-item d-flex justify-content-between align-items-center"
        f"{'  fw-bold' if t.id_tramo == principal.id_tramo and t.id_via == principal.id_via else ''}'"
        f" style='background-color:#cff4fc;"
        f"{'border-left: 3px solid #0d6efd;' if t.id_tramo == principal.id_tramo and t.id_via == principal.id_via else ''}'>"
        f"Tramo <strong>{t.id_tramo}</strong> &nbsp; Vía: {t.id_via or '—'}"
        f"<span class='badge bg-secondary rounded-pill'>{t.distancia_km:.4f} km</span>"
        f"</li>"
        for t in tramos
    )
    
    if n <= 3:
        # Sin colapsable
        html += (
            f"<div class='mb-3'>"
            f"<strong>Tramos encontrados en esa localización ({n}):</strong>"
            f"<ul class='list-group mt-1'>{filas_tramos}</ul>"
            f"</div>"
        )
    else:
        # Con <details> colapsable
        primeros = "".join(
            f"<li class='list-group-item d-flex justify-content-between align-items-center"
            f"{'  list-group-item-success fw-bold' if t.id_tramo == principal.id_tramo and t.id_via == principal.id_via else ''}'"
            f" style='background-color:#cff4fc;'>"
            f"Tramo <strong>{t.id_tramo}</strong> &nbsp; Vía: {t.id_via or '—'}"
            f"<span class='badge bg-secondary rounded-pill'>{t.distancia_km:.4f} km</span>"
            f"</li>"
            for t in tramos[:3]
        )
        resto = "".join(
            f"<li class='list-group-item d-flex justify-content-between align-items-center"
            f"{'  list-group-item-success fw-bold' if t.id_tramo == principal.id_tramo and t.id_via == principal.id_via else ''}'"
            f" style='background-color:#cff4fc;'>"
            f"Tramo <strong>{t.id_tramo}</strong> &nbsp; Vía: {t.id_via or '—'}"
            f"<span class='badge bg-secondary rounded-pill'>{t.distancia_km:.4f} km</span>"
            f"</li>"
            for t in tramos[3:]
        )
        html += (
            f"<div class='mb-3'>"
            f"<details>"
            f"<summary style='cursor:pointer; font-weight:bold;'>"
            f"Tramos encontrados en esa localización ({n}) — "
            f"<span style='color:#0d6efd;'>ver todos …</span>"
            f"</summary>"
            f"<ul class='list-group mt-1'>"
            f"{primeros}{resto}"
            f"</ul>"
            f"</details>"
            f"</div>"
        )

    return html


# ---------------------------------------------------------------------------
# Helper para mapa (Leaflet): tramos/segmentos + cuadrantes
# ---------------------------------------------------------------------------
def resolver_mapa_por_ambito_geografico(
    cluster: Any,
    clausula_FROM: str,
    coordenada_gps: str,
    radio_km: float,
    max_segmentos: int = 3000,
) -> Dict[str, Any]:
    """
    Genera un payload listo para un mapa Leaflet.

    - Dibuja cuadrantes (rectángulos) del rango vecino.
    - Dibuja segmentos (polylines) cuyos puntos caen dentro del radio.
    - Cada segmento incluye qué cuadrantes tiene asociado para filtrar por click.

    Devuelve un dict serializable a JSON.
    """
    if radio_km is None or float(radio_km) <= 0:
        raise ValueError("El radio debe ser mayor que 0")

    _validar_keyspace(clausula_FROM)
    lat_ref, lon_ref = _parsear_coordenada_gps(coordenada_gps)
    radio_km = float(radio_km)
    keyspace = _keyspace_prefix(clausula_FROM)

    # ── 1) Cuadrante central ─────────────────────────────────────────────────
    cuadrante_central = _localizar_cuadrante_central(cluster, keyspace, lat_ref, lon_ref)
    fila_c = int(cuadrante_central["fila"])
    col_c = int(cuadrante_central["col"])

    # ── 2) Rango de vecinos (margen ~ borde) ───────────────────────────────
    try:
        cols_result = cluster.query(
            f"SELECT MAX(c.col) AS max_col FROM {keyspace}`Cuadrantes` AS c"
        ).rows()
        cols_max = int(cols_result[0]["max_col"])
    except Exception:
        cols_max = COLS

    fila_min, fila_max, col_min, col_max = _rango_vecinos(fila_c, col_c, radio_km, cols_max)

    # ── 3) Segmentos (geometría) + pertenencia a cuadrantes ───────────────
    #
    # Ojo: en Tramos_Cuadrantes.id_tramo suele corresponder al id "uuid" del
    # registro en Maestro_Tramos (mt.id), mientras mt.id_tramo es el código.
    query = f"""
        SELECT
            mt.id               AS id_segmento,
            mt.id_tramo        AS id_tramo,
            mt.id_via          AS id_via,
            mt.punto_inicial   AS punto_inicial,
            mt.punto_final     AS punto_final,
            mt.punto_centroide AS punto_centroide,
            tc.id_cuadrante    AS id_cuadrante
        FROM {keyspace}`Cuadrantes` AS c
        JOIN {keyspace}`Tramos_Cuadrantes` AS tc
            ON tc.id_cuadrante = c.id_cuadrante
        JOIN {keyspace}`Maestro_Tramos` AS mt
            ON mt.id = tc.id_tramo
        WHERE c.fila >= $fila_min AND c.fila <= $fila_max
          AND c.col  >= $col_min  AND c.col  <= $col_max
          AND mt.id_tramo IS NOT MISSING
          AND mt.id_tramo IS NOT NULL;
    """
    rows = [dict(r) for r in cluster.query(query, fila_min=fila_min, fila_max=fila_max, col_min=col_min, col_max=col_max).rows()]

    # Agrupamos por id_segmento para unir el set de cuadrantes asociados.
    segmentos_tmp: Dict[str, Dict[str, Any]] = {}

    for r in rows:
        seg_id = r.get("id_segmento")
        if not seg_id:
            continue

        punto_ini = r.get("punto_inicial") or []
        punto_fin = r.get("punto_final") or []
        if len(punto_ini) < 2 or len(punto_fin) < 2:
            continue

        if seg_id not in segmentos_tmp:
            punto_cent = r.get("punto_centroide") or []
            if len(punto_cent) < 2:
                punto_cent = [
                    (float(punto_ini[0]) + float(punto_fin[0])) / 2.0,
                    (float(punto_ini[1]) + float(punto_fin[1])) / 2.0,
                ]

            dist_seg = _distancia_punto_a_segmento_km(
                lat_ref,
                lon_ref,
                float(punto_ini[0]),
                float(punto_ini[1]),
                float(punto_fin[0]),
                float(punto_fin[1]),
            )
            dist_cent = _haversine_km(lat_ref, lon_ref, float(punto_cent[0]), float(punto_cent[1]))
            distancia = min(dist_seg, dist_cent)

            segmentos_tmp[seg_id] = {
                "id_segmento": seg_id,
                "id_tramo": r.get("id_tramo", ""),
                "id_via": r.get("id_via"),
                "punto_inicial": [float(punto_ini[0]), float(punto_ini[1])],
                "punto_final": [float(punto_fin[0]), float(punto_fin[1])],
                "distancia_km": round(float(distancia), 4),
                "cuadrantes": set(),
            }

        cuad_id = r.get("id_cuadrante")
        if cuad_id is not None:
            segmentos_tmp[seg_id]["cuadrantes"].add(int(cuad_id))

    # ── 4) Filtrado por radio + cap de rendimiento ──────────────────────────
    segmentos_filtrados = [
        s
        for s in segmentos_tmp.values()
        if s.get("distancia_km") is not None and float(s["distancia_km"]) <= radio_km + 1e-9
    ]

    segmentos_filtrados.sort(key=lambda s: float(s.get("distancia_km", 0)))
    if max_segmentos is not None and max_segmentos > 0 and len(segmentos_filtrados) > max_segmentos:
        segmentos_filtrados = segmentos_filtrados[:max_segmentos]

    if not segmentos_filtrados:
        logger.warning(
            "No se encontraron segmentos dentro del radio para el mapa; se devuelve payload vacío"
        )
        return {
            "punto_busqueda": {"lat": lat_ref, "lon": lon_ref},
            "radio_km": radio_km,
            "cuadrante_defecto": int(cuadrante_central["id_cuadrante"]),
            "cuadrantes": [],
            "segmentos": [],
            "bounds_hint": {"fila_min": fila_min, "fila_max": fila_max, "col_min": col_min, "col_max": col_max},
        }

    # ── 5) Cuadrantes a dibujar (solo los que tienen segmentos incluidos) ──
    cuadrantes_set = set()
    for s in segmentos_filtrados:
        cuadrantes_set |= set(s.get("cuadrantes") or [])

    cuadrantes_set = {int(x) for x in cuadrantes_set if x is not None}

    query_c = f"""
        SELECT c.id_cuadrante, c.esquina_NO, c.esquina_SE, c.fila, c.col
        FROM {keyspace}`Cuadrantes` AS c
        WHERE c.fila >= $fila_min AND c.fila <= $fila_max
          AND c.col  >= $col_min  AND c.col  <= $col_max;
    """
    cuad_rows = [dict(r) for r in cluster.query(query_c, fila_min=fila_min, fila_max=fila_max, col_min=col_min, col_max=col_max).rows()]
    cuad_map: Dict[int, Dict[str, Any]] = {}
    for c in cuad_rows:
        try:
            id_c = int(c.get("id_cuadrante"))
        except Exception:
            continue
        if id_c not in cuadrantes_set:
            continue
        cuad_map[id_c] = {
            "id_cuadrante": id_c,
            "esquina_NO": c.get("esquina_NO") or [],
            "esquina_SE": c.get("esquina_SE") or [],
            "fila": c.get("fila"),
            "col": c.get("col"),
        }

    cuadrantes = [cuad_map[cid] for cid in sorted(cuad_map.keys())]

    # Preparación final: convertir sets -> listas (JSON serializable).
    segmentos = []
    for s in segmentos_filtrados:
        segmentos.append(
            {
                "id_segmento": s["id_segmento"],
                "id_tramo": s.get("id_tramo", ""),
                "id_via": s.get("id_via"),
                "punto_inicial": s.get("punto_inicial") or [0.0, 0.0],
                "punto_final": s.get("punto_final") or [0.0, 0.0],
                "distancia_km": s.get("distancia_km", 0.0),
                "cuadrantes": sorted(list(s.get("cuadrantes") or [])),
            }
        )

    return {
        "punto_busqueda": {"lat": lat_ref, "lon": lon_ref},
        "radio_km": radio_km,
        "cuadrante_defecto": int(cuadrante_central["id_cuadrante"]),
        "cuadrantes": cuadrantes,
        "segmentos": segmentos,
        "bounds_hint": {"fila_min": fila_min, "fila_max": fila_max, "col_min": col_min, "col_max": col_max},
    }


def resolver_tramos_por_cuadrantes(
    cluster: Any,
    clausula_FROM: str,
    ids_cuadrantes: list[int],
    max_tramos: int = 5000,
) -> list[TramoEncontrado]:
    """
    Devuelve tramos (id_tramo/id_via) asociados a una lista de cuadrantes.
    Útil para el flujo "selecciono cuadrantes en mapa" sin coordenada+radio.
    """
    if not ids_cuadrantes:
        return []
    _validar_keyspace(clausula_FROM)
    keyspace = _keyspace_prefix(clausula_FROM)
    ids = [int(x) for x in ids_cuadrantes if x is not None]
    if not ids:
        return []

    query = f"""
        SELECT DISTINCT
            mt.id_tramo AS id_tramo,
            mt.id_via   AS id_via
        FROM {keyspace}`Tramos_Cuadrantes` AS tc
        JOIN {keyspace}`Maestro_Tramos` AS mt
            ON mt.id = tc.id_tramo
        WHERE tc.id_cuadrante IN $ids
          AND mt.id_tramo IS NOT MISSING
          AND mt.id_tramo IS NOT NULL
        LIMIT $limit;
    """
    rows = [dict(r) for r in cluster.query(query, ids=ids, limit=int(max_tramos)).rows()]
    out: list[TramoEncontrado] = []
    for r in rows:
        id_tramo = r.get("id_tramo")
        if not id_tramo:
            continue
        out.append(TramoEncontrado(id_tramo=str(id_tramo), id_via=r.get("id_via"), distancia_km=0.0))
    return out


# ---------------------------------------------------------------------------
# Tests unitarios
# ---------------------------------------------------------------------------

def _run_tests() -> None:  # pragma: no cover
    import traceback

    ok = 0; fail = 0

    def check(name, fn):
        nonlocal ok, fail
        try:
            fn(); print(f"  ✅  {name}"); ok += 1
        except Exception:
            print(f"  ❌  {name}"); traceback.print_exc(); fail += 1

    print("\n── Tests de _haversine_km ──")
    check("Madrid–Barcelona ~505 km",
          lambda: None if 503 < _haversine_km(40.4168,-3.7038,41.3851,2.1734) < 507
          else (_ for _ in ()).throw(AssertionError("fuera de rango")))
    check("Mismo punto → 0",
          lambda: None if _haversine_km(0,0,0,0) == 0.0
          else (_ for _ in ()).throw(AssertionError()))

    print("\n── Tests de _parsear_coordenada_gps ──")
    def t_parse_coma():
        lat, lon = _parsear_coordenada_gps("40.4168, -3.7038")
        assert lat == 40.4168 and lon == -3.7038
    def t_parse_pycoma():
        lat, _ = _parsear_coordenada_gps("40.4168; -3.7038")
        assert lat == 40.4168
    def t_parse_vacia():
        try: _parsear_coordenada_gps(""); assert False
        except ValueError: pass
    def t_parse_rango():
        try: _parsear_coordenada_gps("95.0, 0.0"); assert False
        except ValueError: pass
    check("Coma",              t_parse_coma)
    check("Punto y coma",      t_parse_pycoma)
    check("Vacía → ValueError",t_parse_vacia)
    check("Rango → ValueError",t_parse_rango)

    print("\n── Tests de _distancia_punto_a_segmento_km ──")
    def t_sobre_segmento():
        d = _distancia_punto_a_segmento_km(40.5,-4.0, 40.0,-4.0, 41.0,-4.0)
        assert d < 0.01, d
    def t_fuera_extremo():
        d = _distancia_punto_a_segmento_km(42.0,-4.0, 40.0,-4.0, 41.0,-4.0)
        ref = _haversine_km(42.0,-4.0, 41.0,-4.0)
        assert abs(d - ref) < 0.1, (d, ref)
    def t_degenerado():
        d   = _distancia_punto_a_segmento_km(40.5,-4.0, 40.0,-4.0, 40.0,-4.0)
        ref = _haversine_km(40.5,-4.0, 40.0,-4.0)
        assert abs(d - ref) < 0.001
    check("Punto sobre segmento → ~0", t_sobre_segmento)
    check("Punto más allá extremo",    t_fuera_extremo)
    check("Segmento degenerado",       t_degenerado)

    print("\n── Tests de _rango_vecinos ──")
    def t_rango_radio_pequeño():
        fmin,fmax,cmin,cmax = _rango_vecinos(25, 40, 0.5)
        # Con radio 0.5 km → delta_filas=1+1=2, delta_cols=1+1=2
        assert fmin == 23 and fmax == 27
        assert cmin == 38 and cmax == 42
    def t_rango_radio_grande():
        fmin,fmax,cmin,cmax = _rango_vecinos(25, 40, 5.0)
        assert fmin <= 19 and fmax >= 31
    def t_rango_no_negativo():
        fmin,_,cmin,_ = _rango_vecinos(1, 1, 10.0)
        assert fmin >= 1 and cmin >= 1
    check("Radio pequeño → vecinos correctos", t_rango_radio_pequeño)
    check("Radio grande → rango amplio",       t_rango_radio_grande)
    check("No produce filas/cols negativas",   t_rango_no_negativo)

    print("\n── Tests de _calcular_candidatos ──")
    def t_excluye_fuera():
        segs = [{"id_tramo":"T1","id_via":"1",
                 "punto_inicial":[40.0,-3.0],"punto_final":[41.0,-3.0],
                 "punto_centroide":[40.5,-3.0]}]
        assert len(_calcular_candidatos(segs, 10.0, 10.0, 0.001)) == 0
    def t_incluye_dentro():
        segs = [{"id_tramo":"T1","id_via":"1",
                 "punto_inicial":[40.3,-3.8],"punto_final":[40.5,-3.6],
                 "punto_centroide":[40.4,-3.7]}]
        assert len(_calcular_candidatos(segs, 40.4168, -3.7038, 50.0)) == 1
    def t_elige_mas_cercano():
        segs = [
            {"id_tramo":"110800040","id_via":"1",
             "punto_inicial":[40.910342,-4.094772],
             "punto_final":[40.917847,-4.122610],
             "punto_centroide":[40.91510018,-4.11102045]},
            {"id_tramo":"011000100","id_via":"1",
             "punto_inicial":[40.644002,-4.603366],
             "punto_final":[40.647395,-4.629437],
             "punto_centroide":[40.647501,-4.615297]},
        ]
        cands = _calcular_candidatos(segs, 40.915, -4.108, 200.0)
        assert cands[0].id_tramo == "110800040", cands[0].id_tramo
    def t_dos_tramos_misma_zona():
        """Cuadrante con 2 tramos → ambos se devuelven, el más cercano primero."""
        lat_f, lon_f = 40.657213, -4.68309   # frontera 011000100 / 011000110
        segs = [
            {"id_tramo":"011000100","id_via":"1",
             "punto_inicial":[40.650671,-4.658601],
             "punto_final":[40.657213,-4.68309],
             "punto_centroide":[40.652146,-4.673171]},
            {"id_tramo":"011000110","id_via":"1",
             "punto_inicial":[40.657213,-4.68309],
             "punto_final":[40.675972,-4.693204],
             "punto_centroide":[40.667958,-4.690566]},
        ]
        cands = _calcular_candidatos(segs, lat_f, lon_f, 5.0)
        ids = [c.id_tramo for c in cands]
        assert "011000100" in ids and "011000110" in ids, ids
        assert len(cands) == 2
    check("Excluye fuera de radio",         t_excluye_fuera)
    check("Incluye dentro de radio",        t_incluye_dentro)
    check("Elige el más cercano primero",   t_elige_mas_cercano)
    check("Devuelve AMBOS tramos en zona de frontera", t_dos_tramos_misma_zona)

    print("\n── Tests de ResultadoBusqueda (compatibilidad dict) ──")
    def t_compat():
        te = TramoEncontrado("T1","V1",1.23)
        rb = ResultadoBusqueda(te,[te],(40.0,-3.0),5.0)
        assert rb.get("id_tramo") == "T1"
        assert rb["id_via"] == "V1"
        assert "distancia_km" in rb
        assert rb.get("no_existe","def") == "def"
    check("Compatibilidad dict completa", t_compat)

    print("\n── Tests de construir_mensaje_parametros ──")
    def t_html_pocos():
        te = TramoEncontrado("T1","1",0.1)
        rb = ResultadoBusqueda(te,[te],(40.0,-3.0),5.0)
        html = construir_mensaje_parametros(rb)
        assert "40.000000" in html and "5.0 km" in html
        assert "<details>" not in html  # sin colapsable
    def t_html_muchos():
        tramos = [TramoEncontrado(f"T{i}","1",float(i)*0.1) for i in range(6)]
        rb = ResultadoBusqueda(tramos[0],tramos,(40.0,-3.0),5.0)
        html = construir_mensaje_parametros(rb)
        assert "<details>" in html      # con colapsable
        assert "ver todos" in html
    check("HTML con ≤3 tramos: sin colapsable", t_html_pocos)
    check("HTML con >3 tramos: con colapsable", t_html_muchos)

    total = ok + fail
    print(f"\n{'─'*44}")
    print(f"Resultado: {ok}/{total} tests pasados", "✅" if fail == 0 else "❌")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s — %(message)s")
    _run_tests()