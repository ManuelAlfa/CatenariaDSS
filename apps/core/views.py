from __future__ import annotations

from functools import lru_cache
from html import escape
import json
import os
import re
import subprocess
import sys
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
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from apps.core.couchbase_client import connection

from apps.core.html_legacy import (
    page_consultar_datos_filtros,
    page_configuracion,
    page_filtros,
    page_consultar_datos_formularios_resultados,
    page_consultar_datos_incidencias_resultados,
    page_consultar_datos_inspecciones_resultados,
    page_consultar_datos_mediciones_resultados,
    page_operaciones,
    page_tramos,
    page_umbrales,
    page_usuarios,
    page_modal_incidencia_detalle,
    page_modal_incidencias_medicion,
    page_modal_medicion_detalle,
    page_indicadores_operativa_resultados,
    page_alertas,
)
from apps.alertas.services import (
    buscar_alertas_agrupadas,
    contar_alertas_pendientes,
    contar_alertas_resumen,
    contar_fechas_alertas,
    marcar_revision_incidencia,
    POR_PAGINA_ALERTAS,
)

from apps.consultas.calculo import (
    LIMITE_AVISO_CONSULTA_GRANDE,
    page_confirmacion_consulta_grande,
    obtener_todos_los_datos,
    calcular_indicadores,
    pintar,
    pintar_incidencias,
)

from apps.core.messages import GENERIC, INDICADORES, OPERACIONES, TRAMOS, UMBRALES, UMBRALES_CODES, USUARIOS

from apps.core.validators import validar_umbral_doc

from apps.consultas.services import (
    buscar_formularios,
    buscar_incidencia_por_doc_id,
    buscar_incidencias_agrupadas,
    buscar_incidencias_por_medicion,
    buscar_inspecciones,
    buscar_medicion_por_clave,
    buscar_mediciones,
    consulta_supera_limite,
)
from apps.consultas.geolocalizacion import (
    construir_mensaje_parametros,
    resolver_mapa_por_ambito_geografico,
    resolver_tramos_por_cuadrantes,
    resolver_tramo_por_ambito_geografico,
)
from apps.consultas.indicadores import obtener_indicadores_operativa
from apps.analitica.services import (
    calcular_indicadores_predictivos,
    generar_recomendaciones,
    obtener_proyecciones_simplificadas,
    proyectar_indicador_geometrico,
    proyectar_incidencias_poisson,
)
from apps.operaciones.services import (
    actualizar_subgrupo,
    crear_grupo,
    crear_subgrupo,
    eliminar_subgrupo,
    obtener_grupos_por_parte,
    obtener_partes,
    obtener_subgrupos,
    obtener_todas_operaciones,
)
from apps.tramos.services import (
    actualizar_tramo,
    crear_tramo,
    eliminar_tramo,
    obtener_rango_fechas_incidencias_postgres,
    obtener_tramos,
    obtener_tramos_con_incidencias,
    obtener_tramos_crud,
    obtener_vias_por_tramo,
)
from apps.umbrales.services import (
    actualizar_umbral,
    crear_umbral,
    eliminar_umbral,
    existe_umbral_con_clave,
    obtener_umbrales_crud,
)
from apps.usuarios.services import (
    actualizar_usuario,
    crear_usuario,
    eliminar_usuario,
    obtener_personas,
)


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


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    """
    Error CSRF amigable en lugar de la página técnica de Django.
    """
    _ = reason  # mantenemos firma esperada por Django
    if request.user.is_authenticated:
        return _redirect_303("/entrada?error=" + quote("La sesión ha caducado. Recarga la página e inténtalo de nuevo."))
    return _redirect_303("/?error=" + quote("La sesión ha caducado. Vuelve a iniciar sesión."))


def render_error_page(request: HttpRequest, status_code: int, message: str) -> HttpResponse:
    return render(
        request,
        "core/error.html",
        {"status_code": status_code, "title": f"Error {status_code}", "message": message},
        status=status_code,
    )


def error_400(request: HttpRequest, exception=None) -> HttpResponse:
    _ = exception
    return render_error_page(request, 400, "La solicitud no es valida. Revisa los datos e intentalo de nuevo.")


def error_403(request: HttpRequest, exception=None) -> HttpResponse:
    _ = exception
    return render_error_page(request, 403, "No tienes permisos para acceder a esta pagina.")


def error_404(request: HttpRequest, exception=None) -> HttpResponse:
    _ = exception
    return render_error_page(request, 404, "La pagina que buscas no existe o ya no esta disponible.")


def error_500(request: HttpRequest) -> HttpResponse:
    return render_error_page(request, 500, "Ha ocurrido un error inesperado. Intentalo de nuevo en unos minutos.")


estado_sync_state: dict[str, Any] = {"trabajando": False, "mensaje": ""}


def _tarea_en_segundo_plano() -> None:
    estado_sync_state["trabajando"] = True
    estado_sync_state["mensaje"] = ""
    try:
        subprocess.run([sys.executable, "scripts/exportar_couchbase.py"], check=True, capture_output=True, text=True)
        estado_sync_state["mensaje"] = "¡Base de datos sincronizada con éxito!"
    except subprocess.CalledProcessError as e:
        estado_sync_state["mensaje"] = f"Error en el script: {e.stderr}"
    except Exception as e:  # noqa: BLE001
        estado_sync_state["mensaje"] = f"fsfsfsfsfsfs: {str(e)}"
    finally:
        estado_sync_state["trabajando"] = False


