from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.login, name="login"),
    path("login", views.login_post, name="login_post"),
    path("logout", views.logout, name="logout"),
    path("logout/", views.logout),
    path("entrada", views.entrada, name="entrada"),
    path("configuracion", views.configuracion, name="configuracion"),
    path("cambiar-password", views.cambiar_password, name="cambiar_password"),
    path("restablecer-password", views.restablecer_password, name="restablecer_password"),
    path("descargar-pdf-kpis", views.descargar_pdf_kpis, name="descargar_pdf_kpis"),
]
