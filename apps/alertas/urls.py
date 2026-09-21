from django.urls import path
from . import views

app_name = "alertas"

urlpatterns = [
    path("", views.alertas, name="alertas"),
    path("marcar-revision", views.marcar_revision, name="marcar_revision"),
]
