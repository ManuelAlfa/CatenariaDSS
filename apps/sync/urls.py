from django.urls import path
from . import views

app_name = "sync"

urlpatterns = [
    path("estado-sync", views.estado_sync, name="estado_sync"),
    path("limpiar-estado-sync", views.limpiar_estado_sync, name="limpiar_estado_sync"),
    path("ejecutar-script", views.ejecutar_script, name="ejecutar_script"),
]
