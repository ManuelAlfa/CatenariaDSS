from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.usuarios, name="usuarios"),
    path("nuevo", views.usuarios_nuevo, name="usuarios_nuevo"),
    path("acceso/nuevo", views.usuarios_acceso_nuevo, name="usuarios_acceso_nuevo"),
    path("acceso/<str:doc_id>/editar", views.usuarios_acceso_editar, name="usuarios_acceso_editar"),
    path("acceso/<str:doc_id>/resetear-password", views.usuarios_acceso_resetear_password, name="usuarios_acceso_resetear_password"),
    path("acceso/<str:doc_id>/eliminar", views.usuarios_acceso_eliminar, name="usuarios_acceso_eliminar"),
    path("<str:doc_id>/editar", views.usuarios_editar, name="usuarios_editar"),
    path("<str:doc_id>/eliminar", views.usuarios_eliminar, name="usuarios_eliminar"),
]
