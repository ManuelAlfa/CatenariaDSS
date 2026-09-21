from django.urls import path

from . import views

app_name = "dss"

urlpatterns = [
    path("", views.dss, name="dss"),
]