def login(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return _redirect_303("/entrada")
    return render(request, "core/login.html", {"error": request.GET.get("error", "")})


def login_post(request: HttpRequest) -> HttpResponse:
    """
    Login real con sesión Django.

    Soporta el formulario legacy: usuario/contraseña (con ñ).
    """
    if request.method != "POST":
        return _redirect_303("/")

    username = (request.POST.get("usuario") or request.POST.get("username") or "").strip()
    password = request.POST.get("password") or request.POST.get("contraseña") or ""

    user = authenticate(request, username=username, password=password)
    if user is None:
        request.session.flush()
        # Version original (mensaje siempre genérico):
        # return _redirect_303("/?error=" + quote("Usuario o contraseña incorrectos"))
        mensaje = "Usuario o contraseña incorrectos"
        if settings.DEBUG:
            motivo = getattr(request, "auth_error", None)
            if motivo:
                mensaje = f"{mensaje} [debug] usuario={username!r} motivo={motivo}"
        return _redirect_303("/?error=" + quote(mensaje))

    request.session["cb_username"] = user.username
    request.session["cb_role"] = getattr(user, "_role", "usuario")
    request.session["cb_authenticated"] = True
    if request.session.pop("pending_password_change", False):
        return _redirect_303("/cambiar-password")
    # from=login: indicador para que /entrada muestre el modal de alertas pendientes.
    return _redirect_303("/entrada?from=login")


def restablecer_password(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return _redirect_303("/cambiar-password")
    request.session["pending_password_change"] = True
    return _redirect_303(
        "/?error="
        + quote("Debes iniciar sesión para cambiar tu contraseña. Tras validarte, te llevaremos al formulario.")
    )


@login_required
def cambiar_password(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        actual = request.POST.get("password_actual", "") or ""
        nueva = request.POST.get("password_nueva", "") or ""
        confirmar = request.POST.get("password_confirmar", "") or ""

        if not actual or not nueva or not confirmar:
            return _redirect_303("/cambiar-password?error=" + quote("Todos los campos son obligatorios."))

        user = authenticate(request, username=request.user.username, password=actual)
        if user is None:
            return _redirect_303("/cambiar-password?error=" + quote("La contraseña actual no es correcta."))

        if nueva != confirmar:
            return _redirect_303("/cambiar-password?error=" + quote("La nueva contraseña y la confirmación no coinciden."))

        if actual == nueva:
            return _redirect_303("/cambiar-password?error=" + quote("La nueva contraseña debe ser diferente de la actual."))

        errores = _validar_password_nueva(nueva)
        if errores:
            return _redirect_303("/cambiar-password?error=" + quote(" ".join(errores)))

        cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
        try:
            coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
            doc = coll.get(request.user.username).content_as[dict]
            if not check_password(actual, str(doc.get("password_hash") or "")) and str(doc.get("password_hash") or ""):
                return _redirect_303("/cambiar-password?error=" + quote("No se pudo validar la contraseña actual."))
            doc["password_hash"] = make_password(nueva)
            doc.pop("password", None)
            coll.upsert(request.user.username, doc)
            return _redirect_303("/cambiar-password?success=" + quote("Contraseña actualizada correctamente."))
        except DocumentNotFoundException:
            return _redirect_303("/cambiar-password?error=" + quote("Usuario no encontrado."))
        except Exception as e:  # noqa: BLE001
            return _redirect_303("/cambiar-password?error=" + quote("Error al cambiar la contraseña: " + str(e)))

    return render(
        request,
        "core/cambiar_password.html",
        {
            "error": request.GET.get("error", ""),
            "success": request.GET.get("success", ""),
        },
    )


@login_required
def logout(request: HttpRequest) -> HttpResponse:
    request.session.flush()
    return _redirect_303("/")


@login_required
def entrada(request: HttpRequest) -> HttpResponse:
    role = _current_role(request)
    n_alertas = 0
    if role in (ROLE_ADMIN, ROLE_ESTANDAR):
        try:
            cluster, clausula_from = _cb_ctx()
            n_alertas = contar_alertas_pendientes(cluster, clausula_from)
        except Exception:
            pass
    # El modal de alertas solo se muestra cuando el usuario llega a /entrada
    # tras hacer login (?from=login) o al pulsar "Inicio" en el nav (?from=nav).
    # Si llega aquí desde un botón "Volver atrás" no debe mostrarse.
    came_from = (request.GET.get("from", "") or "").strip().lower()
    show_alerts_modal = came_from in ("login", "nav")
    return render(
        request,
        "core/entrada.html",
        {
            "error": _get_error_param(request),
            "role": role,
            "n_alertas": n_alertas,
            "show_alerts_modal": show_alerts_modal,
        },
    )


@login_required
def analitica_actual(request: HttpRequest) -> HttpResponse:
    role = _current_role(request)
    tramos: list[str] = ["110800020", "011000120", "110800040"]
    fecha_min_ymd = ""
    fecha_max_ymd = ""
    grafana_from = ""
    grafana_to = ""
    fecha_msg = ""

    try:
        cluster, clausula_from = _cb_ctx()
        tramos_cb = sorted(obtener_tramos_con_incidencias(cluster, clausula_from))
        if not tramos_cb:
            tramos_cb = sorted(obtener_tramos(cluster, clausula_from))
        if tramos_cb:
            tramos = tramos_cb
    except Exception:  # noqa: BLE001
        pass

    try:
        fecha_min_ymd, fecha_max_ymd, grafana_from, grafana_to = obtener_rango_fechas_incidencias_postgres()
        if not fecha_min_ymd or not fecha_max_ymd:
            fecha_msg = "No se pudo obtener el rango de fechas desde PostgreSQL. Revisa la configuracion de la base de datos."
    except Exception:  # noqa: BLE001
        fecha_msg = "Error leyendo fechas desde PostgreSQL."

    if fecha_min_ymd and not fecha_max_ymd:
        fecha_max_ymd = fecha_min_ymd
    if fecha_max_ymd and not fecha_min_ymd:
        fecha_min_ymd = fecha_max_ymd

    grafana_base_url = os.getenv("GRAFANA_BASE_URL", "https://grafana.catenaria-lab.com/d-solo/ad2q78k/catenaria")

    return render(
        request,
        "analitica/analitica_actual.html",
        {
            "error": _get_error_param(request),
            "role": role,
            "tramos": tramos,
            "fecha_min_ymd": fecha_min_ymd,
            "fecha_max_ymd": fecha_max_ymd,
            "grafana_from": grafana_from,
            "grafana_to": grafana_to,
            "fecha_msg": fecha_msg,
            "grafana_base_url": grafana_base_url,
        },
    )


@login_required
def analitica_predictiva(request: HttpRequest) -> HttpResponse:
    """
    Vista de Análisis Predictiva Avanzada.
    
    Dashboard profesional con proyecciones, métricas y análisis de tendencias.
    """
    role = _current_role(request)
    error = _get_error_param(request)
    
    # Parámetros de filtro
    tramo_seleccionado = request.GET.get("tramo", "")
    dias_proyeccion = int(request.GET.get("dias", 90))
    
    # Contexto para la nueva plantilla (espera variables específicas)
    contexto = {
        "error": error,
        "role": role,
        # Variables para selects de la plantilla
        "tramos": [],
        "selected_tramo": tramo_seleccionado,
        "vias": [],
        "selected_via": request.GET.get("via", ""),
        "selected_pk_min": request.GET.get("pk_min", ""),
        "selected_pk_max": request.GET.get("pk_max", ""),
        "selected_fecha_inicio": request.GET.get("fecha_inicio", ""),
        "selected_fecha_fin": request.GET.get("fecha_fin", ""),
        # Datos predictivos en formato JSON para la plantilla
        "predictive_data_json": json.dumps({
            "tramo": tramo_seleccionado,
            "via": request.GET.get("via", ""),
            "parametros": [],
            "calibration": {},
            "message": "Selecciona tramo, vía y fechas para calcular la predicción."
        }),
        # Mantener compatibilidad con código anterior
        "tramo_seleccionado": tramo_seleccionado,
        "dias_proyeccion": dias_proyeccion,
        "proyecciones": None,
        "recomendaciones": [],
        "tramos_disponibles": [],
        "info_tramo": None,
        "estadisticas": None,
        "ultima_actualizacion": None,
    }
    
    try:
        # Obtener conexión Couchbase
        cluster, bucket_name, scope_name, clausula_from = _cb_bucket_scope()
        
        # === OBTENER TRAMOS DESDE MAESTRO_TRAMOS ===
        # Usar exactamente la misma consulta que funciona en la pagina de filtros
        tramos_list = []
        try:
            # Consulta simple como en obtener_tramos()
            query_tramos = "SELECT DISTINCT id_tramo " + clausula_from + "`Maestro_Tramos` WHERE id_tramo IS NOT MISSING AND id_tramo IS NOT NULL ORDER BY id_tramo LIMIT 200;"
            resultado = cluster.query(query_tramos)
            tramos_ids = [str(row["id_tramo"]) for row in resultado]
            
            # Crear lista con los IDs - la plantilla espera 'tramos' como lista simple
            tramos_list = [{"id_tramo": tid, "id_via": "", "tipologia": "", "velocidad_max": ""} for tid in tramos_ids]
            contexto["tramos_disponibles"] = tramos_list
            contexto["tramos"] = tramos_ids  # Para el select de la plantilla
        except Exception as e:
            contexto["error_debug"] = f"Error cargando tramos: {str(e)}"
            tramos_list = []
        
        # Si no hay tramo seleccionado, usar el primero disponible
        if not tramo_seleccionado and tramos_list:
            tramo_seleccionado = tramos_list[0]["id_tramo"]
            contexto["tramo_seleccionado"] = tramo_seleccionado
        
        # Buscar info del tramo seleccionado y cargar vías
        if tramo_seleccionado:
            for t in tramos_list:
                if t["id_tramo"] == tramo_seleccionado:
                    contexto["info_tramo"] = t
                    break
            # Cargar vías del tramo para el select
            try:
                vias = obtener_vias_por_tramo(cluster, clausula_from, tramo_seleccionado)
                contexto["vias"] = vias
            except Exception:
                contexto["vias"] = []
        
        # === CALCULAR PROYECCIONES SI HAY TRAMO ===
        if tramo_seleccionado:
            # Cargar mediciones del tramo (usando la coleccion correcta: Medicion_Individual)
            query_mediciones = f"""
                SELECT m.fecha, m.altura_LAC, m.descentramiento, m.flecha, 
                       m.contraflecha, m.pendiente, m.variacion_pendiente,
                       m.id_via, m.pto_km
                {clausula_from}`Medicion_Individual` AS m
                WHERE m.id_tramo = $tramo 
                AND m.fecha IS NOT MISSING
                ORDER BY m.fecha DESC
                LIMIT 10000
            """
            
            mediciones = []
            try:
                mediciones_result = cluster.query(query_mediciones, tramo=tramo_seleccionado)
                mediciones = [dict(r) for r in mediciones_result]
                # Reordenar cronológicamente
                mediciones.reverse()
                contexto["ultima_actualizacion"] = mediciones[-1].get("fecha", "") if mediciones else None
                
                # DEBUG: Loguear valores crudos para diagnóstico
                if mediciones:
                    print(f"[DEBUG] Primera medicion cruda: {mediciones[0]}")
                    for campo in ["contraflecha", "flecha", "altura_LAC", "descentramiento"]:
                        val = mediciones[0].get(campo)
                        if val is not None:
                            print(f"[DEBUG] {campo} crudo={val}, tipo={type(val).__name__}")
            except Exception as e:
                contexto["error"] = f"Error cargando mediciones: {str(e)}"
            
            # Estadísticas descriptivas
            if mediciones:
                contexto["estadisticas"] = calcular_estadisticas_basicas(mediciones)
            
            # Cargar incidencias del tramo (coleccion correcta: Incidencias)
            query_incidencias = f"""
                SELECT i.fecha, i.tipo, i.nivel, i.valor_medido, i.valor_referencia
                {clausula_from}`Incidencias` AS i
                WHERE i.id_tramo = $tramo 
                AND i.fecha IS NOT MISSING
                ORDER BY i.fecha DESC
                LIMIT 5000
            """
            
            incidencias = []
            try:
                incidencias_result = cluster.query(query_incidencias, tramo=tramo_seleccionado)
                incidencias = [dict(r) for r in incidencias_result]
            except Exception:
                incidencias = []
            
            # Cargar umbrales desde Maestro_Umbrales
            umbrales = cargar_umbrales_tramo(cluster, clausula_from, tramo_seleccionado, contexto.get("info_tramo", {}))
            
            # Calcular proyecciones
            if mediciones and len(mediciones) >= 3:
                # Usar nuevo formato simplificado: solo valor + fecha
                proyecciones_simplificadas = obtener_proyecciones_simplificadas(
                    mediciones,
                    incidencias,
                    umbrales,
                    dias_proyeccion
                )
                contexto["proyecciones"] = proyecciones_simplificadas
                contexto["predictive_data_json"] = json.dumps(proyecciones_simplificadas)

                # Generar recomendaciones
                resultados_predictivos = calcular_indicadores_predictivos(
                    mediciones,
                    incidencias,
                    umbrales,
                    dias_proyeccion
                )
                recomendaciones = generar_recomendaciones_avanzadas(
                    resultados_predictivos,
                    contexto.get("info_tramo"),
                    len(mediciones)
                )
                contexto["recomendaciones"] = recomendaciones
            else:
                if mediciones:
                    contexto["error"] = f"Datos insuficientes: solo {len(mediciones)} mediciones (mínimo 3 requeridas)"
                else:
                    contexto["error"] = "No hay datos de mediciones para este tramo"
    
    except Exception as e:
        contexto["error"] = f"Error general: {str(e)}"
        import traceback
        contexto["error_debug"] = traceback.format_exc()
    
    return render(request, "analitica/analitica_predictiva.html", contexto)


def calcular_estadisticas_basicas(mediciones: List[Dict]) -> Dict:
    """Calcula estadísticas descriptivas básicas."""
    campos = ["altura_LAC", "descentramiento", "flecha", "contraflecha", "pendiente"]
    stats = {}
    
    for campo in campos:
        valores = [float(m.get(campo, 0)) for m in mediciones if m.get(campo) is not None]
        if valores:
            import numpy as np
            stats[campo] = {
                "media": round(np.mean(valores), 4),
                "std": round(np.std(valores), 4),
                "min": round(min(valores), 4),
                "max": round(max(valores), 4),
                "count": len(valores)
            }
    
    return stats


def _extraer_valor_numerico(valor, default=0.0):
    """Extrae un valor numérico de varios formatos posibles (lista, string, número)."""
    if valor is None:
        return default
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, list) and len(valor) > 0:
        return _extraer_valor_numerico(valor[0], default)
    if isinstance(valor, str):
        try:
            return float(valor.replace(",", "."))
        except (ValueError, TypeError):
            return default
    return default


def cargar_umbrales_tramo(cluster, clausula_from: str, id_tramo: str, info_tramo: Dict) -> Dict:
    """Carga umbrales específicos para el tramo desde Maestro_Umbrales.
    
    Los valores del DB están en las mismas unidades brutas que las mediciones,
    por lo que se aplica la misma normalización que _normalizar_unidades_servicio:
      - altura: ya en metros (4.xx m)
      - flecha, contraflecha, descentramiento: mm si v>10 (/1000), cm si v>1 (/100)
      - pendiente, var_pendiente: ‰ (1 < v ≤ 10 → /100)
    """
    def _normalizar_umbral(valor_raw, campo):
        """Aplica la misma normalización que las mediciones."""
        try:
            v = float(valor_raw)
        except (TypeError, ValueError):
            return None
        if campo == "altura_LAC":
            # Ya en metros
            return v
        elif campo in ("flecha", "contraflecha", "descentramiento"):
            if v > 10:
                return v / 1000.0   # mm → m
            elif v > 1:
                return v / 100.0    # cm → m
            return v
        elif campo in ("pendiente", "variacion_pendiente"):
            if v > 10:
                return v / 1000.0
            elif v > 1:
                return v / 100.0    # ‰ normalizado igual que mediciones
            return v
        return v

    def _umbral_nivel(row, nivel, campo, default):
        raw = row.get(f"valores_{nivel}")
        if raw is None:
            return default
        # Tomar el límite inferior del rango (inicio del nivel)
        if isinstance(raw, list) and len(raw) > 0:
            raw = raw[0]
        v = _normalizar_umbral(raw, campo)
        return v if v is not None else default

    # Umbrales por defecto (en unidades normalizadas = metros / fracción)
    # Solo se usan si la DB no devuelve datos para ese campo
    umbrales_default = {
        "altura_LAC":        {"N1": 4.55, "N2": 4.50, "N3": 4.45, "N4": 4.40},
        "descentramiento":   {"N1": 0.023, "N2": 0.033, "N3": 0.040, "N4": 0.045},
        "flecha":            {"N1": 0.0115, "N2": 0.1085, "N3": 0.1275, "N4": 0.15},
        "contraflecha":      {"N1": 0.045, "N2": 0.085, "N3": 0.135, "N4": 0.999},
        "pendiente":         {"N1": 0.025, "N2": 0.035, "N3": 0.0475, "N4": 0.055},
        "variacion_pendiente": {"N1": 0.017, "N2": 0.020, "N3": 0.035, "N4": 0.045},
    }

    try:
        tipologia = info_tramo.get("tipologia", "CA-160") if isinstance(info_tramo, dict) else "CA-160"
        try:
            velocidad = int(float(str(info_tramo.get("velocidad_max", "160")).replace("km/h", "").strip()))
        except (TypeError, ValueError):
            velocidad = 160

        # ── Indicadores con tipología (altura, flecha, contraflecha, descentramiento) ──
        query_tip = f"""
            SELECT u.tipo, u.valores_N1, u.valores_N2, u.valores_N3, u.valores_N4
            {clausula_from}`Maestro_Umbrales` AS u
            WHERE u.tipologia = $tipologia
            LIMIT 100
        """
        seen = set()
        for row in cluster.query(query_tip, tipologia=tipologia):
            if not isinstance(row, dict):
                continue
            tipo = str(row.get("tipo", "")).lower()
            # Evitar procesar duplicados (DB tiene entradas repetidas)
            key = tipo
            if key in seen:
                continue
            seen.add(key)

            if tipo == "altura":
                umbrales_default["altura_LAC"] = {
                    "N1": _umbral_nivel(row, "N1", "altura_LAC", 4.55),
                    "N2": _umbral_nivel(row, "N2", "altura_LAC", 4.50),
                    "N3": _umbral_nivel(row, "N3", "altura_LAC", 4.45),
                    "N4": _umbral_nivel(row, "N4", "altura_LAC", 4.40),
                }
            elif tipo == "flecha":
                umbrales_default["flecha"] = {
                    "N1": _umbral_nivel(row, "N1", "flecha", 0.0115),
                    "N2": _umbral_nivel(row, "N2", "flecha", 0.1085),
                    "N3": _umbral_nivel(row, "N3", "flecha", 0.1275),
                    "N4": _umbral_nivel(row, "N4", "flecha", 0.15),
                }
            elif tipo == "contraflecha":
                umbrales_default["contraflecha"] = {
                    "N1": _umbral_nivel(row, "N1", "contraflecha", 0.045),
                    "N2": _umbral_nivel(row, "N2", "contraflecha", 0.085),
                    "N3": _umbral_nivel(row, "N3", "contraflecha", 0.135),
                    "N4": _umbral_nivel(row, "N4", "contraflecha", 0.999),
                }
            elif tipo == "descentramiento_recta":
                umbrales_default["descentramiento"] = {
                    "N1": _umbral_nivel(row, "N1", "descentramiento", 0.023),
                    "N2": _umbral_nivel(row, "N2", "descentramiento", 0.033),
                    "N3": _umbral_nivel(row, "N3", "descentramiento", 0.040),
                    "N4": _umbral_nivel(row, "N4", "descentramiento", 0.045),
                }

        # ── Pendiente y variación de pendiente (filtradas por velocidad) ──
        query_vel = f"""
            SELECT u.tipo, u.valores_N1, u.valores_N2, u.valores_N3, u.valores_N4
            {clausula_from}`Maestro_Umbrales` AS u
            WHERE u.tipo IN ["pendiente", "var_pendiente"]
            AND u.velocidad = $velocidad
            LIMIT 10
        """
        seen_vel = set()
        for row in cluster.query(query_vel, velocidad=velocidad):
            if not isinstance(row, dict):
                continue
            tipo = str(row.get("tipo", "")).lower()
            if tipo in seen_vel:
                continue
            seen_vel.add(tipo)

            if tipo == "pendiente":
                umbrales_default["pendiente"] = {
                    "N1": _umbral_nivel(row, "N1", "pendiente", 0.025),
                    "N2": _umbral_nivel(row, "N2", "pendiente", 0.035),
                    "N3": _umbral_nivel(row, "N3", "pendiente", 0.0475),
                    "N4": _umbral_nivel(row, "N4", "pendiente", 0.055),
                }
            elif tipo == "var_pendiente":
                umbrales_default["variacion_pendiente"] = {
                    "N1": _umbral_nivel(row, "N1", "variacion_pendiente", 0.017),
                    "N2": _umbral_nivel(row, "N2", "variacion_pendiente", 0.020),
                    "N3": _umbral_nivel(row, "N3", "variacion_pendiente", 0.035),
                    "N4": _umbral_nivel(row, "N4", "variacion_pendiente", 0.045),
                }

    except Exception as e:
        print(f"[DEBUG] Error cargando umbrales: {e}")

    print(f"[DEBUG] Umbrales finales para {id_tramo}: {umbrales_default}")
    return umbrales_default


def generar_recomendaciones_avanzadas(
    resultados: Dict, 
    info_tramo: Optional[Dict],
    num_mediciones: int
) -> List[str]:
    """Genera recomendaciones más detalladas y profesionales."""
    recomendaciones = []
    
    # Información del tramo
    if info_tramo:
        tipologia = info_tramo.get("tipologia", "Desconocida")
        vel_max = info_tramo.get("velocidad_max", "N/A")
        recomendaciones.append(
            f"📍 Tramo {info_tramo.get('id_tramo', '')} - Tipología: {tipologia}, Vel. max: {vel_max} km/h"
        )
    
    # Calidad de datos
    if num_mediciones < 30:
        recomendaciones.append(
            f"⚠️ Poca historia de datos ({num_mediciones} mediciones). "
            f"Las proyecciones tienen baja confianza. Se recomienda >30 días de datos."
        )
    elif num_mediciones >= 90:
        recomendaciones.append(
            f"✅ Base de datos sólida ({num_mediciones} mediciones). "
            f"Proyecciones con alta confianza estadística."
        )
    else:
        recomendaciones.append(
            f"ℹ️ Base de datos aceptable ({num_mediciones} mediciones). "
            f"Proyecciones con confianza media."
        )
    
    # Alertas de umbrales
    alertas_criticas = [a for a in resultados.get("alertas", []) if a.get("dias", 999) <= 7]
    alertas_importantes = [a for a in resultados.get("alertas", []) if 7 < a.get("dias", 999) <= 30]
    
    if alertas_criticas:
        recomendaciones.append(
            f"🚨 URGENTE: {len(alertas_criticas)} indicador(es) superarán umbrales críticos en <7 días. "
            f"Programar inspección inmediata."
        )
    
    if alertas_importantes:
        recomendaciones.append(
            f"⚠️ ATENCIÓN: {len(alertas_importantes)} indicador(es) requerirán vigilancia en 7-30 días. "
            f"Planificar mantenimiento preventivo."
        )
    
    # Análisis de tendencias
    for indicador, datos in resultados.get("indicadores_geometricos", {}).items():
        tendencia = datos.get("tendencia", "estable")
        r2 = datos.get("r2", 0)
        
        if tendencia == "creciente" and r2 > 0.8:
            recomendaciones.append(
                f"📈 {indicador.upper()}: Deterioro significativo (R²={r2:.2f}). "
                f"Tasa de cambio: {datos.get('pendiente_diaria', 0):.4f} unidades/día. "
                f"Revisar estado de componentes."
            )
        elif tendencia == "decreciente" and r2 > 0.8:
            recomendaciones.append(
                f"📉 {indicador.upper()}: Mejora consistente (R²={r2:.2f}). "
                f"Mantener protocolos actuales de mantenimiento."
            )
    
    # Incidencias
    total_esperadas = sum(
        d.get("prediccion_30d", 0) 
        for d in resultados.get("incidencias", {}).values()
    )
    if total_esperadas > 10:
        recomendaciones.append(
            f"🔴 Incidencias: Se proyectan {total_esperadas:.1f} eventos en 30 días. "
            f"Considerar aumentar frecuencia de inspecciones."
        )
    elif total_esperadas > 5:
        recomendaciones.append(
            f"🟡 Incidencias: Se proyectan {total_esperadas:.1f} eventos en 30 días. "
            f"Vigilancia estándar recomendada."
        )
    else:
        recomendaciones.append(
            f"🟢 Incidencias: Solo {total_esperadas:.1f} eventos esperados en 30 días. "
            f"Estado estable."
        )
    
    if not recomendaciones:
        recomendaciones.append("✅ No se detectan anomalías. Mantener vigilancia habitual.")
    
    return recomendaciones


def _safe_get(diccionario, clave, default=None):
    """Obtiene valor de forma segura, manejando listas y otros tipos."""
    if not isinstance(diccionario, dict):
        return default
    return diccionario.get(clave, default)


def _normalizar_unidades(valor, campo):
    """
    Normaliza unidades de mediciones.
    Algunos campos en Couchbase pueden estar en mm/cm cuando deberían estar en metros.
    """
    if valor is None:
        return None
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return valor
    
    # Campos que típicamente están en el rango de 0.001-0.1 metros (1-100 mm)
    campos_milimetricos = ["contraflecha", "flecha", "descentramiento", "variacion_pendiente"]
    
    # Si el valor es > 1.0 para estos campos, probablemente está en mm o cm
    if campo in campos_milimetricos:
        if v > 1000:
            # Probablemente está en milímetros, convertir a metros
            return v / 1000.0
        elif v > 100:
            # Probablemente está en centímetros, convertir a metros  
            return v / 100.0
        elif v > 10:
            # Podría estar en decímetros o mal escalado
            return v / 10.0
    
    # Altura LAC típicamente está entre 4-6 metros
    if campo == "altura_LAC":
        if v > 1000:
            # Probablemente en milímetros
            return v / 1000.0
        elif v > 100:
            # Probablemente en centímetros
            return v / 100.0
    
    return v


def _convertir_a_formato_plantilla(
    resultados: Dict,
    mediciones: List[Dict],
    umbrales: Dict,
    tramo: str,
    via: str,
    dias_proyeccion: int
) -> Dict:
    """Convierte los resultados del servicio al formato JSON que espera la plantilla."""
    from datetime import datetime, timedelta
    
    # Mapeo de campos a nombres amigables
    campo_labels = {
        "altura_LAC": ("Altura LAC", "m"),
        "descentramiento": ("Descentramiento", "m"),
        "flecha": ("Flecha", "m"),
        "contraflecha": ("Contraflecha", "m"),
        "pendiente": ("Pendiente", "‰/m"),
    }
    
    parametros = []
    
    # Verificar que resultados sea dict
    if not isinstance(resultados, dict):
        resultados = {}
    
    indicadores = _safe_get(resultados, "indicadores_geometricos", {})
    if not isinstance(indicadores, dict):
        indicadores = {}
    
    # Procesar indicadores geométricos
    for campo, datos in indicadores.items():
        if campo not in campo_labels:
            continue
        
        if not isinstance(datos, dict):
            datos = {}
            
        label, unit = campo_labels[campo]
        
        # Extraer valores históricos de las mediciones
        valores_historicos = []
        fechas_historicas = []
        for m in mediciones:
            if not isinstance(m, dict):
                continue
            val = m.get(campo)
            if val is not None:
                try:
                    # Normalizar unidades (mm/cm -> m)
                    val_normalizado = _normalizar_unidades(val, campo)
                    valores_historicos.append(float(val_normalizado))
                    fechas_historicas.append(str(m.get("fecha", "")))
                    # DEBUG: Log primer valor
                    if len(valores_historicos) == 1:
                        print(f"[DEBUG] _convertir_a_formato: {campo} crudo={val} normalizado={val_normalizado}")
                except (ValueError, TypeError):
                    pass
        
        # Calcular niveles N para cada punto histórico
        n_levels_hist = []
        thr = _safe_get(umbrales, campo, {})
        if not isinstance(thr, dict):
            thr = {}
        for val in valores_historicos:
            n = _calcular_nivel(val, thr)
            n_levels_hist.append(n)
        
        # Preparar forecast (proyección) - el servicio devuelve "predicciones" no "proyeccion"
        predicciones = datos.get("predicciones", [])
        if not isinstance(predicciones, list):
            predicciones = []
        print(f"[DEBUG] {campo}: datos.keys={list(datos.keys())}, predicciones count={len(predicciones)}")
        valores_proy = []
        for p in predicciones:
            if isinstance(p, dict):
                v = p.get("valor", 0)
                try:
                    valores_proy.append(float(v))
                except (ValueError, TypeError):
                    valores_proy.append(0.0)
        
        # Extraer fechas de las predicciones del servicio
        fechas_proy = []
        for p in predicciones:
            if isinstance(p, dict):
                fecha = p.get("fecha", "")
                if fecha:
                    # Extraer solo la parte de fecha (YYYY-MM-DD)
                    fecha_str = str(fecha).split("T")[0] if "T" in str(fecha) else str(fecha)
                    fechas_proy.append(fecha_str)
        
        # Si no hay fechas, usar fechas generadas
        if not fechas_proy:
            hoy = datetime.now()
            fechas_proy = [(hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, len(valores_proy) + 1)]
        
        # Calcular IC 95% simple (±1.96 * std de residuos)
        valores_lower = []
        valores_upper = []
        try:
            mse = float(datos.get("mse", 0) or 0)
            std_residual = mse ** 0.5
        except (ValueError, TypeError):
            std_residual = 0.0
        
        for val in valores_proy:
            try:
                valores_lower.append(max(0.0, val - 1.96 * std_residual))
                valores_upper.append(val + 1.96 * std_residual)
            except (ValueError, TypeError):
                valores_lower.append(0.0)
                valores_upper.append(0.0)
        
        # Calcular niveles N para proyección
        n_levels_proy = []
        for val in valores_proy:
            n = _calcular_nivel(val, thr)
            n_levels_proy.append(n)
        
        # Calcular distribución de niveles - lista de 5 elementos [N0, N1, N2, N3, N4]
        dist_counts = [0, 0, 0, 0, 0]
        for n in n_levels_hist:
            try:
                idx = int(n)
                if 0 <= idx < 5:
                    dist_counts[idx] += 1
            except (ValueError, TypeError):
                pass
        
        # KPIs
        valor_actual = valores_historicos[-1] if valores_historicos else 0.0
        valor_proyectado = valores_proy[-1] if valores_proy else valor_actual
        tendencia = str(datos.get("tendencia", "estable"))
        trend_map = {"creciente": "subida", "decreciente": "bajada", "estable": "estable"}
        
        # Construir thresholds de forma segura
        def build_threshold(nivel_val):
            if nivel_val is None:
                return None
            try:
                nv = float(nivel_val)
                return {"min": nv * 0.9, "max": nv}
            except (ValueError, TypeError):
                return None
        
        thresholds = {
            "N1": build_threshold(thr.get("N1")),
            "N2": build_threshold(thr.get("N2")),
            "N3": build_threshold(thr.get("N3")),
            "N4": build_threshold(thr.get("N4")),
            "ref": None,
        }
        
        param = {
            "key": str(campo),
            "label": label,
            "unit": unit,
            "history": {
                "labels": fechas_historicas[-30:] if len(fechas_historicas) > 30 else fechas_historicas,
                "values_avg": valores_historicos[-30:] if len(valores_historicos) > 30 else valores_historicos,
                "n_level_max": n_levels_hist[-30:] if len(n_levels_hist) > 30 else n_levels_hist,
            },
            "forecast": {
                "labels": fechas_proy,
                "values": valores_proy,
                "values_lower": valores_lower,
                "values_upper": valores_upper,
                "n_level_forecast": n_levels_proy,
                "horizon_days": int(dias_proyeccion),
            },
            "kpis": {
                "current_value": float(valor_actual),
                "projected_value": float(valor_proyectado),
                "current_n_level": int(_calcular_nivel(valor_actual, thr)),
                "projected_n_level": int(_calcular_nivel(valor_proyectado, thr)),
                "trend": trend_map.get(tendencia, "estable"),
                "samples": len(valores_historicos),
            },
            "thresholds": thresholds,
            "distribution": {
                "values": dist_counts,
            },
            "hotspots": _calcular_hotspots_por_pk(mediciones, campo, thr),
            "model_used": "linear" if float(datos.get("r2", 0) or 0) > 0.5 else "arima",
            "model_params": {
                "r2": float(datos.get("r2", 0) or 0),
                "pendiente": float(datos.get("pendiente_diaria", 0) or 0),
            },
        }
        parametros.append(param)
    
    return {
        "tramo": str(tramo) if tramo else "",
        "via": str(via) if via else "",
        "parametros": parametros,
        "calibration": {
            "tipologia": "CA-160",
            "velocidad": "160",
        },
        "message": None if parametros else "No se encontraron datos suficientes para proyectar.",
    }


def _calcular_nivel(valor: float, umbrales) -> int:
    """Calcula el nivel N (0-4) para un valor dado según los umbrales."""
    if not umbrales or valor is None:
        return 0
    
    # Manejar caso donde umbrales es una lista en lugar de dict
    if isinstance(umbrales, list):
        return 0
    
    # Asegurar que es un dict
    if not isinstance(umbrales, dict):
        return 0
    
    n4 = umbrales.get("N4")
    n3 = umbrales.get("N3")
    n2 = umbrales.get("N2")
    n1 = umbrales.get("N1")
    
    # DEBUG: Log para entender por qué 9.347 da N4
    if valor > 5:  # Solo loguear valores anómalos
        print(f"[DEBUG] _calcular_nivel: valor={valor}, umbrales={umbrales}")
        print(f"[DEBUG]   n4={n4}, n3={n3}, n2={n2}, n1={n1}")
        print(f"[DEBUG]   valor < n4? {n4 and valor < n4}")
    
    # Para altura: valores más bajos son peores
    if n4 and valor < n4:
        return 4
    if n3 and valor < n3:
        return 3
    if n2 and valor < n2:
        return 2
    if n1 and valor < n1:
        return 1
    return 0


def _calcular_hotspots_por_pk(mediciones: List[Dict], campo: str, umbrales: Dict) -> List[Dict]:
    """Calcula hotspots (puntos kilométricos) con mayor nivel de alerta."""
    from collections import defaultdict
    
    # Agrupar mediciones por PK
    pk_data = defaultdict(lambda: {"valores": [], "niveles": []})
    
    for m in mediciones:
        if not isinstance(m, dict):
            continue
        pk = m.get("pto_km")
        if pk is None:
            continue
        try:
            pk_val = float(pk)
            val = m.get(campo)
            if val is not None:
                val_float = float(val)
                pk_data[pk_val]["valores"].append(val_float)
                pk_data[pk_val]["niveles"].append(_calcular_nivel(val_float, umbrales))
        except (ValueError, TypeError):
            continue
    
    if not pk_data:
        return []
    
    # Calcular estadísticas por PK y ordenar por nivel máximo (descendente)
    hotspots = []
    for pk, data in pk_data.items():
        if not data["valores"]:
            continue
        valores = data["valores"]
        niveles = data["niveles"]
        
        # Calcular promedio de valores
        try:
            import numpy as np
            valor_avg = float(np.mean(valores))
        except:
            valor_avg = sum(valores) / len(valores) if valores else 0.0
        
        n_max = max(niveles) if niveles else 0
        n_avg = sum(niveles) / len(niveles) if niveles else 0.0
        
        hotspots.append({
            "pto_km": f"{pk:.2f}",
            "value_avg": valor_avg,
            "n_level_max": int(n_max),
            "n_level_avg": round(n_avg, 1),
            "samples": len(valores)
        })
    
    # Ordenar por nivel máximo (descendente), luego por número de muestras
    hotspots.sort(key=lambda x: (-x["n_level_max"], -x["samples"], x["pto_km"]))
    
    # Devolver top 8
    return hotspots[:8]


@login_required
def analitica_predictiva_datos(request: HttpRequest) -> JsonResponse:
    """Endpoint AJAX para obtener datos predictivos en formato JSON."""
    try:
        # Parámetros de la petición
        tramo = request.GET.get("tramo", "")
        via = request.GET.get("via", "")
        horizon_days = int(request.GET.get("horizon_days", 30))
        fecha_inicio = request.GET.get("fecha_inicio", "")
        fecha_fin = request.GET.get("fecha_fin", "")
        pk_min = request.GET.get("pk_min", "")
        pk_max = request.GET.get("pk_max", "")
        
        if not tramo or not via:
            return JsonResponse({"error": "Se requiere tramo y vía"}, status=400)
        
        # Obtener conexión Couchbase
        cluster, bucket_name, scope_name, clausula_from = _cb_bucket_scope()
        
        # Cargar mediciones del tramo/vía
        query_mediciones = f"""
            SELECT m.fecha, m.altura_LAC, m.descentramiento, m.flecha, 
                   m.contraflecha, m.pendiente, m.variacion_pendiente,
                   m.id_via, m.pto_km
            {clausula_from}`Medicion_Individual` AS m
            WHERE m.id_tramo = $tramo AND m.id_via = $via
            AND m.fecha IS NOT MISSING
        """
        
        # Agregar filtros de PK si existen
        params = {"tramo": tramo, "via": via}
        if pk_min:
            query_mediciones += " AND m.pto_km >= $pk_min"
            params["pk_min"] = float(pk_min)
        if pk_max:
            query_mediciones += " AND m.pto_km <= $pk_max"
            params["pk_max"] = float(pk_max)
        
        # Agregar filtros de fecha si existen.
        # m.fecha se almacena como "YYYYMMDD" (sin guiones), mientras que
        # request.GET trae "YYYY-MM-DD" (formato de <input type="date">).
        if fecha_inicio:
            query_mediciones += " AND m.fecha >= $fecha_inicio"
            params["fecha_inicio"] = fecha_inicio.replace("-", "")
        if fecha_fin:
            query_mediciones += " AND m.fecha <= $fecha_fin"
            params["fecha_fin"] = fecha_fin.replace("-", "")
        
        query_mediciones += " ORDER BY m.fecha DESC LIMIT 10000"
        
        mediciones_result = cluster.query(query_mediciones, **params)
        mediciones = [dict(r) for r in mediciones_result]
        mediciones.reverse()  # Orden cronológico
        
        if len(mediciones) < 3:
            return JsonResponse({
                "error": f"Datos insuficientes: solo {len(mediciones)} mediciones (mínimo 3 requeridas)"
            }, status=400)
        
        # Cargar incidencias (sin filtrar por vía, por si no existe ese campo)
        try:
            query_incidencias = f"""
                SELECT i.fecha, i.tipo, i.nivel, i.valor_medido, i.valor_referencia
                {clausula_from}`Incidencias` AS i
                WHERE i.id_tramo = $tramo
                AND i.fecha IS NOT MISSING
                ORDER BY i.fecha DESC LIMIT 5000
            """
            incidencias_result = cluster.query(query_incidencias, tramo=tramo)
            incidencias = [dict(r) for r in incidencias_result]
        except Exception as e:
            incidencias = []
        
        # Depuración: contar incidencias por tipo
        debug_inc = {"total": len(incidencias)}
        from collections import Counter
        tipos = Counter(i.get("tipo", "sin_tipo") for i in incidencias)
        debug_inc["por_tipo"] = dict(tipos)
        if incidencias:
            debug_inc["fecha_ejemplo"] = str(incidencias[0].get("fecha", ""))
        
        # Cargar umbrales
        info_tramo = {"tipologia": "CA-160", "velocidad_max": "160"}
        umbrales = cargar_umbrales_tramo(cluster, clausula_from, tramo, info_tramo)
        
        # Calcular proyecciones simplificadas
        predictive_data = obtener_proyecciones_simplificadas(
            mediciones, incidencias, umbrales, horizon_days
        )
        # Añadir metadatos de tramo/vía
        predictive_data["tramo"] = tramo
        predictive_data["via"] = via
        predictive_data["_debug_inc"] = debug_inc
        
        return JsonResponse(predictive_data)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def configuracion(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    html = page_configuracion(_get_error_param(request))
    return _html_response(request, html)


@login_required
def alertas(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_ESTANDAR})
    if denied:
        return denied
    cluster, clausula_from = _cb_ctx()
    try:
        pagina = max(1, int(request.GET.get("pagina", 1)))
    except (ValueError, TypeError):
        pagina = 1

    import math
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Lanzar conteo y datos en paralelo — de 2 queries secuenciales a 1 round-trip efectivo
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_resumen = pool.submit(contar_alertas_resumen, cluster, clausula_from)
        # Para la primera llamada usamos pagina=1 provisional; si pagina > total_paginas
        # la corregimos después (caso raro: el usuario manipula la URL)
        fut_grupos  = pool.submit(buscar_alertas_agrupadas, cluster, clausula_from, pagina)

        total_global, total_fechas = fut_resumen.result()
        grupos = fut_grupos.result()

    total_paginas = max(1, math.ceil(total_fechas / POR_PAGINA_ALERTAS))
    pagina = min(pagina, total_paginas)

    # Si la página fue corregida hacia abajo, volver a consultar con la página correcta
    if pagina != max(1, int(request.GET.get("pagina", 1))):
        grupos = buscar_alertas_agrupadas(cluster, clausula_from, pagina)

    total = sum(
        len(inc)
        for g in grupos
        for tv in g.get("tramos", [])
        for inc in [tv.get("incidencias", [])]
    )
    html = page_alertas(grupos, total, total_global, pagina, total_paginas)
    return _html_response(request, html)


@login_required
@csrf_exempt
def marcar_revision(request: HttpRequest) -> JsonResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_ESTANDAR})
    if denied:
        return JsonResponse({"success": False, "error": "Sin permisos"}, status=403)
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body)
        doc_id = str(data.get("doc_id") or "").strip()
        revisado = bool(data.get("revisado", True))
        if not doc_id:
            return JsonResponse({"success": False, "error": "Falta doc_id"}, status=400)
        cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
        marcar_revision_incidencia(cluster, bucket_name, scope_name, doc_id, revisado)
        return JsonResponse({"success": True})
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def consultar_datos(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return consultar_datos_post(request)
    cluster, clausula_from = _cb_ctx()
    tramos = obtener_tramos(cluster, clausula_from)
    opciones_html = "".join(f'<option value="{t}">{t}</option>' for t in tramos)
    html = page_consultar_datos_filtros(opciones_html, _get_error_param(request))
    return _html_response(request, html)


@login_required
def usuarios(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, clausula_from = _cb_ctx()
    query_params = {k: [escape(v) for v in request.GET.getlist(k)] for k in request.GET.keys()}
    personas = obtener_personas(cluster, clausula_from)
    usuarios_acceso = _obtener_usuarios_acceso()
    html = page_usuarios(personas, "", query_params, usuarios_acceso=usuarios_acceso)
    return _html_response(request, html)


@login_required
def tramos(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, clausula_from = _cb_ctx()
    query_params = {k: [escape(v) for v in request.GET.getlist(k)] for k in request.GET.keys()}
    tramos_data = obtener_tramos_crud(cluster, clausula_from)
    html = page_tramos(tramos_data, "", query_params)
    return _html_response(request, html)


@login_required
def umbrales(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, clausula_from = _cb_ctx()
    query_params = {k: [escape(v) for v in request.GET.getlist(k)] for k in request.GET.keys()}
    umbrales_data = obtener_umbrales_crud(cluster, clausula_from)
    html = page_umbrales(umbrales_data, "", query_params)
    return _html_response(request, html)


@login_required
def operaciones(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, clausula_from = _cb_ctx()
    qparams = {k: request.GET.getlist(k) for k in request.GET.keys()}

    sel_parte = request.GET.get("parte", "")
    sel_grupo = request.GET.get("grupo", "")
    buscar_codigo = escape(request.GET.get("buscar_codigo", ""))
    ver_todas = (request.GET.get("ver_todas", "") or "").strip() in ("1", "true", "on")

    partes = obtener_partes(cluster, clausula_from)

    if ver_todas:
        # Vista catálogo completo: ignoramos parte/grupo, listamos todo plano.
        grupos = []
        subgrupos = []
        todas = obtener_todas_operaciones(cluster, clausula_from, buscar_codigo or None)
    else:
        grupos = obtener_grupos_por_parte(cluster, sel_parte, clausula_from) if sel_parte else []
        subgrupos = (
            obtener_subgrupos(cluster, sel_parte, sel_grupo, clausula_from, buscar_codigo)
            if (sel_parte and sel_grupo)
            else []
        )
        todas = None

    html = page_operaciones(
        partes,
        grupos,
        subgrupos,
        seleccion_parte=sel_parte,
        seleccion_grupo=sel_grupo,
        mensaje_html="",
        filtro_codigo=buscar_codigo,
        query_params=qparams,
        ver_todas=ver_todas,
        todas_operaciones=todas,
    )
    return _html_response(request, html)


@login_required
def filtros(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return tabla(request)
    cluster, clausula_from = _cb_ctx()
    tramos = obtener_tramos(cluster, clausula_from)
    opciones_html = "\n".join(f'<option value="{t}">{t}</option>' for t in tramos)
    html = page_filtros(opciones_html, _get_error_param(request))
    return _html_response(request, html)


@login_required
def obtener_vias(request: HttpRequest) -> JsonResponse:
    cluster, clausula_from = _cb_ctx()
    tramo = request.GET.get("tramo")
    vias = obtener_vias_por_tramo(cluster, tramo, clausula_from) if tramo else []
    return JsonResponse({"vias": vias})


@login_required
def mapa_cuadrantes(request: HttpRequest) -> JsonResponse:
    """
    Devuelve un payload JSON para dibujar el mapa por cuadrantes
    en la pantalla de filtros (sin tener que hacer la consulta completa).
    """
    cluster, clausula_from = _cb_ctx()
    coordenada_gps = (request.GET.get("coordenada_gps", "") or "").strip()
    radio_raw = (request.GET.get("radio", "") or "").strip()
    max_segmentos_raw = (request.GET.get("max_segmentos", "") or "").strip()

    if not coordenada_gps or not radio_raw:
        return JsonResponse(
            {"error": "Faltan parámetros: coordenada_gps y/o radio"},
            status=400,
        )

    try:
        radio_km = float(radio_raw)
    except ValueError:
        return JsonResponse({"error": "El radio debe ser numérico"}, status=400)

    try:
        max_segmentos = int(max_segmentos_raw) if max_segmentos_raw else 800
    except ValueError:
        max_segmentos = 800

    try:
        payload = resolver_mapa_por_ambito_geografico(
            cluster,
            clausula_from,
            coordenada_gps,
            radio_km,
            max_segmentos=max_segmentos,
        )
        return JsonResponse(payload, safe=False)
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def mapa_cuadrantes_overview(request: HttpRequest) -> JsonResponse:
    """
    Vista general por bbox (para niveles de zoom bajos).
    Devuelve cuadrantes dentro del bbox con un conteo aproximado de tramos.

    Params:
      - bbox: "south,west,north,east" (lat/lon)
      - limit: int (máximo cuadrantes)
    """
    cluster, clausula_from = _cb_ctx()
    bbox_raw = (request.GET.get("bbox", "") or "").strip()
    limit_raw = (request.GET.get("limit", "") or "").strip()

    if not bbox_raw or bbox_raw.count(",") < 3:
        return JsonResponse({"error": "Falta bbox (south,west,north,east)"}, status=400)

    try:
        south_s, west_s, north_s, east_s = [x.strip() for x in bbox_raw.split(",", 3)]
        south = float(south_s)
        west = float(west_s)
        north = float(north_s)
        east = float(east_s)
    except Exception:
        return JsonResponse({"error": "bbox inválido"}, status=400)

    try:
        limit = int(limit_raw) if limit_raw else 1500
        limit = max(100, min(limit, 5000))
    except Exception:
        limit = 1500

    # Filtro bbox: cualquier cuadrante que interseque con el bbox.
    # Condición de intersección de rectángulos (lat/lon):
    #   cuad.lat_min <= north AND cuad.lat_max >= south
    #   cuad.lon_min <= east  AND cuad.lon_max >= west
    # donde:
    #   lat_max = esquina_NO[0], lat_min = esquina_SE[0]
    #   lon_min = esquina_NO[1], lon_max = esquina_SE[1]
    keyspace = clausula_from.replace("FROM ", "").strip()
    if keyspace and not keyspace.endswith("."):
        keyspace = keyspace + "."

    query = f"""
        SELECT
            c.id_cuadrante AS id_cuadrante,
            c.esquina_NO   AS esquina_NO,
            c.esquina_SE   AS esquina_SE,
            COUNT(DISTINCT tc.id_tramo) AS n_tramos
        FROM {keyspace}`Cuadrantes` AS c
        LEFT JOIN {keyspace}`Tramos_Cuadrantes` AS tc
            ON tc.id_cuadrante = c.id_cuadrante
        WHERE c.esquina_SE[0] <= $north
          AND c.esquina_NO[0] >= $south
          AND c.esquina_NO[1] <= $east
          AND c.esquina_SE[1] >= $west
        GROUP BY c.id_cuadrante, c.esquina_NO, c.esquina_SE
        HAVING COUNT(DISTINCT tc.id_tramo) > 0
        LIMIT $limit;
    """

    try:
        rows = [
            {
                "id_cuadrante": int(r.get("id_cuadrante")),
                "esquina_NO": r.get("esquina_NO") or [],
                "esquina_SE": r.get("esquina_SE") or [],
                "n_tramos": int(r.get("n_tramos") or 0),
            }
            for r in (dict(x) for x in cluster.query(query, north=north, south=south, east=east, west=west, limit=limit).rows())
        ]
        return JsonResponse({"cuadrantes": rows, "limit": limit})
    except Exception as e:  # noqa: BLE001
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def medicion_detalle(request: HttpRequest) -> HttpResponse:
    cluster, clausula_from = _cb_ctx()
    try:
        id_tramo = request.GET.get("id_tramo")
        id_via = request.GET.get("id_via")
        pto_km = request.GET.get("pto_km")
        fecha = request.GET.get("fecha")
        hora = request.GET.get("hora")
        if not all([id_tramo, id_via, pto_km, fecha, hora]):
            raise ValueError("Faltan parámetros para buscar la medición")
        medicion = buscar_medicion_por_clave(
            cluster,
            clausula_from,
            id_tramo,
            id_via,
            float(pto_km),
            fecha,
            hora,
        )
        html = page_modal_medicion_detalle(medicion)
        return _html_response(request, html)
    except Exception as e:  # noqa: BLE001
        html = f"<div class='p-3 text-danger'>Error cargando medición: {str(e)}</div>"
        return _html_response(request, html)


@login_required
def incidencia_detalle(request: HttpRequest) -> HttpResponse:
    cluster, clausula_from = _cb_ctx()
    try:
        doc_id = request.GET.get("doc_id")
        if not doc_id:
            raise ValueError("Falta el parámetro doc_id (Doc ID de la incidencia)")
        incidencia = buscar_incidencia_por_doc_id(cluster, clausula_from, doc_id)
        html = page_modal_incidencia_detalle(incidencia)
        return HttpResponse(html, content_type="text/html; charset=utf-8")
    except Exception as e:  # noqa: BLE001
        html = f"<div class='p-3 text-danger'>Error cargando incidencia: {str(e)}</div>"
        return HttpResponse(html, content_type="text/html; charset=utf-8")


@login_required
def incidencias_medicion(request: HttpRequest) -> HttpResponse:
    cluster, clausula_from = _cb_ctx()
    id_tramo = request.GET.get("id_tramo")
    id_via = request.GET.get("id_via")
    pto_km = request.GET.get("pto_km")
    fecha = request.GET.get("fecha")
    hora = request.GET.get("hora")
    if not all([id_tramo, id_via, pto_km, fecha, hora]):
        html = "<div class='p-3 text-danger'>Faltan parámetros de medición</div>"
        return HttpResponse(html, content_type="text/html; charset=utf-8", status=400)

    incidencias = buscar_incidencias_por_medicion(
        cluster, clausula_from, id_tramo, id_via, float(pto_km), fecha, hora
    )

    incidencias_det = []
    for inc in incidencias or []:
        if isinstance(inc, str):
            det = buscar_incidencia_por_doc_id(cluster, clausula_from, inc)
            if det:
                incidencias_det.append(det)
        elif isinstance(inc, dict):
            incidencias_det.append(inc)

    html = page_modal_incidencias_medicion(id_tramo, id_via, float(pto_km), fecha, hora, incidencias_det)
    return HttpResponse(html, content_type="text/html; charset=utf-8")


@login_required
def estado_sync(request: HttpRequest) -> JsonResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return JsonResponse({"error": "forbidden"}, status=403)
    return JsonResponse(estado_sync_state)


@login_required
@csrf_exempt
def limpiar_estado_sync(_: HttpRequest) -> HttpResponse:
    denied = _require_any_role(_, {ROLE_ADMIN})
    if denied:
        return HttpResponse(status=403)
    estado_sync_state["mensaje"] = ""
    return HttpResponse(status=200)


@login_required
@csrf_exempt
def ejecutar_script(_: HttpRequest) -> HttpResponse:
    denied = _require_any_role(_, {ROLE_ADMIN})
    if denied:
        return HttpResponse(status=403)
    if not estado_sync_state.get("trabajando"):
        threading.Thread(target=_tarea_en_segundo_plano, daemon=True).start()
    return HttpResponse(status=200)


@login_required
def usuarios_nuevo(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    doc = {
        "codigo": request.POST.get("codigo", ""),
        "nombre": request.POST.get("nombre", ""),
        "perfil": request.POST.get("perfil", ""),
    }
    documento_id = doc["codigo"]
    try:
        crear_usuario(cluster, bucket_name, scope_name, documento_id, doc)
        return _redirect_303("/usuarios?success=" + quote(USUARIOS["create_success"]))
    except DocumentExistsException:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["create_exists"]))
    except ValueError as ve:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["create_invalid"] + ": " + str(ve)))
    except DocumentNotFoundException as e:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["not_found"] + ": " + str(e)))
    except CouchbaseException as e:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["unexpected"] + ": " + str(e)))


