from django.urls import path
from . import views

app_name = "tramos"

urlpatterns = [
    path("", views.tramos, name="tramos"),
    path("nuevo", views.tramos_nuevo, name="tramos_nuevo"),
    path("<str:doc_id>/editar", views.tramos_editar, name="tramos_editar"),
    path("<str:doc_id>/eliminar", views.tramos_eliminar, name="tramos_eliminar"),
]
