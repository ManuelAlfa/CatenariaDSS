from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "consultas"

urlpatterns = [
    # Compat: rutas antiguas del hub viejo "Consultas" -> ahora "DSS".
    path("consulta", RedirectView.as_view(url="/dss", permanent=True)),
    path("consultas", RedirectView.as_view(url="/dss", permanent=True)),

    # Vistas hoja del módulo Consultas (datos, KPIs, mapas, mediciones).
    path("consultar-datos", views.consultar_datos, name="consultar_datos"),
    path("tabla", views.tabla, name="tabla"),
    path("filtros", views.filtros, name="filtros"),
    path("obtener_vias", views.obtener_vias, name="obtener_vias"),
    path("mapa-cuadrantes", views.mapa_cuadrantes, name="mapa_cuadrantes"),
    path("mapa-cuadrantes-overview", views.mapa_cuadrantes_overview, name="mapa_cuadrantes_overview"),
    path("medicion-detalle", views.medicion_detalle, name="medicion_detalle"),
    path("incidencia-detalle", views.incidencia_detalle, name="incidencia_detalle"),
    path("incidencias-medicion", views.incidencias_medicion, name="incidencias_medicion"),
]