@login_required
def usuarios_acceso_nuevo(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    usuario = (request.POST.get("usuario") or "").strip()
    password = request.POST.get("password") or ""
    rol = _normalize_role((request.POST.get("rol") or "usuario").strip() or "usuario")

    if not usuario or not password:
        return _redirect_303("/usuarios?error=" + quote("Usuario y contraseña son obligatorios"))

    doc = {
        "usuario": usuario,
        "password_hash": make_password(password),
        "rol": rol,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
        coll.insert(usuario, doc)
        return _redirect_303("/usuarios?success=" + quote("Acceso a la app creado correctamente"))
    except DocumentExistsException:
        return _redirect_303("/usuarios?error=" + quote("Ese usuario de acceso ya existe"))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote("Error creando acceso a la app: " + str(e)))


@login_required
def usuarios_acceso_editar(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    if request.method != "POST":
        return _redirect_303("/usuarios")

    nuevo_usuario = (request.POST.get("usuario") or "").strip()
    nuevo_rol = _normalize_role((request.POST.get("rol") or "usuario").strip() or "usuario")
    if not nuevo_usuario:
        return _redirect_303("/usuarios?error=" + quote("El usuario de acceso es obligatorio."))

    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
    try:
        actual = coll.get(doc_id).content_as[dict]
        actual["usuario"] = nuevo_usuario
        actual["rol"] = nuevo_rol

        if nuevo_usuario != doc_id:
            try:
                coll.insert(nuevo_usuario, actual)
            except DocumentExistsException:
                return _redirect_303("/usuarios?error=" + quote("Ese usuario de acceso ya existe."))
            coll.remove(doc_id)
        else:
            coll.upsert(doc_id, actual)
        return _redirect_303("/usuarios?success=" + quote("Acceso a la app actualizado correctamente."))
    except DocumentNotFoundException:
        return _redirect_303("/usuarios?error=" + quote("No se encontró el acceso seleccionado."))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote("Error actualizando acceso: " + str(e)))


@login_required
def usuarios_acceso_resetear_password(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    if request.method != "POST":
        return _redirect_303("/usuarios")

    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
    try:
        doc = coll.get(doc_id).content_as[dict]
        doc["password_hash"] = make_password("12345678")
        coll.upsert(doc_id, doc)
        return _redirect_303("/usuarios?success=" + quote(f"Contraseña de '{doc_id}' restablecida a 12345678."))
    except DocumentNotFoundException:
        return _redirect_303("/usuarios?error=" + quote("No se encontró el usuario seleccionado."))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote("Error restableciendo contraseña: " + str(e)))


@login_required
def usuarios_acceso_eliminar(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    if request.method != "POST":
        return _redirect_303("/usuarios")
    if request.user.username == doc_id:
        return _redirect_303("/usuarios?error=" + quote("No puedes darte de baja a ti mismo."))

    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
    try:
        coll.remove(doc_id)
        return _redirect_303("/usuarios?success=" + quote("Acceso dado de baja correctamente."))
    except DocumentNotFoundException:
        return _redirect_303("/usuarios?error=" + quote("No se encontró el acceso seleccionado."))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote("Error dando de baja el acceso: " + str(e)))


@login_required
def usuarios_editar(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    try:
        coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios")
        actual = coll.get(doc_id).content_as[dict]
        actual.update(
            {
                "nombre": (request.POST.get("nombre", "") or "").strip(),
                "perfil": (request.POST.get("perfil", "") or "").strip(),
            }
        )
        actualizar_usuario(cluster, bucket_name, scope_name, doc_id, actual)
        return _redirect_303("/usuarios?success=" + quote(USUARIOS["update_success"]))
    except ValueError as ve:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["update_invalid"] + ": " + str(ve)))
    except DocumentNotFoundException:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["not_found"]))
    except CouchbaseException as e:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["update_error"] + ": " + str(e)))


