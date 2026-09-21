from __future__ import annotations

import re

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from apps.core.auth_backend import AnonymousCouchbaseUser, CouchbaseUser


POST_FORM_RE = re.compile(
    r"(<form\b[^>]*method\s*=\s*(?:[\"']?post[\"']?)[^>]*>)(.*?)(</form>)",
    re.IGNORECASE | re.DOTALL,
)
CSRF_INPUT_RE = re.compile(r"name\s*=\s*[\"']csrfmiddlewaretoken[\"']", re.IGNORECASE)


def _wants_html_response(request) -> bool:
    accept = (request.headers.get("Accept") or "").lower()
    if "application/json" in accept:
        return False
    if "text/html" in accept or "*/*" in accept or not accept:
        return True
    return False


def _build_error_response(request, status_code: int, message: str) -> HttpResponse:
    response = render(
        request,
        "core/error.html",
        {"status_code": status_code, "title": f"Error {status_code}", "message": message},
        status=status_code,
    )
    response["Cache-Control"] = "no-store"
    return response


class GlobalHtmlErrorMiddleware:
    """
    Fuerza una plantilla de error homogénea para respuestas HTML.
    """

    ERROR_MESSAGES = {
        400: "La solicitud no es valida. Revisa los datos e intentalo de nuevo.",
        403: "No tienes permisos para acceder a esta pagina.",
        404: "La pagina que buscas no existe o ya no esta disponible.",
        500: "Ha ocurrido un error inesperado. Intentalo de nuevo en unos minutos.",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Http404:
            if not _wants_html_response(request):
                raise
            return _build_error_response(request, 404, self.ERROR_MESSAGES[404])
        except PermissionDenied:
            if not _wants_html_response(request):
                raise
            return _build_error_response(request, 403, self.ERROR_MESSAGES[403])
        except SuspiciousOperation:
            if not _wants_html_response(request):
                raise
            return _build_error_response(request, 400, self.ERROR_MESSAGES[400])
        except Exception:
            if not _wants_html_response(request):
                raise
            return _build_error_response(request, 500, self.ERROR_MESSAGES[500])

        if response.status_code not in self.ERROR_MESSAGES:
            return response

        content_type = (response.get("Content-Type") or "").lower()
        if "application/json" in content_type:
            return response
        if not _wants_html_response(request):
            return response

        return _build_error_response(request, response.status_code, self.ERROR_MESSAGES[response.status_code])


class LegacyCsrfFormInjectionMiddleware:
    """
    Inserta csrfmiddlewaretoken en formularios POST HTML legacy.

    Permite mantener plantillas HTML heredadas (string-built) sin romper CSRF.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return response

        if not hasattr(response, "content"):
            return response

        try:
            html = response.content.decode(response.charset or "utf-8", errors="replace")
        except Exception:
            return response

        if "method=\"post\"" not in html.lower() and "method='post'" not in html.lower() and "method=post" not in html.lower():
            return response

        token = get_token(request)

        def repl(match: re.Match) -> str:
            form_open = match.group(1)
            form_body = match.group(2)
            form_close = match.group(3)
            # No duplicar si el formulario ya trae token.
            if CSRF_INPUT_RE.search(form_body):
                return f"{form_open}{form_body}{form_close}"
            return (
                f'{form_open}\n<input type="hidden" name="csrfmiddlewaretoken" value="{token}">'
                f"{form_body}{form_close}"
            )

        html = POST_FORM_RE.sub(repl, html)

        response.content = html.encode(response.charset or "utf-8")
        if "Content-Length" in response:
            response["Content-Length"] = str(len(response.content))
        return response


class CouchbaseAuthenticationMiddleware:
    """
    Authentication middleware sin dependencia de auth_user.
    Lee usuario/rol desde sesión firmada.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Django admin depends on contrib.auth User semantics (numeric pk).
        # Keep admin requests on Django's native anonymous/auth flow.
        if request.path.startswith("/admin"):
            request.user = AnonymousUser()
            return self.get_response(request)

        username = (request.session.get("cb_username") or "").strip()
        role = (request.session.get("cb_role") or "usuario").strip() or "usuario"
        if username:
            request.user = CouchbaseUser(username=username, role=role)
        else:
            request.user = AnonymousCouchbaseUser()
        return self.get_response(request)

