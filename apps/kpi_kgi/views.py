"""
Vista hub del módulo Sistemas de KPI / KGI.

Muestra las dos opciones que cuelgan de KPI / KGI:
  - KPIs / Indicadores    -> /filtros
  - Analítica Predictiva  -> /analitica/predictiva
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.core.views import _current_role, _get_error_param


@login_required
def kpi_kgi(request: HttpRequest) -> HttpResponse:
    role = _current_role(request)
    return render(
        request,
        "kpi_kgi/kpi_kgi.html",
        {"error": _get_error_param(request), "role": role},
    )