@login_required
def usuarios_eliminar(_: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(_, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    try:
        eliminar_usuario(cluster, bucket_name, scope_name, doc_id)
        return _redirect_303("/usuarios?success=" + quote(USUARIOS["delete_success"]))
    except ValueError as e:
        return _redirect_303("/usuarios?error=" + quote(str(e)))
    except CouchbaseException as e:
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/usuarios?error=" + quote(USUARIOS["delete_error"] + ": " + str(e)))


@login_required
def tramos_nuevo(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    doc = {
        "id_tramo": request.POST.get("id_tramo", ""),
        "id_via": request.POST.get("id_via", ""),
        "pto_km_ini": request.POST.get("pto_km_ini", ""),
        "pto_km_fin": request.POST.get("pto_km_fin", ""),
        "tipologia": request.POST.get("tipologia", ""),
        "velocidad_max": request.POST.get("velocidad_max", ""),
        "descripcion": request.POST.get("descripcion", ""),
    }
    try:
        crear_tramo(cluster, bucket_name, scope_name, doc)
        return _redirect_303("/tramos?success=" + quote(TRAMOS["create_success"]))
    except DocumentExistsException:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["create_exists"]))
    except ValueError as ve:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["create_invalid"] + ": " + str(ve)))
    except DocumentNotFoundException as e:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["not_found"] + ": " + str(e)))
    except CouchbaseException as e:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/tramos?error=" + quote(TRAMOS["unexpected"] + ": " + str(e)))


