from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "analitica"

urlpatterns = [
    # Compat: el antiguo hub /analitica/ ya no existe; redirige al hub KPI / KGI.
    path("", RedirectView.as_view(url="/kpi-kgi", permanent=True)),
    path("actual", views.analitica_actual, name="analitica_actual"),
    path("predictiva", views.analitica_predictiva, name="analitica_predictiva"),
    path("predictiva/datos", views.analitica_predictiva_datos, name="analitica_predictiva_datos"),
]
