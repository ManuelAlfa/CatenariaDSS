from django.urls import path

from . import views

app_name = "kpi_kgi"

urlpatterns = [
    path("", views.kpi_kgi, name="kpi_kgi"),
]
