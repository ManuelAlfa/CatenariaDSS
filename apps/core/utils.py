"""
Utilidades compartidas para todas las apps.
Funciones comunes para Couchbase, roles, y utilidades HTTP.
"""
from __future__ import annotations

from functools import lru_cache
from html import escape
import json
import os
import re
import subprocess
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

from couchbase.exceptions import (
    CouchbaseException,
    DocumentExistsException,
    DocumentNotFoundException,
)
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from apps.core.couchbase_client import connection

from apps.core.messages import GENERIC, INDICADORES, OPERACIONES, TRAMOS, UMBRALES, UMBRALES_CODES, USUARIOS


@lru_cache(maxsize=1)
def _cb_ctx() -> Tuple[object, str]:
    cluster, bucket_name, scope_name = connection("entorno")
    clausula_from = f"FROM `{bucket_name}`.`{scope_name}`."
    return cluster, clausula_from


@lru_cache(maxsize=1)
def _cb_bucket_scope() -> Tuple[object, str, str, str]:
    cluster, bucket_name, scope_name = connection("entorno")
    clausula_from = f"FROM `{bucket_name}`.`{scope_name}`."
    return cluster, bucket_name, scope_name, clausula_from


def _get_error_param(request: HttpRequest) -> str | None:
    raw_error = request.GET.get("error")
    return escape(raw_error) if raw_error else None


def _redirect_303(location: str) -> HttpResponse:
    resp = HttpResponse(status=303)
    resp["Location"] = location
    return resp


ROLE_ADMIN = "administrador"
ROLE_LICITADOR = "licitador"
ROLE_ESTANDAR = "usuario"


def _normalize_role(raw_role: str) -> str:
    role = (raw_role or "").strip().lower()
    if role in ("administrador", "admin"):
        return ROLE_ADMIN
    if role in ("licitador",):
        return ROLE_LICITADOR
    if role in ("usuario estandar", "usuario estándar", "usuario_estandar", "usuario"):
        return ROLE_ESTANDAR
    return ROLE_ESTANDAR


def _current_role(request: HttpRequest) -> str:
    if not request.user.is_authenticated:
        return ROLE_ESTANDAR
    for group_name in request.user.groups.values_list("name", flat=True):
        normalized = _normalize_role(str(group_name))
        if normalized == ROLE_ADMIN:
            return ROLE_ADMIN
        if normalized == ROLE_LICITADOR:
            return ROLE_LICITADOR
    return ROLE_ESTANDAR


def _require_any_role(request: HttpRequest, allowed_roles: set[str]) -> HttpResponse | None:
    if _current_role(request) in allowed_roles:
        return None
    return _redirect_303("/entrada?error=" + quote("No tienes permisos para acceder a esta sección"))


def _remove_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return text
    end = text.find(end_marker, start)
    if end == -1:
        return text
    return text[:start] + text[end:]