@login_required
def tramos_editar(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    try:
        coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Tramos")
        _ = coll.get(doc_id).content_as[dict]
        datos_actualizados = {
            "id_tramo": request.POST.get("id_tramo", ""),
            "id_via": request.POST.get("id_via", ""),
            "pto_km_ini": request.POST.get("pto_km_ini", ""),
            "pto_km_fin": request.POST.get("pto_km_fin", ""),
            "tipologia": request.POST.get("tipologia", ""),
            "velocidad_max": request.POST.get("velocidad_max", ""),
            "descripcion": request.POST.get("descripcion", ""),
        }
        actualizar_tramo(cluster, bucket_name, scope_name, doc_id, datos_actualizados)
        return _redirect_303("/tramos?success=" + quote(TRAMOS["update_success"]))
    except DocumentNotFoundException:
        return _redirect_303("/tramos?error=" + quote(GENERIC["tramo_edit_not_found"]))
    except ValueError as ve:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["update_invalid"] + ": " + str(ve)))
    except CouchbaseException as e:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/tramos?error=" + quote(TRAMOS["update_error"] + ": " + str(e)))


@login_required
def tramos_eliminar(_: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(_, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    try:
        eliminar_tramo(cluster, bucket_name, scope_name, doc_id)
        return _redirect_303("/tramos?success=" + quote(TRAMOS["delete_success"]))
    except DocumentNotFoundException:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["not_found"]))
    except CouchbaseException as e:
        return _redirect_303("/tramos?error=" + quote(TRAMOS["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/tramos?error=" + quote(TRAMOS["delete_error"] + ": " + str(e)))


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


@login_required
def umbrales_validar(request: HttpRequest) -> JsonResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return JsonResponse({"ok": False, "message": "No autorizado"}, status=403)
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()

    def _range_param(nombre: str) -> list[str]:
        vals = request.POST.getlist(nombre)
        if not vals:
            return []
        if len(vals) == 1:
            return _range_param_single(vals[0])
        a = (vals[0] or "").strip()
        b = (vals[1] or "").strip() if len(vals) > 1 else a
        return [a, b]

    doc = {
        "tipo": (request.POST.get("tipo", "") or "").strip(),
        "tipologia": (request.POST.get("tipologia", "") or "").strip(),
        "velocidad": (request.POST.get("velocidad", "") or "").strip(),
        "valor_referencia": (request.POST.get("valor_referencia", "") or "").strip(),
        "valores_N1": _range_param("valores_N1"),
        "valores_N2": _range_param("valores_N2"),
        "valores_N3": _range_param("valores_N3"),
        "valores_N4": _range_param("valores_N4"),
    }
    doc_id = (request.POST.get("doc_id", "") or "").strip()

    duplicado_message = None
    duplicado_field = "tipo"
    tipo_clave = doc["tipo"]
    tipologia_clave = doc["tipologia"]
    velocidad_clave = doc["velocidad"]

    if tipo_clave and (tipologia_clave or velocidad_clave):
        try:
            existe_clave = existe_umbral_con_clave(
                cluster,
                bucket_name,
                scope_name,
                tipo_clave,
                tipologia_clave,
                velocidad_clave,
                doc_id or None,
            )
        except CouchbaseException as e:
            duplicado_message = f"{UMBRALES['db_error']}: {str(e)}"
            duplicado_field = "tipo"
        else:
            if existe_clave:
                duplicado_message = UMBRALES["create_exists"]
                if tipologia_clave:
                    duplicado_field = "tipologia"
                elif velocidad_clave:
                    duplicado_field = "velocidad"

    if duplicado_message:
        return JsonResponse(
            {"ok": False, "code": "DUPLICATE_KEY", "message": duplicado_message, "field": duplicado_field},
            status=200,
        )

    ok, code = validar_umbral_doc(doc)
    if ok:
        return JsonResponse({"ok": True}, status=200)

    base_code = code
    field_prefix = ""
    if code and code.startswith(("N1_", "N2_", "N3_", "N4_")):
        field_prefix, base_code = code.split("_", 1)

    detalle_base = UMBRALES_CODES.get(base_code, base_code or "")
    detalle = (f"{field_prefix}: {detalle_base}" if field_prefix else detalle_base)

    field = ""
    if field_prefix in ("N1", "N2", "N3", "N4"):
        field = f"valores_{field_prefix}"
    else:
        if base_code in ("DIR_UNDETERMINED", "ASC_N1N2", "DESC_N1N2"):
            field = "valores_N2"
        elif base_code in ("ASC_N2N3", "DESC_N2N3"):
            field = "valores_N3"
        elif base_code in ("ASC_N3N4", "DESC_N3N4"):
            field = "valores_N4"
        elif base_code and base_code.startswith("SPEED_"):
            field = "velocidad"
        elif base_code and base_code.startswith("VREF_"):
            field = "valor_referencia"

    texto = f"{UMBRALES['create_invalid']}: {detalle}" if detalle else UMBRALES["create_invalid"]
    return JsonResponse({"ok": False, "code": code, "message": texto, "field": field}, status=200)


@login_required
def umbrales_nuevo(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()

    doc: dict[str, Any] = {
        "tipo": (request.POST.get("tipo", "") or "").strip(),
        "tipologia": (request.POST.get("tipologia", "") or "").strip(),
        "velocidad": (request.POST.get("velocidad", "") or "").strip(),
        "valor_referencia": (request.POST.get("valor_referencia", "") or "").strip(),
        "valores_N1": _range_param_single(request.POST.get("valores_N1", "")),
        "valores_N2": _range_param_single(request.POST.get("valores_N2", "")),
        "valores_N3": _range_param_single(request.POST.get("valores_N3", "")),
    }
    v4 = _range_param_single(request.POST.get("valores_N4", ""))
    if v4:
        doc["valores_N4"] = v4

    ok, code = validar_umbral_doc(doc)
    if not ok:
        base_code = code
        field_prefix = ""
        if code and code.startswith(("N1_", "N2_", "N3_", "N4_")):
            field_prefix, base_code = code.split("_", 1)
        detalle_base = UMBRALES_CODES.get(base_code, base_code or "")
        detalle = (f"{field_prefix}: {detalle_base}" if field_prefix else detalle_base)
        texto = f"{UMBRALES['create_invalid']}: {detalle}" if detalle else UMBRALES["create_invalid"]
        return _redirect_303("/umbrales?error=" + quote(texto))

    try:
        crear_umbral(cluster, bucket_name, scope_name, doc)
        return _redirect_303("/umbrales?success=" + quote(UMBRALES["create_success"]))
    except DocumentExistsException:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["create_exists"]))
    except ValueError as ve:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["create_invalid"] + ": " + str(ve)))
    except DocumentNotFoundException as e:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["not_found"] + ": " + str(e)))
    except CouchbaseException as e:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["unexpected"] + ": " + str(e)))


@login_required
def umbrales_editar(request: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()

    def _range_param(nombre: str) -> list[str]:
        vals = request.POST.getlist(nombre)
        if not vals:
            return []
        if len(vals) == 1:
            return _range_param_single(vals[0])
        a = (vals[0] or "").strip()
        b = (vals[1] or "").strip() if len(vals) > 1 else a
        return [a, b]

    vel_raw = (request.POST.get("velocidad", "") or "").strip()
    try:
        velocidad = int(vel_raw) if vel_raw != "" else None
    except ValueError:
        velocidad = None

    datos_actualizados: dict[str, Any] = {
        "tipo": (request.POST.get("tipo", "") or "").strip(),
        "tipologia": (request.POST.get("tipologia", "") or "").strip(),
        "velocidad": velocidad,
        "valor_referencia": (request.POST.get("valor_referencia", "") or "").strip(),
        "valores_N1": _range_param("valores_N1"),
        "valores_N2": _range_param("valores_N2"),
        "valores_N3": _range_param("valores_N3"),
        "valores_N4": _range_param("valores_N4"),
    }

    ok, code = validar_umbral_doc(datos_actualizados)
    if not ok:
        base_code = code
        field_prefix = ""
        if code and code.startswith(("N1_", "N2_", "N3_", "N4_")):
            field_prefix, base_code = code.split("_", 1)
        detalle_base = UMBRALES_CODES.get(base_code, base_code or "")
        detalle = (f"{field_prefix}: {detalle_base}" if field_prefix else detalle_base)
        msg = UMBRALES["update_invalid"]
        texto = f"{msg}: {detalle}" if detalle else msg
        return _redirect_303("/umbrales?error=" + quote(texto))

    try:
        actualizar_umbral(cluster, bucket_name, scope_name, doc_id, datos_actualizados)
        return _redirect_303("/umbrales?success=" + quote(UMBRALES["update_success"]))
    except ValueError:
        mensaje = UMBRALES["update_invalid"]
        detalle = "No se permite modificar Tipo, Tipología o Velocidad del umbral."
        return _redirect_303("/umbrales?error=" + quote(f"{mensaje}: {detalle}"))
    except DocumentNotFoundException:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["not_found"]))
    except CouchbaseException as e:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["unexpected"] + ": " + str(e)))


@login_required
def umbrales_eliminar(_: HttpRequest, doc_id: str) -> HttpResponse:
    denied = _require_any_role(_, {ROLE_ADMIN, ROLE_LICITADOR})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    try:
        eliminar_umbral(cluster, bucket_name, scope_name, doc_id)
        return _redirect_303("/umbrales?success=" + quote(UMBRALES["delete_success"]))
    except DocumentNotFoundException:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["not_found"]))
    except CouchbaseException as e:
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/umbrales?error=" + quote(UMBRALES["unexpected"] + ": " + str(e)))


