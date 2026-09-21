from django.urls import path
from . import views

app_name = "umbrales"

urlpatterns = [
    path("", views.umbrales, name="umbrales"),
    path("validar", views.umbrales_validar, name="umbrales_validar"),
    path("nuevo", views.umbrales_nuevo, name="umbrales_nuevo"),
    path("<str:doc_id>/editar", views.umbrales_editar, name="umbrales_editar"),
    path("<str:doc_id>/eliminar", views.umbrales_eliminar, name="umbrales_eliminar"),
]
