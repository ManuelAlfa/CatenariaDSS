"""
Vistas hoja del módulo Consultas: filtros, mapas, mediciones, consultar-datos.
"""
from apps.core.views import (
    tabla,
    filtros,
    obtener_vias,
    mapa_cuadrantes,
    mapa_cuadrantes_overview,
    medicion_detalle,
    incidencia_detalle,
    incidencias_medicion,
    consultar_datos,
)

__all__ = [
    "tabla",
    "filtros",
    "obtener_vias",
    "mapa_cuadrantes",
    "mapa_cuadrantes_overview",
    "medicion_detalle",
    "incidencia_detalle",
    "incidencias_medicion",
    "consultar_datos",
]
