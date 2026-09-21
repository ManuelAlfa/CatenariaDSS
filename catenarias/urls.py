from __future__ import annotations

from pathlib import Path

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve


BASE_DIR = Path(__file__).resolve().parent.parent

urlpatterns = [
    # Core (login, logout, entrada, configuración)
    path("", include("apps.core.urls")),
    # Usuarios
    path("usuarios/", include("apps.usuarios.urls")),
    # DSS (Decision Support System) — hub
    path("dss", include("apps.dss.urls")),
    # Sistemas de KPI / KGI — hub
    path("kpi-kgi", include("apps.kpi_kgi.urls")),
    # Analítica (vistas hoja: actual, predictiva)
    path("analitica/", include("apps.analitica.urls")),
    # Alertas
    path("alertas/", include("apps.alertas.urls")),
    # Tramos
    path("tramos/", include("apps.tramos.urls")),
    # Umbrales
    path("umbrales/", include("apps.umbrales.urls")),
    # Operaciones
    path("operaciones/", include("apps.operaciones.urls")),
    # Consultas
    path("", include("apps.consultas.urls")),
    # Sync
    path("", include("apps.sync.urls")),
    # Dev-only: preserve existing /img/... URLs without changing HTML.
    re_path(r"^img/(?P<path>.*)$", serve, {"document_root": str(BASE_DIR / "img")}),
]

handler400 = "apps.core.views.error_400"
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"

