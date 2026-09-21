from django.urls import path
from . import views

app_name = "operaciones"

urlpatterns = [
    path("", views.operaciones, name="operaciones"),
    path("nuevo", views.operaciones_nuevo, name="operaciones_nuevo"),
    path("grupo/nuevo", views.operaciones_grupo_nuevo, name="operaciones_grupo_nuevo"),
    path("editar", views.operaciones_editar, name="operaciones_editar"),
    path("eliminar", views.operaciones_eliminar, name="operaciones_eliminar"),
    path("actualizar-tablas-tablet", views.operaciones_actualizar_tablas, name="operaciones_actualizar_tablas"),
]