@login_required
def operaciones_nuevo(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    parte = request.POST.get("parte", "")
    id_grupo = request.POST.get("id_grupo", "")
    codigo = request.POST.get("codigo", "")
    descripcion = request.POST.get("descripcion", "")
    try:
        crear_subgrupo(cluster, bucket_name, scope_name, parte, id_grupo, codigo, descripcion)
        return _redirect_303(
            f"/operaciones?parte={quote(parte)}&grupo={quote(id_grupo)}&success={quote(OPERACIONES['create_success'])}"
        )
    except Exception:  # noqa: BLE001
        return _redirect_303("/operaciones?error=" + quote(OPERACIONES["create_error"]))


@login_required
def operaciones_grupo_nuevo(request: HttpRequest) -> HttpResponse:
    """
    Crea un grupo nuevo dentro de una parte existente.
    Campos esperados: parte, id_grupo, nombre.
    Tras la creación deja al usuario posicionado en (parte, grupo) recién
    creados para que pueda dar de alta subgrupos directamente.
    """
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    if request.method != "POST":
        return _redirect_303("/operaciones")
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    parte = (request.POST.get("parte", "") or "").strip()
    id_grupo = (request.POST.get("id_grupo", "") or "").strip()
    nombre = (request.POST.get("nombre", "") or "").strip()
    try:
        crear_grupo(cluster, bucket_name, scope_name, parte, id_grupo, nombre)
        return _redirect_303(
            f"/operaciones?parte={quote(parte)}&grupo={quote(id_grupo)}"
            f"&success={quote('Grupo creado correctamente. Ya puedes añadir subgrupos.')}"
        )
    except DocumentExistsException as e:
        return _redirect_303("/operaciones?error=" + quote(str(e)))
    except ValueError as e:
        return _redirect_303("/operaciones?error=" + quote(str(e)))
    except CouchbaseException as e:
        return _redirect_303(
            "/operaciones?error=" + quote(f"{OPERACIONES.get('db_error', 'Error de BD')}: {str(e)}")
        )
    except Exception as e:  # noqa: BLE001
        return _redirect_303(
            "/operaciones?error=" + quote(f"Error inesperado al crear el grupo: {str(e)}")
        )


@login_required
def operaciones_editar(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    parte = request.POST.get("parte", "")
    id_grupo = request.POST.get("id_grupo", "")
    codigo_original = request.POST.get("codigo_original", "")
    codigo = request.POST.get("codigo", "")
    descripcion = request.POST.get("descripcion", "")
    try:
        if codigo != codigo_original:
            codigo = codigo_original
        actualizar_subgrupo(cluster, bucket_name, scope_name, parte, id_grupo, codigo_original, codigo, descripcion)
        return _redirect_303(
            f"/operaciones?parte={quote(parte)}&grupo={quote(id_grupo)}&success={quote(OPERACIONES['update_success'])}"
        )
    except ValueError as ve:
        return _redirect_303("/operaciones?error=" + quote(OPERACIONES["update_invalid"] + ": " + str(ve)))
    except CouchbaseException as e:
        return _redirect_303("/operaciones?error=" + quote(OPERACIONES["db_error"] + ": " + str(e)))
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/operaciones?error=" + quote(OPERACIONES["update_error"] + ": " + str(e)))


@login_required
def operaciones_eliminar(request: HttpRequest) -> HttpResponse:
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    cluster, bucket_name, scope_name, _ = _cb_bucket_scope()
    parte = request.POST.get("parte", "")
    id_grupo = request.POST.get("id_grupo", "")
    codigo = request.POST.get("codigo", "")
    try:
        eliminar_subgrupo(cluster, bucket_name, scope_name, parte, id_grupo, codigo)
        return _redirect_303(
            f"/operaciones?parte={quote(parte)}&grupo={quote(id_grupo)}&success={quote(OPERACIONES['delete_success'])}"
        )
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/operaciones?error=" + quote(OPERACIONES["delete_error"] + ": " + str(e)))


@login_required
def operaciones_actualizar_tablas(request: HttpRequest) -> HttpResponse:
    """Ejecuta script_actualizar_tablas.py para sincronizar las tablas de la tablet con Couchbase."""
    denied = _require_any_role(request, {ROLE_ADMIN})
    if denied:
        return denied
    if request.method != "POST":
        return _redirect_303("/operaciones")

    import sys
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script_path = os.path.join(base_dir, "scripts", "actualizar_tablas.py")

    parte = request.POST.get("parte", "")
    id_grupo = request.POST.get("id_grupo", "")
    qs = ""
    if parte:
        qs += f"&parte={quote(parte)}"
    if id_grupo:
        qs += f"&grupo={quote(id_grupo)}"

    if not os.path.isfile(script_path):
        return _redirect_303(
            f"/operaciones?error={quote('No se encontró scripts/actualizar_tablas.py')}{qs}"
        )

    try:
        # Forzamos UTF-8 en el subprocess para que el script hijo pueda
        # imprimir caracteres no-ASCII (emojis, acentos) sin romper en Windows
        # con cp1252. PYTHONIOENCODING aplica al stdout/stderr del hijo;
        # encoding/errors aplican a la decodificación que hace subprocess.
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [sys.executable, script_path],
            cwd=base_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
            timeout=180,
            check=False,
        )
        if proc.returncode == 0:
            return _redirect_303(
                f"/operaciones?success={quote('Tablas de la tablet actualizadas correctamente.')}{qs}"
            )
        err = (proc.stderr or proc.stdout or "Error desconocido").strip().splitlines()[-1][:200]
        return _redirect_303(
            f"/operaciones?error={quote('Error al actualizar tablas: ' + err)}{qs}"
        )
    except subprocess.TimeoutExpired:
        return _redirect_303(
            f"/operaciones?error={quote('Timeout: el script tardó demasiado en responder.')}{qs}"
        )
    except Exception as e:  # noqa: BLE001
        return _redirect_303(
            f"/operaciones?error={quote('Error al ejecutar el script: ' + str(e))}{qs}"
        )


@login_required
def consultar_datos_post(request: HttpRequest) -> HttpResponse:
    cluster, _, _, clausula_from = _cb_bucket_scope()
    tramo = request.POST.get("tramo") or None
    via = request.POST.get("via") or None
    tipo_busqueda = request.POST.get("tipo_busqueda", "mediciones") or "mediciones"
    fecha_inicio = request.POST.get("fecha_inicio") or None
    fecha_fin = request.POST.get("fecha_fin") or None
    pto_km_ini_raw = request.POST.get("pto_km_ini") or None
    pto_km_fin_raw = request.POST.get("pto_km_fin") or None
    confirmar_consulta_grande = request.POST.get("confirmar_consulta_grande", "0") == "1"

    try:
        pto_km_ini = float(pto_km_ini_raw) if pto_km_ini_raw not in ("", None) else None
    except ValueError:
        pto_km_ini = None
    try:
        pto_km_fin = float(pto_km_fin_raw) if pto_km_fin_raw not in ("", None) else None
    except ValueError:
        pto_km_fin = None

    if not tramo or not via:
        return _redirect_303("/consultar-datos?error=" + quote("Los campos Tramo y Vía son obligatorios."))

    try:
        supera_limite = consulta_supera_limite(
            cluster,
            clausula_from,
            tipo_busqueda,
            tramo,
            via,
            LIMITE_AVISO_CONSULTA_GRANDE,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            pto_km_ini=pto_km_ini,
            pto_km_fin=pto_km_fin,
        )
    except Exception as e:  # noqa: BLE001
        return _redirect_303(
            "/consultar-datos?error=" + quote("No se pudo validar el tamano de la consulta: " + str(e))
        )

    if False and supera_limite and not confirmar_consulta_grande:
        html = page_confirmacion_consulta_grande(
            LIMITE_AVISO_CONSULTA_GRANDE,
            tramo,
            via,
            tipo_busqueda,
            fecha_inicio,
            fecha_fin,
            pto_km_ini_raw,
            pto_km_fin_raw,
        )
        return HttpResponse(html, content_type="text/html; charset=utf-8")

    try:
        if tipo_busqueda == "mediciones":
            resultados = buscar_mediciones(
                cluster,
                clausula_from,
                tramo,
                via,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                pto_km_ini=pto_km_ini,
                pto_km_fin=pto_km_fin,
            )
            html = page_consultar_datos_mediciones_resultados(
                tramo or "",
                via or "",
                pto_km_ini,
                pto_km_fin,
                fecha_inicio or "",
                fecha_fin or "",
                resultados,
            )
        elif tipo_busqueda == "inspecciones":
            resultados = buscar_inspecciones(
                cluster,
                clausula_from,
                tramo,
                via,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                pto_km_ini=pto_km_ini,
                pto_km_fin=pto_km_fin,
            )
            html = page_consultar_datos_inspecciones_resultados(
                tramo or "",
                via or "",
                pto_km_ini,
                pto_km_fin,
                fecha_inicio or "",
                fecha_fin or "",
                resultados,
            )
        elif tipo_busqueda == "formularios":
            resultados = buscar_formularios(
                cluster,
                clausula_from,
                tramo,
                via,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                pto_km_ini=pto_km_ini,
                pto_km_fin=pto_km_fin,
            )
            html = page_consultar_datos_formularios_resultados(
                tramo or "",
                via or "",
                pto_km_ini,
                pto_km_fin,
                fecha_inicio or "",
                fecha_fin or "",
                resultados,
            )
        elif tipo_busqueda == "incidencias":
            fecha_ini = fecha_inicio if fecha_inicio not in ("", None) else None
            fecha_fin_ = fecha_fin if fecha_fin not in ("", None) else None
            pk_ini = pto_km_ini if isinstance(pto_km_ini, (int, float)) else None
            pk_fin = pto_km_fin if isinstance(pto_km_fin, (int, float)) else None
            try:
                resultados = buscar_incidencias_agrupadas(
                    cluster, clausula_from, tramo, via, fecha_ini, fecha_fin_, pk_ini, pk_fin
                )
                html = page_consultar_datos_incidencias_resultados(
                    tramo or "",
                    via or "",
                    pk_ini,
                    pk_fin,
                    fecha_ini or "",
                    fecha_fin_ or "",
                    resultados,
                )
            except CouchbaseException as e:
                traceback.print_exc()
                return _redirect_303("/consultar-datos?error=" + quote(f"Error en la consulta de incidencias (Couchbase): {e}"))
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return _redirect_303("/consultar-datos?error=" + quote(f"Error al procesar incidencias: {e}"))
        else:
            return _redirect_303("/consultar-datos?error=" + quote(f"Tipo de búsqueda no soportado: {tipo_busqueda}"))

        html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" defer></script>
</head>
<body class="bg-light">
{html}
</body>
</html>
"""
        return _html_response(request, html)
    except Exception as e:  # noqa: BLE001
        return _redirect_303("/consultar-datos?error=" + quote(f"Error al ejecutar la búsqueda: {str(e)}"))


@login_required
def tabla(request: HttpRequest) -> HttpResponse:
    cluster, _, _, clausula_from = _cb_bucket_scope()
    kpigs_seleccionados = request.POST.getlist("kpigs")
    incidencias_seleccionadas = request.POST.getlist("incidencias")
    indicadores_operativa = request.POST.getlist("indicadores")

    fecha_inicio = request.POST.get("fecha_inicio") or None
    fecha_fin = request.POST.get("fecha_fin") or None
    id_tramo = request.POST.get("tramo") or None
    id_via = request.POST.get("via") or None
    pto_km_ini_raw = request.POST.get("pto_km_ini")
    pto_km_fin_raw = request.POST.get("pto_km_fin")
    coordenada_gps = (request.POST.get("coordenada_gps", "") or "").strip()
    radio_raw = request.POST.get("radio")
    radio_km = None
    if radio_raw not in (None, "", "null"):
        try:
            radio_km = float(radio_raw)
        except ValueError:
            radio_km = None

    try:
        pto_km_ini = float(pto_km_ini_raw) if pto_km_ini_raw not in ("", None, "null") else None
    except Exception:  # noqa: BLE001
        pto_km_ini = None
    try:
        pto_km_fin = float(pto_km_fin_raw) if pto_km_fin_raw not in ("", None, "null") else None
    except Exception:  # noqa: BLE001
        pto_km_fin = None

    cuadrantes_seleccionados: list[int] = []
    # Nuevo (multi-clic) + compatibilidad con legado (single).
    raw_multi = (request.POST.get("cuadrantes_seleccionados", "") or "").strip()
    raw_legacy = (request.POST.get("cuadrante_seleccionado", "") or "").strip()
    if raw_multi:
        for part in raw_multi.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                cuadrantes_seleccionados.append(int(part))
            except ValueError:
                continue
    elif raw_legacy:
        try:
            cuadrantes_seleccionados = [int(raw_legacy)]
        except ValueError:
            cuadrantes_seleccionados = []

    if pto_km_ini is not None and pto_km_fin is not None and pto_km_ini > pto_km_fin:
        error = (
            "El punto kilometrico de inicio no puede ser mayor que el punto kilometrico de fin. "
            f"Datos introducidos: tramo={id_tramo or '(sin dato)'}, via={id_via or '(sin dato)'}, "
            f"km_inicio={pto_km_ini}, km_fin={pto_km_fin}"
        )
        return _redirect_303("/filtros?error=" + quote(error))

    if fecha_inicio and fecha_fin:
        f_ini = str(fecha_inicio).replace("-", "")
        f_fin = str(fecha_fin).replace("-", "")
        if f_ini > f_fin:
            error = (
                "La fecha de inicio no puede ser mayor que la fecha de fin. "
                f"Datos introducidos: tramo={id_tramo or '(sin dato)'}, via={id_via or '(sin dato)'}, "
                f"fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}"
            )
            return _redirect_303("/filtros?error=" + quote(error))

    try:
        geo_resultado = None
        geo_mapa_payload = None
        tramos_a_calcular: list[tuple[str, str | None]] = []

        if not id_tramo and cuadrantes_seleccionados and not (coordenada_gps or radio_km is not None):
            # Flujo principal: selección directa en mapa.
            encontrados = resolver_tramos_por_cuadrantes(cluster, clausula_from, cuadrantes_seleccionados)
            for t in encontrados:
                tramos_a_calcular.append((t.id_tramo, t.id_via or id_via))

        elif not id_tramo and (coordenada_gps or radio_km is not None):
            if not coordenada_gps or radio_km is None:
                raise ValueError("Para localización geográfica debe indicar coordenada GPS y radio")
            geo_resultado = resolver_tramo_por_ambito_geografico(
                cluster, clausula_from, coordenada_gps, radio_km
            )
            geo_mapa_payload = resolver_mapa_por_ambito_geografico(
                cluster,
                clausula_from,
                coordenada_gps,
                radio_km,
            )
            for t in geo_resultado.todos_los_tramos:
                tramos_a_calcular.append((t.id_tramo, t.id_via or id_via))
        elif id_tramo:
            tramos_a_calcular.append((id_tramo, id_via))

        # Si hay selección de cuadrantes ("solo marcados"), filtramos los tramos
        # usando el payload del mapa (segmentos y sus cuadrantes asociados).
        if geo_mapa_payload and cuadrantes_seleccionados:
            selected_set = {int(x) for x in cuadrantes_seleccionados if x is not None}
            tramos_set: set[tuple[str, str | None]] = set()
            for seg in geo_mapa_payload.get("segmentos") or []:
                seg_cuads = set(seg.get("cuadrantes") or [])
                if seg_cuads & selected_set:
                    tramos_set.add((str(seg.get("id_tramo") or ""), seg.get("id_via")))

            tramos_a_calcular = sorted(tramos_set, key=lambda t: t[0])

        if not tramos_a_calcular:
            raise ValueError("Debe seleccionar un tramo o informar una localización geográfica válida")

        if len(tramos_a_calcular) > 1:
            id_tramo = [t[0] for t in tramos_a_calcular]
            id_via = None
        else:
            id_tramo = tramos_a_calcular[0][0]
            id_via = tramos_a_calcular[0][1]

        datos = obtener_todos_los_datos(
            cluster, clausula_from, id_tramo, fecha_inicio, fecha_fin, pto_km_ini, pto_km_fin, id_via
        )

        if geo_resultado:
            mensaje_parametros = construir_mensaje_parametros(geo_resultado)
        else:
            parametros = []
            if id_tramo:
                parametros.append(f"Tramo: {id_tramo}")
            if id_via:
                parametros.append(f"Vía: {id_via}")
            if pto_km_ini is not None and pto_km_fin is not None:
                parametros.append(f"KM: {pto_km_ini}-{pto_km_fin}")
            if fecha_inicio:
                parametros.append(f"Fecha inicio: {fecha_inicio}")
            if fecha_fin:
                parametros.append(f"Fecha fin: {fecha_fin}")
            mensaje_parametros = "<div class='alert alert-info mb-3'><strong>Parámetros:</strong><br>"
            mensaje_parametros += " | ".join(parametros)
            mensaje_parametros += "</div>"

        contenido_html = ""
        error_message = None
        aviso_message = None
        # El mapa solo se muestra en /filtros (no en resultados).
        leaflet_head_html = ""
        geo_map_html = ""

        if kpigs_seleccionados:
            try:
                todos_tramos_maestro = datos.get("tramos", [])

                def get_tipologia_tramo(id_t: str, tramos_maestro: list[dict[str, Any]]) -> str:
                    for t in tramos_maestro:
                        if t.get("id_tramo") == id_t:
                            return t.get("tipologia", "DESCONOCIDA")
                    return "DESCONOCIDA"

                grupos_por_tipologia: dict[str, list[tuple[str, str | None]]] = {}
                for (t_id, t_via) in tramos_a_calcular:
                    tip = get_tipologia_tramo(t_id, todos_tramos_maestro)
                    grupos_por_tipologia.setdefault(tip, []).append((t_id, t_via))

                resultados_por_tipologia: list[tuple[list[Any], int, dict[str, Any]]] = []
                avisos_kpi: list[dict[str, str]] = []
                for tipologia, tramos_grupo in grupos_por_tipologia.items():  # noqa: ARG001
                    lista_ids_grupo = [t[0] for t in tramos_grupo]
                    id_tramo_grupo: Any = lista_ids_grupo if len(lista_ids_grupo) > 1 else lista_ids_grupo[0]
                    id_tramo_rep = tramos_grupo[0][0]
                    id_via_rep = tramos_grupo[0][1]
                    vias_set = {v for _, v in tramos_grupo if v is not None and str(v).strip() != ""}
                    id_via_calc = id_via_rep if len(vias_set) == 1 else None

                    datos_grupo = obtener_todos_los_datos(
                        cluster,
                        clausula_from,
                        id_tramo_grupo,
                        fecha_inicio,
                        fecha_fin,
                        pto_km_ini,
                        pto_km_fin,
                        id_via_calc,
                    )

                    resultado_grupo: list[Any] = []
                    kpigs_no_calculables_grupo: list[tuple[str, str]] = []
                    for kpi in kpigs_seleccionados:
                        try:
                            resultado_kpi = calcular_indicadores(
                                datos_grupo, [kpi], id_tramo_rep, pto_km_ini, pto_km_fin, id_via_calc
                            )
                            if resultado_kpi:
                                resultado_grupo.extend(resultado_kpi)
                            else:
                                kpigs_no_calculables_grupo.append((kpi, "sin resultado para el tramo seleccionado"))
                        except Exception as e:  # noqa: BLE001
                            motivo = str(e).strip() or "error no especificado"
                            kpigs_no_calculables_grupo.append((kpi, motivo))

                    if kpigs_no_calculables_grupo:
                        tramos_txt = ", ".join(lista_ids_grupo)
                        tipologia_txt = tipologia or "SIN TIPOLOGIA"
                        for kpi, motivo in kpigs_no_calculables_grupo:
                            avisos_kpi.append(
                                {
                                    "kpi": kpi,
                                    "tramos": tramos_txt,
                                    "tipologia": tipologia_txt,
                                    "motivo": motivo,
                                }
                            )

                    med_grupo = datos_grupo.get("mediciones", {})
                    n_muestras = (
                        (med_grupo.get("muestras_rectas") or 0)
                        + (med_grupo.get("muestras_curvas_poste") or 0)
                        + (med_grupo.get("muestras_curvas_vano") or 0)
                    )
                    if resultado_grupo:
                        resultados_por_tipologia.append((resultado_grupo, n_muestras, datos_grupo))

                def combinar_resultados(resultados_lista: list[tuple[list[Any], int, dict[str, Any]]]) -> list[Any]:
                    if len(resultados_lista) == 1:
                        return resultados_lista[0][0]
                    total_muestras = sum(n for _, n, _ in resultados_lista if n > 0)
                    if total_muestras == 0:
                        return resultados_lista[0][0]

                    kpis_por_nombre: dict[str, list[tuple[list[Any], int]]] = {}
                    for resultado, n_muestras, _ in resultados_lista:
                        for entry in resultado:
                            nombre = entry[0]
                            kpis_por_nombre.setdefault(nombre, []).append((entry, n_muestras))

                    resultado_combinado: list[Any] = []
                    for nombre, entradas in kpis_por_nombre.items():
                        base = entradas[0][0]
                        if (
                            nombre in ("Ind_KPIG2", "Ind_KPIG6", "Ind_KPIG7")
                            and len(base) > 5
                            and isinstance(base[5], dict)
                        ):
                            detalle_combinado: dict[str, Any] = {}
                            valor_max_total = 0
                            for entry, n in entradas:  # noqa: ARG001
                                if len(entry) <= 5 or not isinstance(entry[5], dict):
                                    continue
                                for subtipo, subdatos in entry[5].items():
                                    if subtipo not in detalle_combinado:
                                        detalle_combinado[subtipo] = {
                                            "suma_valor": 0,
                                            "suma_n": 0,
                                            "valor_max": 0,
                                            "muestras": 0,
                                            "referencia": subdatos.get("referencia", 0),
                                        }
                                    sub = detalle_combinado[subtipo]
                                    sub_n = subdatos.get("muestras", 0)
                                    sub["suma_valor"] += subdatos["valor"] * sub_n
                                    sub["suma_n"] += sub_n
                                    sub["muestras"] += sub_n
                                    sub["valor_max"] = max(sub["valor_max"], subdatos.get("valor_max", 0))

                            detalle_final: dict[str, Any] = {}
                            pesos_total = 0
                            valor_pond = 0
                            for subtipo, sub in detalle_combinado.items():
                                valor_medio = sub["suma_valor"] / sub["suma_n"] if sub["suma_n"] > 0 else 0
                                detalle_final[subtipo] = {
                                    "valor": round(valor_medio, 2),
                                    "valor_max": round(sub["valor_max"], 2),
                                    "muestras": sub["muestras"],
                                    "referencia": sub["referencia"],
                                }
                                if nombre == "Ind_KPIG6":
                                    detalle_final[subtipo]["valor_medio"] = round(valor_medio, 2)
                                valor_pond += valor_medio * sub["muestras"]
                                pesos_total += sub["muestras"]
                                valor_max_total = max(valor_max_total, sub["valor_max"])

                            kpig_pond = round(valor_pond / pesos_total, 2) if pesos_total > 0 else 0
                            nueva_entry = list(base)
                            nueva_entry[1] = kpig_pond
                            nueva_entry[5] = detalle_final
                            if len(nueva_entry) > 6:
                                nueva_entry[6] = round(valor_max_total, 2)
                            resultado_combinado.append(nueva_entry)
                        elif nombre in ("Ind_KPIG1", "Ind_KPIG3", "Ind_KPIG8", "Ind_KPIG10", "Ind_KG1"):
                            valor_pond = sum(e[1] * n for e, n in entradas)
                            nueva_entry = list(base)
                            nueva_entry[1] = round(valor_pond / total_muestras, 2)
                            resultado_combinado.append(nueva_entry)
                        elif nombre in (
                            "Ind_KPIG4",
                            "Ind_KPIG5",
                            "Ind_KPIG9",
                            "Ind_KPIG11",
                            "Ind_KPIG13",
                            "Ind_KPIG14",
                        ):
                            nueva_entry = list(base)
                            nueva_entry[1] = round(max(e[1] for e, _ in entradas), 2)
                            resultado_combinado.append(nueva_entry)
                        else:
                            valor_pond = sum(e[1] * n for e, n in entradas)
                            nueva_entry = list(base)
                            nueva_entry[1] = round(valor_pond / total_muestras, 2)
                            resultado_combinado.append(nueva_entry)
                    return resultado_combinado

                resultado_final = combinar_resultados(resultados_por_tipologia)
                if not resultado_final:
                    raise ValueError("No se pudieron calcular los indicadores seleccionados")
                if avisos_kpi:
                    avisos_items = [
                        (
                            "<li><strong>"
                            + escape(item["kpi"])
                            + ":</strong> "
                            + escape(item["motivo"])
                            + "<br><small>Tramo(s): "
                            + escape(item["tramos"])
                            + " | Tipología: "
                            + escape(item["tipologia"])
                            + "</small></li>"
                        )
                        for item in avisos_kpi
                    ]
                    avisos_visibles = "".join(avisos_items[:3])
                    avisos_extra = "".join(avisos_items[3:])
                    bloque_extra = (
                        "<details class='mt-2'><summary style='cursor:pointer;'>Ver más</summary>"
                        "<ul class='mt-2 mb-0 ps-3'>"
                        + avisos_extra
                        + "</ul></details>"
                        if len(avisos_items) > 3
                        else ""
                    )
                    aviso_message = (
                        "<div class='alert alert-warning mb-3'>"
                        "<strong>AVISO:</strong> no se han podido calcular algunos KPIs."
                        "<p class='mb-2 mt-2'>Detalle por KPI (umbrales/tipología o filtros tramo-vía-km):</p>"
                        "<ul class='mb-0 ps-3'>"
                        + avisos_visibles
                        + "</ul>"
                        + bloque_extra
                        + "</div>"
                    )
                pintar(resultado_final, "gauges_output.html")
                with open("gauges_output.html", "r", encoding="utf-8") as f:
                    contenido_html += f.read()

                # Guardar datos en sesión para descarga PDF.
                import json as _json
                try:
                    request.session["pdf_resultado_final"] = _json.dumps(resultado_final)
                    request.session["pdf_aviso_message"] = aviso_message or ""
                    request.session["pdf_parametros"] = mensaje_parametros
                except Exception:
                    pass
            except Exception as e:  # noqa: BLE001
                error_message = f"Error al calcular indicadores: {str(e)}"

        elif incidencias_seleccionadas:
            # Limpiamos cualquier KPI residual en sesión: este flujo no genera PDF.
            for _k in ("pdf_resultado_final", "pdf_aviso_message", "pdf_parametros"):
                request.session.pop(_k, None)
            if "conteo_inc" not in datos:
                error_message = "No se encontraron datos de incidencias"
            else:
                try:
                    fichero = pintar_incidencias(datos["conteo_inc"], incidencias_seleccionadas)
                    with open(fichero, "r", encoding="utf-8") as f:
                        contenido_html += f.read()
                except Exception as e:  # noqa: BLE001
                    error_message = f"Error al generar gráfico de incidencias: {str(e)}"

        elif indicadores_operativa:
            # Limpiamos KPIs residuales: este flujo tampoco genera PDF de KPIs.
            for _k in ("pdf_resultado_final", "pdf_aviso_message", "pdf_parametros"):
                request.session.pop(_k, None)
            try:
                resultados = obtener_indicadores_operativa(
                    cluster, clausula_from, id_tramo, id_via, fecha_inicio, fecha_fin
                )
                indicadores_sel = set(indicadores_operativa)
                labels: list[str] = []
                valores: list[Any] = []
                if "inspecciones" in indicadores_sel:
                    labels.append("Inspecciones realizadas")
                    valores.append(resultados.get("inspecciones", 0))
                if "formularios" in indicadores_sel:
                    labels.append("Informes manuales")
                    valores.append(resultados.get("formularios", 0))
                if "km" in indicadores_sel:
                    labels.append("Km auscultados")
                    valores.append(resultados.get("km", 0.0))
                if "errores" in indicadores_sel:
                    labels.append("Errores detectados")
                    valores.append(resultados.get("errores", 0))
                if not labels:
                    error_message = "No se seleccionó ningún indicador de operativa."
                else:
                    pto_km_ini_str = "" if pto_km_ini is None else str(pto_km_ini)
                    pto_km_fin_str = "" if pto_km_fin is None else str(pto_km_fin)
                    fecha_ini_str = fecha_inicio or ""
                    fecha_fin_str = fecha_fin or ""
                    contenido_html = page_indicadores_operativa_resultados(
                        id_tramo or "",
                        id_via or "",
                        pto_km_ini_str,
                        pto_km_fin_str,
                        fecha_ini_str,
                        fecha_fin_str,
                        labels,
                        valores,
                        mensaje_parametros,
                    )
                    return HttpResponse(contenido_html, content_type="text/html; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                prefix = INDICADORES.get("error_operativa", "Error al procesar los indicadores de operativa")
                error_message = f"{prefix}: {str(e)}"

        else:
            error_message = "Debe seleccionar KPIs, incidencias o indicadores de operativa"

        if error_message:
            return _redirect_303("/filtros?error=" + quote(error_message))

        # geo_mapa_payload se usa para filtrar tramos (backend), pero no se pinta en resultados.

        # Botón PDF solo si hay KPIs calculados (resultado_final guardado en sesión).
        tiene_kpis = bool(request.session.get("pdf_resultado_final"))
        boton_pdf_html = ""
        modal_pdf_html = ""
        if tiene_kpis:
            boton_pdf_html = """
<button class="btn btn-danger btn-sm" onclick="abrirModalPDF()">
    <i class="bi bi-file-earmark-pdf-fill me-1"></i>Descargar PDF
</button>"""
            modal_pdf_html = """
<!-- Modal configuración PDF -->
<div class="modal fade" id="modalPDF" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header bg-danger text-white">
                <h5 class="modal-title">Configurar descarga PDF</h5>
                <button type="button" class="btn-close btn-close-white" onclick="cerrarModalPDF()"></button>
            </div>
            <div class="modal-body">
                <div class="mb-3">
                    <label class="form-label fw-bold">Título del documento</label>
                    <input type="text" class="form-control" id="pdf-titulo"
                                 value="Informe de KPIs - Indicadores de Catenaria">
                    <div class="form-text">Aparecerá en la cabecera del PDF.</div>
                </div>
                <div class="mb-3">
                    <label class="form-label fw-bold">Nombre del archivo</label>
                    <div class="input-group">
                        <input type="text" class="form-control" id="pdf-filename" value="informe_kpis">
                        <span class="input-group-text">.pdf</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="cerrarModalPDF()">Cancelar</button>
                <button type="button" class="btn btn-danger" id="btn-generar-pdf" onclick="descargarPDF()">
                    <span id="pdf-spin" class="spinner-border spinner-border-sm me-1 d-none"></span>
                    Generar y descargar
                </button>
            </div>
        </div>
    </div>
</div>
<script>
function abrirModalPDF() {
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPDF')).show();
}
function cerrarModalPDF() {
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalPDF')).hide();
}
function descargarPDF() {
    var titulo = document.getElementById('pdf-titulo').value.trim() || 'Informe KPIs';
    var filename = (document.getElementById('pdf-filename').value.trim() || 'informe_kpis').replace(/\\.pdf$/i, '') + '.pdf';
    document.getElementById('pdf-spin').classList.remove('d-none');
    document.getElementById('btn-generar-pdf').disabled = true;
    var url = '/descargar-pdf-kpis?titulo=' + encodeURIComponent(titulo) + '&filename=' + encodeURIComponent(filename);
    fetch(url)
        .then(function(r) {
            if (!r.ok) throw new Error('Error ' + r.status);
            return r.blob();
        })
        .then(function(blob) {
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            a.click();
            URL.revokeObjectURL(a.href);
        })
        .catch(function(e) { alert('Error al generar el PDF: ' + e.message); })
        .finally(function() {
            document.getElementById('pdf-spin').classList.add('d-none');
            document.getElementById('btn-generar-pdf').disabled = false;
            bootstrap.Modal.getInstance(document.getElementById('modalPDF')).hide();
        });
}
</script>"""

        html = f"""
<html>
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
  {leaflet_head_html}
</head>
<body class="bg-light">
  <div class="container mt-4">
    {mensaje_parametros}
    {aviso_message or ""}
    {geo_map_html}
    <!-- Botones arriba a la derecha -->
    <div class="d-flex justify-content-end gap-2 mb-3">
      <a href="/filtros" class="btn btn-primary btn-sm"><i class="bi bi-arrow-left me-1"></i>Volver</a>
      {boton_pdf_html}
    </div>
    {contenido_html}
  </div>
    {modal_pdf_html}
</body>
</html>
"""
        return HttpResponse(html, content_type="text/html; charset=utf-8")
    except Exception as e:  # noqa: BLE001
        msg = f"Error procesando los filtros: {str(e)}"
        return _redirect_303("/filtros?error=" + quote(msg))


def descargar_pdf_kpis(request: HttpRequest) -> HttpResponse:
    """
    Genera un PDF con los gauges de KPIs usando Plotly/kaleido para exportar
    cada gráfico como PNG y reportlab para componer el documento.
    Los datos se leen de la sesión Django (guardados por la vista 'tabla').
    """
    import io
    import json as _json
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)

    try:
        import plotly.graph_objects as go
        import plotly.io as pio

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
            HRFlowable, Table, TableStyle, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER
    except Exception as e:
        logger.error(f"Error importando librerías PDF: {str(e)}", exc_info=True)
        return HttpResponse(f"Error importando librerías: {str(e)}", status=500)

    # Parámetros de la petición.
    titulo = request.GET.get("titulo", "Informe de KPIs - Indicadores de Catenaria")
    filename = request.GET.get("filename", "informe_kpis")
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    logger.info(f"Iniciando generación PDF - título: {titulo}, filename: {filename}")

    # Datos guardados en sesión.
    resultado_final_raw = request.session.get("pdf_resultado_final")
    aviso_message_raw = request.session.get("pdf_aviso_message", "")
    mensaje_parametros = request.session.get("pdf_parametros", "")

    logger.info(f"Iniciando generación PDF - resultado_final_raw existe: {bool(resultado_final_raw)}")

    if not resultado_final_raw:
        logger.error("No hay datos de KPIs en sesión")
        return HttpResponse("No hay datos de KPIs en sesión. Vuelve a calcular.", status=400)

    try:
        resultado_final = _json.loads(resultado_final_raw)
        logger.info(f"Datos de sesión cargados correctamente, {len(resultado_final)} entradas")
    except Exception as e:
        logger.error(f"Error leyendo datos de sesión: {str(e)}", exc_info=True)
        return HttpResponse("Error leyendo datos de sesión.", status=500)

    # Extraer parámetros en texto plano.
    import re as _re
    from html.parser import HTMLParser as _HTMLParser

    params_texto = _re.sub(r'<[^>]+>', '', mensaje_parametros).strip()
    params_texto = _re.sub(r'\s+', ' ', params_texto).replace("Parámetros:", "").strip()

    # Parsear aviso HTML en bullets de texto.
    class _AvisoParser(_HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []
            self._in_li = False
            self._in_strong = False
            self._in_small = False
            self._cur_kpi = ""
            self._cur_motivo = ""
            self._cur_small = ""

        def handle_starttag(self, tag, attrs):
            if tag == 'li':
                self._in_li = True
                self._cur_kpi = ""
                self._cur_motivo = ""
                self._cur_small = ""
                self._in_strong = False
            elif tag == 'strong' and self._in_li:
                self._in_strong = True
            elif tag == 'small':
                self._in_small = True

        def handle_endtag(self, tag):
            if tag == 'li':
                self._in_li = False
                self._in_small = False
                if self._cur_kpi or self._cur_motivo:
                    self.items.append((
                        self._cur_kpi.strip().rstrip(':'),
                        self._cur_motivo.strip(),
                        self._cur_small.strip(),
                    ))
            elif tag == 'strong':
                self._in_strong = False
            elif tag == 'small':
                self._in_small = False

        def handle_data(self, data):
            if self._in_li:
                if self._in_strong:
                    self._cur_kpi += data
                elif self._in_small:
                    self._cur_small += data
                else:
                    self._cur_motivo += data

    aviso_items_parsed = []
    if aviso_message_raw:
        parser = _AvisoParser()
        try:
            parser.feed(aviso_message_raw)
            aviso_items_parsed = parser.items
        except Exception:
            pass

    # Generar una imagen PNG por cada gauge.
    gauge_images = []
    colors_list = [
        {"name": "Mala", "color": "#D73027"},
        {"name": "Deficiente", "color": "#FC8D59"},
        {"name": "Regular", "color": "#FEE08B"},
        {"name": "Aceptable", "color": "#91CF60"},
        {"name": "Buena", "color": "#1A9850"},
    ]
    kg1_thresholds = {
        'valores_N4': [0, 2], 'valores_N3': [2, 3.5],
        'valores_N2': [3.5, 5.5], 'valores_N1': [5.5, 7], 'valores_N0': [7, 10],
    }
    descripciones = {
        "Ind_KPIG1": "Altura media del HC respecto del plano de la vía",
        "Ind_KPIG2": "Descentramiento medio del HC respecto al eje longitudinal",
        "Ind_KPIG3": "Desviación de altura en curva",
        "Ind_KPIG4": "Desviación inferior máxima de la altura del HC",
        "Ind_KPIG5": "Desviación superior máxima de la altura del HC",
        "Ind_KPIG6": "Desviación media de descentramiento del HC",
        "Ind_KPIG7": "Desviación máxima de descentramiento del HC",
        "Ind_KPIG8": "Flecha media del HC",
        "Ind_KPIG9": "Contraflecha máxima del HC",
        "Ind_KPIG10": "Contraflecha media del HC",
        "Ind_KPIG11": "Desviación máxima de la contraflecha del HC",
        "Ind_KPIG12": "Efecto tijera en zonas comunes o de solape",
        "Ind_KPIG13": "Desviación máxima de la pendiente del HC",
        "Ind_KPIG14": "Desviación máxima de la Δ de la pendiente del HC",
        "Ind_KG1": "Índice de Calidad de Geometría",
    }
    unidades = {
        "Ind_KPIG1": "m", "Ind_KPIG2": "cm", "Ind_KPIG3": "%", "Ind_KPIG4": "%",
        "Ind_KPIG5": "%", "Ind_KPIG6": "%", "Ind_KPIG7": "%", "Ind_KPIG8": "%",
        "Ind_KPIG9": "%", "Ind_KPIG10": "cm", "Ind_KPIG11": "%", "Ind_KPIG12": "%",
        "Ind_KPIG13": "%", "Ind_KPIG14": "%", "Ind_KG1": "",
    }

    def _zones_from_umbral(umbral, valor_maximo, value):
        if not umbral:
            return [], None, None, None, None, []
        try:
            thresholds = {}
            has_zero_zone = False
            for i in range(5):
                key = f'valores_N{i}'
                if key in umbral:
                    thresholds[i] = list(map(float, umbral[key]))
                    if i == 0 or 0 in thresholds[i]:
                        has_zero_zone = True
            if not thresholds:
                return [], None, None, None, None, []
            all_vals = [v for lst in thresholds.values() for v in lst]
            max_val = float(valor_maximo) if valor_maximo else max(all_vals)
            avail_c = [c["color"] for c in colors_list]
            sorted_levels = sorted([k for k in thresholds if k != 0], reverse=True)
            if not sorted_levels:
                return [], None, None, None, None, []
            zonas = []
            for i, lev in enumerate(sorted_levels):
                zonas.append({'min': thresholds[lev][0], 'max': thresholds[lev][1], 'color': avail_c[i % len(avail_c)]})
            if has_zero_zone:
                zonas.append({'min': thresholds[sorted_levels[-1]][1], 'max': max_val, 'color': colors_list[4]["color"]})
            else:
                zonas.insert(0, {'min': 0, 'max': thresholds[sorted_levels[-1]][0], 'color': colors_list[4]["color"]})
            zonas = sorted(zonas, key=lambda x: x['min'])
            n = len(zonas)
            if n == 0 or max_val == 0:
                return [], None, None, None, None, []
            step_size = max_val / n

            steps = [{"range": [i * step_size, (i + 1) * step_size], "color": z['color']} for i, z in enumerate(zonas)]

            def _remap_value(v):
                if v is None:
                    return None
                for i, z in enumerate(zonas):
                    if z['min'] <= v <= z['max']:
                        denom = z['max'] - z['min']
                        ratio = (v - z['min']) / denom if denom else 0
                        return i * step_size + ratio * step_size
                return max_val if v > zonas[-1]['max'] else 0

            adj = _remap_value(value)
            valor_ref_original = float(umbral.get('valor_referencia')) if 'valor_referencia' in umbral else None
            valor_ref_remapeado = _remap_value(valor_ref_original)

            return steps, max_val, adj, valor_ref_original, valor_ref_remapeado, zonas
        except Exception:
            return [], None, None, None, None, []

    def _make_gauge_png(name, value, steps, max_val, adj, unit, valor_ref_remapeado, tipo_label=None, zonas=None):
        logger.info(f"Generando PNG para gauge: {name}, value={value}, unit={unit}")
        desc = descripciones.get(name, name)
        titulo_gauge = name
        if tipo_label:
            titulo_gauge += f" - {tipo_label}"
        subtitle = desc
        if tipo_label:
            subtitle += f" - {tipo_label}"
        if unit:
            subtitle += f" ({unit})"

        steps_final = list(steps)
        if adj is not None and adj > 0:
            steps_final = list(steps)
            steps_final.append({"range": [0, adj], "color": "darkblue", "thickness": 0.5})

        gauge_cfg = {
            "axis": {"range": [0, max_val], "showticklabels": False},
            "bar": {"color": "darkblue", "thickness": 0.0},
            "steps": steps_final,
            "shape": "angular",
            "bgcolor": "white",
        }

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number={"valueformat": ".2f", "suffix": f" {unit}" if unit else ""},
            title={"text": f"<b>{titulo_gauge}</b><br><span style='font-size:13px'>{subtitle}</span>", "font": {"size": 15}},
            gauge=gauge_cfg,
        ))

        if zonas:
            parts = []
            for z in zonas:
                lo, hi = z['min'], z['max']
                hi_str = "∞" if hi >= 9000 else f"{hi:.2f}"
                parts.append(f"<span style='color:{z['color']}'>■</span> {lo:.2f}-{hi_str}")
            fig.add_annotation(
                text="  ".join(parts),
                xref="paper", yref="paper",
                x=0.5, y=-0.12,
                showarrow=False,
                font=dict(size=9, family="Arial"),
                align="center",
                xanchor="center",
            )

        fig.update_layout(
            height=430, width=480,
            margin=dict(t=160, b=80, l=40, r=40),
            font=dict(family="Arial", size=12),
            paper_bgcolor="white",
        )
        try:
            logger.info(f"Intentando generar PNG con kaleido para {name}")
            png_bytes = pio.to_image(fig, format="png", scale=2, engine="kaleido")
            logger.info(f"PNG generado exitosamente con kaleido para {name}")
        except Exception as e:
            logger.warning(f"Kaleido falló para {name}: {str(e)}, intentando fallback")
            # Fallback: try without specifying engine
            try:
                png_bytes = pio.to_image(fig, format="png", scale=2)
                logger.info(f"PNG generado con fallback para {name}")
            except Exception as e2:
                logger.error(f"Fallback falló para {name}: {str(e2)}, intentando export a archivo")
                # Last resort: use plotly's static export
                try:
                    import tempfile
                    import os
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp_path = tmp.name
                    pio.write_image(fig, tmp_path, format="png", scale=2)
                    with open(tmp_path, 'rb') as f:
                        png_bytes = f.read()
                    os.unlink(tmp_path)
                    logger.info(f"PNG generado con export a archivo para {name}")
                except Exception as e3:
                    logger.error(f"Todos los métodos fallaron para {name}: kaleido={e}, fallback={e2}, file_export={e3}", exc_info=True)
                    raise Exception(f"Error generating PNG with kaleido: {e}, fallback failed: {e2}, static export failed: {e3}")
        return subtitle, png_bytes

    for entry in resultado_final:
        if not entry or len(entry) < 2:
            continue
        name = entry[0]
        if not isinstance(entry[1], (int, float)):
            continue
        value = float(entry[1])
        unit = unidades.get(name, entry[3] if len(entry) > 3 else "")

        if name in ("Ind_KPIG6", "Ind_KPIG2", "Ind_KPIG7") and len(entry) > 5 and isinstance(entry[5], dict):
            for tipo, datos in entry[5].items():
                tipo_label = {'recto': 'Recta', 'curva_poste': 'Curva Poste', 'curva_vano': 'Curva Vano'}.get(tipo, tipo)
                val2 = datos.get('valor')
                vmax2 = datos.get('valor_max')
                umbral2 = entry[4].get(tipo) if len(entry) > 4 and isinstance(entry[4], dict) else None
                if val2 is None:
                    continue
                steps2, mx2, adj2, vref2, vref2_remap, zonas2 = _zones_from_umbral(umbral2, vmax2, float(val2))
                if not steps2:
                    continue
                _, png_bytes = _make_gauge_png(name, float(val2), steps2, mx2, adj2, unit, vref2_remap, tipo_label, zonas2)
                gauge_images.append((f"{name} - {tipo_label}", png_bytes))
        else:
            umbral = entry[4] if len(entry) > 4 else None
            vmax = entry[2] if len(entry) > 2 else None
            if name == "Ind_KG1":
                steps, mx, adj, vref, vref_remap, zonas = _zones_from_umbral(kg1_thresholds, 10, value)
            else:
                steps, mx, adj, vref, vref_remap, zonas = _zones_from_umbral(umbral, vmax, value)
            if not steps:
                continue
            _, png_bytes = _make_gauge_png(name, value, steps, mx, adj, unit, vref_remap, None, zonas)
            gauge_images.append((name, png_bytes))

    logger.info(f"Total de imágenes de gauge generadas: {len(gauge_images)}")

    if not gauge_images:
        logger.error("No se pudieron generar imágenes de los gauges")
        return HttpResponse("No se pudieron generar imágenes de los gauges.", status=500)

    buffer = io.BytesIO()

    PAGE_W, PAGE_H = A4
    MARGEN = 15 * mm

    logger.info("Iniciando construcción del PDF con reportlab")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGEN, rightMargin=MARGEN,
        topMargin=MARGEN, bottomMargin=20 * mm,
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'TituloPDF', parent=estilos['Title'],
        fontSize=16, textColor=colors.white,
        spaceAfter=4, alignment=TA_CENTER, fontName='Helvetica-Bold',
    )
    estilo_fecha = ParagraphStyle(
        'FechaPDF', parent=estilos['Normal'],
        fontSize=9, textColor=colors.HexColor('#6c757d'),
        spaceAfter=6, alignment=TA_CENTER,
    )
    estilo_params = ParagraphStyle(
        'ParamsPDF', parent=estilos['Normal'],
        fontSize=9, textColor=colors.HexColor('#0d47a1'),
        backColor=colors.HexColor('#e8f4ff'),
        borderColor=colors.HexColor('#0d6efd'),
        borderWidth=0.5, borderPadding=6,
        spaceAfter=8, spaceBefore=4,
    )
    estilo_aviso_titulo = ParagraphStyle(
        'AvisoTitulo', parent=estilos['Normal'],
        fontSize=9, textColor=colors.HexColor('#664d03'),
        fontName='Helvetica-Bold',
        backColor=colors.HexColor('#fff3cd'),
        spaceAfter=2, spaceBefore=0,
    )
    estilo_aviso_sub = ParagraphStyle(
        'AvisoSub', parent=estilos['Normal'],
        fontSize=8, textColor=colors.HexColor('#664d03'),
        backColor=colors.HexColor('#fff3cd'),
        spaceAfter=3, spaceBefore=0,
    )
    estilo_aviso_item = ParagraphStyle(
        'AvisoItem', parent=estilos['Normal'],
        fontSize=8, textColor=colors.HexColor('#664d03'),
        backColor=colors.HexColor('#fff3cd'),
        leftIndent=10, spaceAfter=1, spaceBefore=0,
    )
    estilo_aviso_small = ParagraphStyle(
        'AvisoSmall', parent=estilos['Normal'],
        fontSize=7, textColor=colors.HexColor('#8a6d3b'),
        backColor=colors.HexColor('#fff3cd'),
        leftIndent=20, spaceAfter=3, spaceBefore=0,
    )

    story = []

    import os
    # Ruta base del proyecto (raíz donde está manage.py)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(BASE_DIR, "img", "logo.png")
    logo_path = os.path.normpath(logo_path)
    ANCHO_UTIL = PAGE_W - 2 * MARGEN

    if os.path.exists(logo_path):
        logo_img = RLImage(logo_path, width=50 * mm, height=25 * mm, kind='proportional')
        solutia_path = os.path.join(BASE_DIR, "img", "solutia.png")
        solutia_path = os.path.normpath(solutia_path)

        if os.path.exists(solutia_path):
            sol_img = RLImage(solutia_path, width=40 * mm, height=20 * mm, kind='proportional')
            header_table = Table(
                [[logo_img, Paragraph(titulo, estilo_titulo), sol_img]],
                colWidths=[55 * mm, ANCHO_UTIL - 55 * mm - 45 * mm, 45 * mm],
                rowHeights=[28 * mm],
            )
        else:
            header_table = Table(
                [[logo_img, Paragraph(titulo, estilo_titulo)]],
                colWidths=[55 * mm, ANCHO_UTIL - 55 * mm],
                rowHeights=[28 * mm],
            )
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0d6efd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
        ]))
        story.append(header_table)
    else:
        story.append(Paragraph(titulo, estilo_titulo))

    fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Generado el {fecha_gen}", estilo_fecha))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0d6efd'), spaceAfter=6))

    if params_texto:
        story.append(Paragraph(f"<b>Parámetros:</b> {params_texto}", estilo_params))

    if aviso_items_parsed or aviso_message_raw:
        aviso_parrafos = []
        aviso_parrafos.append(Paragraph("■ <b>AVISO:</b> no se han podido calcular algunos KPIs.", estilo_aviso_titulo))
        aviso_parrafos.append(Paragraph("Detalle por KPI (umbrales/tipología o filtros tramo-vía-km):", estilo_aviso_sub))
        for kpi, motivo, small in aviso_items_parsed:
            aviso_parrafos.append(Paragraph(f"• <b>{kpi}:</b> {motivo}", estilo_aviso_item))
            if small:
                aviso_parrafos.append(Paragraph(small, estilo_aviso_small))

        aviso_table = Table([[p] for p in aviso_parrafos], colWidths=[ANCHO_UTIL])
        aviso_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#ffc107')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (0, 0), 6),
            ('BOTTOMPADDING', (0, len(aviso_parrafos) - 1), (0, len(aviso_parrafos) - 1), 6),
        ]))
        story.append(aviso_table)
        story.append(Spacer(1, 6 * mm))

    story.append(Spacer(1, 4 * mm))

    ANCHO_GAUGE = (ANCHO_UTIL - 8 * mm) / 2
    ALTO_GAUGE = ANCHO_GAUGE * 430 / 480

    pares = [gauge_images[i:i + 2] for i in range(0, len(gauge_images), 2)]
    for par in pares:
        celdas = []
        for _, png_bytes in par:
            img_buf = io.BytesIO(png_bytes)
            rl_img = RLImage(img_buf, width=ANCHO_GAUGE, height=ALTO_GAUGE)
            celdas.append(rl_img)
        if len(celdas) == 1:
            celdas.append("")

        fila_table = Table(
            [celdas],
            colWidths=[ANCHO_GAUGE, ANCHO_GAUGE],
            rowHeights=[ALTO_GAUGE + 4 * mm],
        )
        fila_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#dee2e6')),
            ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#dee2e6')),
        ]))
        story.append(KeepTogether(fila_table))
        story.append(Spacer(1, 3 * mm))

    def _pie(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6c757d'))
        canvas.drawString(MARGEN, 12 * mm, "Sistema de Gestión de Catenarias")
        canvas.drawRightString(PAGE_W - MARGEN, 12 * mm, f"Página {doc_obj.page}")
        canvas.setStrokeColor(colors.HexColor('#dee2e6'))
        canvas.setLineWidth(0.5)
        canvas.line(MARGEN, 16 * mm, PAGE_W - MARGEN, 16 * mm)
        canvas.restoreState()

    try:
        logger.info("Construyendo PDF con doc.build()")
        doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
        logger.info("PDF construido exitosamente")
    except Exception as e:
        logger.error(f"Error construyendo PDF con reportlab: {str(e)}", exc_info=True)
        raise

    pdf_bytes = buffer.getvalue()
    logger.info(f"PDF generado exitosamente, tamaño: {len(pdf_bytes)} bytes")
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



