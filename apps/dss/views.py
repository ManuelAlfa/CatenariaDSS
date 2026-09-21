"""
Vista hub del módulo DSS (Decision Support System).

Muestra las dos opciones que cuelgan de DSS:
  - Consultas         -> /consultar-datos
  - Analítica Actual  -> /analitica/actual
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.core.views import _current_role, _get_error_param


@login_required
def dss(request: HttpRequest) -> HttpResponse:
    role = _current_role(request)
    return render(
        request,
        "dss/dss.html",
        {"error": _get_error_param(request), "role": role},
    )