def _apply_role_visibility(html: str | bytes, role: str) -> str | bytes:
    is_bytes = isinstance(html, (bytes, bytearray))
    text = html.decode("utf-8", errors="ignore") if is_bytes else html

    # Normaliza navbar legacy en todas las páginas HTML.
    text = text.replace('<a class="navbar-brand text-white" href="#">', '<a class="navbar-brand text-white" href="/entrada">')
    text = text.replace('<a class="navbar-brand text-white">', '<a class="navbar-brand text-white" href="/entrada">')
    text = text.replace(
        'class="collapse d-flex justify-content-center navbar-collapse"',
        'class="collapse navbar-collapse justify-content-center"',
    )
    text = text.replace(
        'class="collapse navbar-collapse justify-content-end pe-lg-5"',
        'class="collapse navbar-collapse justify-content-center"',
    )
    if "</head>" in text and "/* NAVBAR_GLOBAL_FIX */" not in text:
        text = text.replace(
            "</head>",
            """<style>
/* NAVBAR_GLOBAL_FIX */
.navbar-nav .nav-link { display: flex; align-items: center; text-align: center; min-height: 40px; }
.navbar-nav { gap: 0.75rem; }
@media (min-width: 992px) {
  .navbar .container-fluid { position: relative; display: flex; align-items: center; }
  .navbar .container-fluid .navbar-collapse {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    flex-grow: 0;
    width: max-content;
  }
  .navbar .navbar-right-extra {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 16px;
    padding-left: 24px;
  }
}
</style>
<script>
/* NAVBAR_GLOBAL_FIX */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('nav.navbar').forEach(function (nav) {
    var container = nav.querySelector('.container-fluid');
    if (!container) return;

    var rightDiv = nav.querySelector(':scope > div.d-flex.ms-auto, :scope > div.d-flex.ms-auto.me-2');
    var rightImg = nav.querySelector(':scope > img[alt="solutia"], :scope > img[src*="solutia"]');

    if (rightImg || rightDiv) {
      var wrap = document.createElement('div');
      wrap.className = 'navbar-right-extra';
      if (rightImg) wrap.appendChild(rightImg);
      if (rightDiv) wrap.appendChild(rightDiv);
      container.appendChild(wrap);
    }
  });
});
</script>
</head>""",
        )

    # NOTA: los antiguos parches de inyección de "Inicio" y "Alertas" en el nav
    # se han eliminado. El nav unificado (NAV_HTML / core/_nav.html) ya incluye
    # ambos enlaces, así que inyectarlos aquí los duplicaba.

    if role == ROLE_ADMIN:
        return text.encode("utf-8") if is_bytes else text

    if role == ROLE_ESTANDAR:
        text = re.sub(r'<a[^>]*href="/configuracion"[^>]*>.*?</a>', "", text, flags=re.IGNORECASE | re.DOTALL)

    if role == ROLE_LICITADOR:
        text = re.sub(r'<a[^>]*href="/usuarios"[^>]*>.*?</a>', "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<a[^>]*href="/operaciones"[^>]*>.*?</a>', "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<a[^>]*href="/alertas"[^>]*>.*?</a>', "", text, flags=re.IGNORECASE | re.DOTALL)
        # En Configuración, licitador solo debe ver Tramos y Umbrales.
        text = _remove_block(text, "<!-- Tarjeta Operaciones -->", "<!-- Tarjeta Tramos -->")
        text = _remove_block(text, "<!-- Tarjeta Usuarios -->", '<div style="display:flex; justify-content: center;">')
        text = re.sub(r'<button[^>]*id="btn-sync"[\s\S]*?</button>', "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<p[^>]*id="texto-estado"[\s\S]*?</p>', "", text, flags=re.IGNORECASE | re.DOTALL)

    if is_bytes:
        return text.encode("utf-8")
    return text


def _html_response(request: HttpRequest, html: str | bytes) -> HttpResponse:
    return HttpResponse(_apply_role_visibility(html, _current_role(request)), content_type="text/html; charset=utf-8")


def _obtener_usuarios_acceso() -> list[dict[str, Any]]:
    cluster, bucket_name, scope_name, clausula_from = _cb_bucket_scope()
    query = (
        "SELECT META(u).id AS doc_id, u.usuario, u.rol, u.fecha_creacion "
        + clausula_from
        + "`Maestro_Usuarios_Django` AS u ORDER BY u.usuario"
    )
    try:
        rows = cluster.query(query)
        return [dict(r) for r in rows]
    except Exception:
        return []


def _validar_password_nueva(password: str) -> list[str]:
    errores: list[str] = []
    if len(password) < 10:
        errores.append("Debe tener al menos 10 caracteres.")
    if not re.search(r"[A-Z]", password):
        errores.append("Debe incluir al menos una letra mayúscula.")
    if not re.search(r"[a-z]", password):
        errores.append("Debe incluir al menos una letra minúscula.")
    if not re.search(r"\d", password):
        errores.append("Debe incluir al menos un número.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errores.append("Debe incluir al menos un símbolo.")
    return errores


estado_sync_state: dict[str, Any] = {"trabajando": False, "mensaje": ""}


def _tarea_en_segundo_plano() -> None:
    estado_sync_state["trabajando"] = True
    estado_sync_state["mensaje"] = ""
    try:
        subprocess.run(["python3", "scripts/exportar_couchbase.py"], check=True, capture_output=True, text=True)
        estado_sync_state["mensaje"] = "¡Base de datos sincronizada con éxito!"
    except subprocess.CalledProcessError as e:
        estado_sync_state["mensaje"] = f"Error en el script: {e.stderr}"
    except Exception as e:  # noqa: BLE001
        estado_sync_state["mensaje"] = f"fsfsfsfsfsfs: {str(e)}"
    finally:
        estado_sync_state["trabajando"] = False


def _range_param_single(value: str) -> list[str]:
    s = (value or "").strip().replace(" ", "")
    if not s:
        return []
    if "," in s:
        a, b = s.split(",", 1)
    elif "-" in s:
        a, b = s.split("-", 1)
    else:
        a = b = s
    return [a, b]
