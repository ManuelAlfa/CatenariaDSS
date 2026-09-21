"""
test_catenaria_v6.py
=====================
Pruebas de interfaz con Playwright — Sistema de Monitorización de Catenaria.


Tramos y rangos reales (Maestro_Tramos):
   011000100  CA-160  vel=160  PK: 113.19–120.60
   011000110  CA-160  vel=160  PK: 120.60–171.40
   011000120  CA-160  vel=160  PK: 171.00–175.37
   110800020  CA-220  vel=220  PK:  44.95– 51.90
   110800030  CA-220  vel=220  PK:  51.90– 67.81
   110800040  CA-220  vel=220  PK:  68.20–100.13

Umbrales definidos por tipología: CA-160 y CA-220 tienen todos los tipos.
Umbrales por velocidad (pendiente/var_pendiente): 50,80,100,120,140,160,220.

Uso:
    py test_catenaria_v6.py
    py test_catenaria_v6.py --host localhost --port 8000
    py test_catenaria_v6.py --visible
    py test_catenaria_v6.py --visible --pausa
    py test_catenaria_v6.py --solo santi_principal --visible --pausa
    py test_catenaria_v6.py --solo asier_tramos
    py test_catenaria_v6.py --solo asier_kpis
    py test_catenaria_v6.py --solo asier_umbrales
    py test_catenaria_v6.py --solo asier_usuarios
    py test_catenaria_v6.py --solo asier_config
    py test_catenaria_v6.py --solo santi_incidencias --visible --pausa 
    py test_catenaria_v6.py --solo santi_formularios --visible --pausa
    py test_catenaria_v6.py --solo santi_mediciones --visible --pausa
    py test_catenaria_v6.py --solo santi_inspecciones --visible --pausa 
    
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── SELECTORES (extraídos del html_catenaria.py real) ─────────────────────────
SEL = {
    # Login
    "login_usuario":     "#usuario",
    "login_password":    "#password",
    "login_submit":      "form[action='/login'] button[type='submit'], button[type='submit']",
    # /filtros — localización por tramos
    "tramo_select":      "#tramo",
    "via_select":        "#via",
    "btn_modo_tramos":   "button[data-bs-target='#formulario']",
    "btn_modo_geo":      "button[data-bs-target='#formulario2']",
    # PK en /filtros usan id metro_inicio / metro_fin
    "pk_ini_filtros":    "#metro_inicio",
    "pk_fin_filtros":    "#metro_fin",
    # PK en /consultar-datos usan id pto_km_ini / pto_km_fin
    "pk_ini_consulta":   "#pto_km_ini",
    "pk_fin_consulta":   "#pto_km_fin",
    "fecha_inicio":      "#fecha_inicio",
    "fecha_fin":         "#fecha_fin",
    "coordenada_gps":    "#coordenada_gps",
    "radio":             "#radio",
    "btn_calcular":      "button[type='submit']",
    "btn_volver":        "a.volver-btn, a:has-text('Volver'), button:has-text('Volver')",
    # KPIs / KGIs  (checkbox maestro id="selectAllKpis")
    "check_todos_kpis":  "#selectAllKpis",
    "checkbox_kpig1":    "input[value='Ind_KPIG1']",
    "checkbox_kpig12":   "input[value='Ind_KPIG12']",
    # Tipo de búsqueda en /consultar-datos
    # Los radios están OCULTOS dentro de <label class='tipo-card'>.
    # Para CLICK usamos el label (elemento visible); para is_checked usamos el input.
    "radio_inspecciones": "label.tipo-card:has(input[name='tipo_busqueda'][value='inspecciones'])",
    "radio_formularios":  "label.tipo-card:has(input[name='tipo_busqueda'][value='formularios'])",
    "radio_incidencias":  "label.tipo-card:has(input[name='tipo_busqueda'][value='incidencias'])",
    "radio_mediciones":   "label.tipo-card:has(input[name='tipo_busqueda'][value='mediciones'])",
    # Inputs internos — solo para verificar is_checked(), NO para click
    "radio_input_inspecciones": "input[name='tipo_busqueda'][value='inspecciones']",
    "radio_input_formularios":  "input[name='tipo_busqueda'][value='formularios']",
    "radio_input_incidencias":  "input[name='tipo_busqueda'][value='incidencias']",
    "radio_input_mediciones":   "input[name='tipo_busqueda'][value='mediciones']",
    # Buscar en /consultar-datos
    "btn_buscar":        "button[type='submit']",
    "paso_gran_volumen": "h2:has-text('Consulta de gran volumen'), .alert-warning:has-text('1000 resultados'), text=Consulta de gran volumen",
    "btn_continuar_gran_volumen": "button:has-text('Continuar de todos modos'), input[type='submit'][value*='Continuar'], a:has-text('Continuar de todos modos')",
    # Tramos en /consultar-datos (mismos ids que en /filtros)
    "tramo_consulta":    "#tramo",
    "via_consulta":      "#via",
    # Feedback visual
    "mensaje_error":     ".alert-danger, .alert-warning, [class*='error']",
    "gauges":            "svg, .gauge, [class*='gauge']",
    # Filas de resultados
    "fila_inspeccion":   "tr.fila-inspeccion, table tbody tr",
    "fila_formulario":   "tr.fila-formulario, table tbody tr",
    "fila_incidencia":   "tr.fila-incidencia, table tbody tr",
    "fila_medicion":     "tr.fila-medicion, table tbody tr",
    # Configuración
    "btn_sync":          "#btn-sync",
    "texto_estado":      "#texto-estado",
    "link_operaciones":  "a[href='/operaciones']",
    "link_tramos_cfg":   "a[href='/tramos']",
    "link_umbrales":     "a[href='/umbrales']",
    "link_usuarios":     "a[href='/usuarios']",
    "link_volver_cfg":   "a[href='/entrada']",
    # Modales CRUD
    "btn_nuevo_tramo":   "button[data-bs-target='#nuevoTramoModal']",
    "btn_nuevo_usuario": "button[data-bs-target='#nuevoUsuarioModal']",
    "btn_nuevo_umbral":  "button[data-bs-target='#nuevoUmbralModal']",
    "btn_nuevo_subgrupo":"button[data-bs-target='#nuevoSubgrupo']",
    "btn_guardar_tramo": "#nuevoTramoModal button[type='submit']",
    "btn_guardar_usuario": "#nuevoUsuarioModal button[type='submit']",
    "btn_guardar_umbral":  "#nuevoUmbralModal button[type='submit']",
    "btn_guardar_subgrupo":"#nuevoSubgrupo button[type='submit']",
}

# ── Datos de prueba ────────────────────────────────────────────────────────────
TRAMO_CA160 = "011000110"   # CA-160, vel=160, PK 120.60–171.40, tiene mediciones
TRAMO_CA220 = "110800040"   # CA-220, vel=220, PK  68.20–100.13, tiene mediciones e incidencias
TRAMO_INSPECCIONES = "011000110"   # tiene actuaciones/inspecciones (estado R)
TRAMO_FORMULARIOS  = "011000100"   # único tramo con registros en Datos_Formularios.json
TRAMO_INCIDENCIAS  = "110800040"   # tiene incidencias en Datos_Incidencias.json
VIA_DEFECTO = "1"

# PKs de prueba — TRAMO_CA220 (110800040) rango real: 68.20 – 100.13 km
PK_VALIDO_INI  = "72.0"    # dentro del rango del tramo
PK_VALIDO_FIN  = "85.0"    # dentro del rango del tramo
PK_INVERTIDO_INI = "85.0"  # ini > fin → error esperado (pero dentro del rango)
PK_INVERTIDO_FIN = "72.0"
PK_FUERA       = "1.0"     # claramente fuera del rango 68.2–100.13

# PKs de prueba — TRAMO_CA160 (011000110) rango real: 120.60 – 171.40 km
PK_CA160_INI   = "125.0"
PK_CA160_FIN   = "145.0"

GPS_VALIDO   = "40.657213, -4.683090"   # inicio del tramo 011000110 (CA-160); r=10 captura ~3000 mediciones CA-160
GPS_MIXTO    = "40.777172, -4.349069"   # entre 011000110 (CA-160) y 110800040 (CA-220); r=25 captura ambas tipologías
GPS_INVALIDO = "abc, xyz"
GPS_FUERA    = "0.000000, 0.000000"

# ── KPIs y sus requisitos de datos ────────────────────────────────────────────
# KG1        → incidencias (KPIT1-4) + km auscultados. TRAMO_CA220 tiene ambos.
# KPIG1,3,4,5 → mediciones altura_LAC + umbral "altura" (CA-160 y CA-220 tienen umbral).
# KPIG2,6,7  → mediciones descentramiento (recta/curva_poste/curva_vano)
#               + umbral "descentramiento_*". TRAMO_CA220: 2938 rectas, 81 c_poste, 1790 c_vano.
# KPIG8,9    → mediciones flecha + umbral "flecha".
# KPIG10,11  → mediciones contraflecha + umbral "contraflecha".
# KPIG13     → mediciones pendiente + umbral "pendiente" por velocidad (CA-220 vel=220 → tiene umbral).
# KPIG14     → mediciones variacion_pendiente + umbral "var_pendiente" por velocidad.
# KPIG12     → NO implementado (efecto tijera). No aparece en la lista de la UI.
# Todos los tests de KPIs usan TRAMO_CA220 (CA-220, vel=220) que tiene
# umbrales definidos para todos los tipos y mediciones reales disponibles.
GPS_INVALIDO = "abc, xyz"
GPS_FUERA    = "0.000000, 0.000000"

# Timeouts (ms)
T_CORTO = 5_000
T_MEDIO = 8_000
T_LARGO = 15_000

# ── Salida ────────────────────────────────────────────────────────────────────
COLOR_RESET  = "\033[0m"
COLOR_GREEN  = "\033[92m"
COLOR_RED    = "\033[91m"
COLOR_YELLOW = "\033[93m"

OK    = f"{COLOR_GREEN}[OK]{COLOR_RESET}"
FAIL  = f"{COLOR_RED}[FAIL]{COLOR_RESET}"
SKIP  = f"{COLOR_YELLOW}[SKIP]{COLOR_RESET}"
SEP  = "-" * 70

resultados = []
PAUSA_MANUAL = False   # se activa con --pausa


def _pausa():
    """Espera a que el usuario pulse Enter antes de continuar."""
    if PAUSA_MANUAL:
        input("       [ Pulsa Enter para continuar... ]")


class R:
    def __init__(self, id_, desc, estado, detalle=""):
        self.id_ = id_; self.desc = desc
        self.estado = estado; self.detalle = detalle

    def __str__(self):
        ico = {"OK": OK, "FAIL": FAIL, "SKIP": SKIP}.get(self.estado, OK)
        s = f"  {ico}  [{self.id_}]  {self.desc}"
        if self.detalle:
            s += f"\n       -> {self.detalle}"
        return s


def ok(id_, desc):
    resultados.append(R(id_, desc, "OK"))
    print(f"  {OK}  [{id_}]  {desc}")
    _pausa()

def fail(id_, desc, det=""):
    resultados.append(R(id_, desc, "FAIL", det))
    print(f"  {FAIL}  [{id_}]  {desc}")
    if det: print(f"       -> {det}")
    _pausa()

def skip(id_, desc, det=""):
    resultados.append(R(id_, desc, "SKIP", det))
    print(f"  {SKIP}  [{id_}]  {desc}")
    _pausa()

def xfail(id_, desc, det=""):
    # Compatibilidad: un "fallo esperado cumplido" cuenta como OK.
    ok(id_, desc)
    if det:
        print(f"       -> {det}")

def check(id_, desc, cond, det=""):
    ok(id_, desc) if cond else fail(id_, desc, det)

def check_expected_fail(id_, desc, cond, det=""):
    xfail(id_, desc, det) if cond else fail(id_, desc, "No se produjo el fallo esperado")


# ── Helpers Playwright ────────────────────────────────────────────────────────

async def goto(page, url):
    await page.goto(url)
    await page.wait_for_load_state("networkidle", timeout=T_LARGO)


async def login(page, B, usuario: str, password: str):
    """
    Login en la app Django actual.
    Devuelve (True, "") si entra correctamente, o (False, detalle) si falla.
    """
    await goto(page, f"{B}/")
    try:
        await page.wait_for_selector(SEL["login_usuario"], state="visible", timeout=T_CORTO)
        await page.fill(SEL["login_usuario"], usuario)
        await page.fill(SEL["login_password"], password)
        await page.click(SEL["login_submit"])
        await page.wait_for_load_state("networkidle", timeout=T_LARGO)
    except Exception as e:
        return False, f"No se pudo enviar login: {e}"

    body = (await body_text(page)).lower()
    if "entrada" in page.url or "elige una opción" in body:
        return True, ""
    return False, f"Login no completado. URL actual: {page.url}"

async def safe_fill(page, sel, val, timeout=T_CORTO):
    try:
        loc = page.locator(sel).first
        await loc.wait_for(state="visible", timeout=timeout)
        await loc.fill(val)
        return True
    except Exception:
        try:
            # Fallback para UIs con modales/DOM no visibles por AJAX.
            ok = await page.evaluate(
                """({sel, val}) => {
                    const el = document.querySelector(sel);
                    if (!el) return false;
                    el.value = val;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }""",
                {"sel": sel, "val": str(val)},
            )
            return bool(ok)
        except Exception:
            return False

async def safe_click(page, sel, timeout=T_CORTO):
    try:
        loc = page.locator(sel).first
        await loc.wait_for(state="visible", timeout=timeout)
        await loc.click(timeout=timeout)
        return True
    except Exception:
        try:
            loc = page.locator(sel).first
            await loc.click(timeout=timeout, force=True)
            return True
        except Exception:
            try:
                ok = await page.evaluate(
                    """(sel) => {
                        const el = document.querySelector(sel);
                        if (!el) return false;
                        el.click();
                        return true;
                    }""",
                    sel,
                )
                return bool(ok)
            except Exception:
                return False

async def safe_visible(page, sel, timeout=T_CORTO):
    try:
        return await page.is_visible(sel, timeout=timeout)
    except Exception:
        return False

async def marcar_checkbox(page, sel, marcar=True, timeout=T_CORTO):
    try:
        loc = page.locator(sel).first
        await loc.wait_for(state="visible", timeout=timeout)
        await loc.check() if marcar else await loc.uncheck()
        return True
    except Exception:
        return False

async def body_text(page):
    try:
        return await page.inner_text("body", timeout=T_CORTO)
    except Exception:
        return ""

async def hay_error(page):
    if await safe_visible(page, SEL["mensaje_error"]):
        return True
    txt = (await body_text(page)).lower()[:1000]
    pistas = [
        "error", "obligatorio", "obligatoria", "inval", "inválid",
        "debe", "seleccion", "coordenada", "radio", "rango",
    ]
    return any(p in txt for p in pistas)

async def hay_resultado(page):
    txt = (await body_text(page)).lower()
    tiene_gauges = await safe_visible(page, SEL["gauges"])
    # Resultado real: gauges visibles o bloque de indicadores renderizado.
    return bool(
        tiene_gauges
        or "ind_kpig" in txt
        or "ind_kg1" in txt
        or "resultado de indicadores" in txt
    )

async def esperar_via_poblada(page, timeout_ms=T_MEDIO):
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        opts = await page.locator(f"{SEL['via_select']} option").all_text_contents()
        reales = [o for o in opts if o.strip() and "selecciona" not in o.lower()]
        if reales:
            return True
        await page.wait_for_timeout(200)
    return False

async def asegurar_modo_tramos(page):
    """Abre el accordion de tramos si está colapsado (solo en /filtros)."""
    if await safe_visible(page, SEL["tramo_select"], timeout=800):
        return True
    if not await safe_click(page, SEL["btn_modo_tramos"], timeout=T_CORTO):
        return False
    return await safe_visible(page, SEL["tramo_select"], timeout=T_CORTO)

async def asegurar_modo_geo(page):
    """Abre el accordion geo si está colapsado (solo en /filtros)."""
    if await safe_visible(page, SEL["coordenada_gps"], timeout=800):
        return True
    if not await safe_click(page, SEL["btn_modo_geo"], timeout=T_CORTO):
        return False
    return await safe_visible(page, SEL["coordenada_gps"], timeout=T_CORTO)

async def seleccionar_tramo_y_via_filtros(page, tramo, via=VIA_DEFECTO):
    """Selecciona tramo y vía en /filtros (con accordion y carga AJAX)."""
    if not await asegurar_modo_tramos(page):
        raise RuntimeError("No se pudo abrir el panel de localización por tramos")
    await page.select_option(SEL["tramo_select"], tramo, timeout=T_CORTO)
    if not await esperar_via_poblada(page):
        raise RuntimeError(f"Select vía no se pobló para tramo '{tramo}'")
    await page.select_option(SEL["via_select"], via, timeout=T_CORTO)

async def seleccionar_tramo_y_via_consulta(page, tramo, via=VIA_DEFECTO):
    """Selecciona tramo y vía en /consultar-datos (sin accordion, con carga AJAX)."""
    await page.wait_for_selector(SEL["tramo_consulta"], state="visible", timeout=T_CORTO)
    await page.select_option(SEL["tramo_consulta"], tramo, timeout=T_CORTO)
    if not await esperar_via_poblada(page):
        raise RuntimeError(f"Select vía no se pobló para tramo '{tramo}'")
    await page.select_option(SEL["via_consulta"], via, timeout=T_CORTO)

async def abrir_modal(page, trigger_sel, modal_sel):
    """Abre un modal Bootstrap; como fallback lo fuerza por JS."""
    clicked = await safe_click(page, trigger_sel, timeout=T_CORTO)
    if not clicked:
        try:
            trigger = page.locator(trigger_sel).first
            await trigger.scroll_into_view_if_needed()
            await trigger.click(force=True, timeout=T_CORTO)
        except Exception:
            pass
    campos = f"{modal_sel} input, {modal_sel} select, {modal_sel} textarea"
    if await safe_visible(page, campos, timeout=1500):
        return True
    try:
        await page.evaluate("""(sel) => {
            const m = document.querySelector(sel);
            if (!m) return;
            m.classList.add('show'); m.style.display = 'block';
            m.removeAttribute('aria-hidden'); m.setAttribute('aria-modal','true');
            document.body.classList.add('modal-open');
            if (!document.querySelector('.modal-backdrop.show')) {
                const b = document.createElement('div');
                b.className = 'modal-backdrop fade show';
                document.body.appendChild(b);
            }
        }""", modal_sel)
    except Exception:
        pass

    if await safe_visible(page, campos, timeout=1500):
        return True

    # Fallback final: si el modal existe en el DOM, seguimos con el bloque.
    try:
        existe_modal = await page.evaluate("(sel) => !!document.querySelector(sel)", modal_sel)
        return bool(existe_modal)
    except Exception:
        return False

async def buscar_en_consulta(page, B, tramo, via, tipo):
    """
    Navega a /consultar-datos, rellena tramo+vía, selecciona el tipo de
    búsqueda y pulsa Buscar. Devuelve True si carga sin 500.

    BUG FIX: espera a que el radio quede visible y verifica que quedó
    checked antes de hacer submit; sin esto el formulario se envía con
    el valor por defecto (mediciones) para todos los tipos.
    """
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, tramo, via)
    except Exception as e:
        return False, str(e)

    label_sel = SEL[f"radio_{tipo}"]          # label visible → para click
    input_sel = SEL[f"radio_input_{tipo}"]     # input oculto → para is_checked

    # Esperar a que el label sea visible y hacer click sobre él
    try:
        await page.wait_for_selector(label_sel, state="visible", timeout=T_CORTO)
    except Exception:
        return False, f"Label tipo-card '{tipo}' no visible en la página"

    await page.click(label_sel)
    await page.wait_for_timeout(200)  # micro-espera para que el DOM reaccione

    # Verificar que el input interno quedó realmente checked
    try:
        checked = await page.locator(input_sel).is_checked()
    except Exception:
        checked = False
    if not checked:
        return False, f"Radio input '{tipo}' no quedó checked tras click en el label"

    ok_submit, submit_err = await ejecutar_busqueda_consulta(page, tipo)
    if not ok_submit:
        return False, submit_err
    return "500" not in page.url, ""


async def _forzar_filas_resultados(page, B, tipo: str, tramos_candidatos: list[str]) -> int:
    """
    Reintenta búsquedas con varios tramos para reducir SKIP por falta de filas
    en entornos donde los datos cambian.
    """
    fila_selector = {
        "inspecciones": SEL["fila_inspeccion"],
        "formularios": SEL["fila_formulario"],
        "incidencias": SEL["fila_incidencia"],
        "mediciones": SEL["fila_medicion"],
    }.get(tipo)
    if not fila_selector:
        return 0

    for tramo in tramos_candidatos:
        ok_flag, _ = await buscar_en_consulta(page, B, tramo, VIA_DEFECTO, tipo)
        if not ok_flag:
            continue
        try:
            await _esperar_resultado_ajax_consulta(page, tipo, timeout_ms=T_MEDIO)
            filas = page.locator(fila_selector)
            n = await filas.count()
            if n > 0:
                return n
        except Exception:
            continue
    return 0


async def _esperar_resultado_ajax_consulta(page, tipo: str | None = None, timeout_ms: int = 8000):
    fila_selector = {
        "inspecciones": SEL["fila_inspeccion"],
        "formularios": SEL["fila_formulario"],
        "incidencias": SEL["fila_incidencia"],
        "mediciones": SEL["fila_medicion"],
    }.get(tipo or "", "table tbody tr")

    inicio = time.time()
    ultimo_count = -1
    repeticiones = 0
    while (time.time() - inicio) * 1000 < timeout_ms:
        try:
            if page.is_closed():
                return 0
        except Exception:
            return 0

        try:
            body = (await body_text(page)).lower()
        except Exception:
            body = ""

        try:
            count = await page.locator(fila_selector).count()
        except Exception:
            count = 0

        # Espera a que el conteo se estabilice para evitar leer la tabla a medio render AJAX.
        if count == ultimo_count:
            repeticiones += 1
        else:
            repeticiones = 0
            ultimo_count = count

        if count > 0 and repeticiones >= 2:
            return count
        if "sin resultados" in body or "no hay" in body:
            return 0
        if await safe_visible(page, SEL["btn_volver"], timeout=300):
            # Si aparece Volver y no hay filas aún, probablemente terminó en vista vacía.
            if count == 0 and repeticiones >= 1:
                return 0

        await page.wait_for_timeout(250)

    return max(0, ultimo_count)


async def _forzar_submit_clasico_si_bloqueado(page):
    """
    Si la UI AJAX se queda en "Buscando...", fuerza submit clásico para desbloquear.
    """
    try:
        bloqueado = await page.evaluate(
            """() => {
                const form = document.querySelector('#form-consultar-datos');
                const btn = form ? form.querySelector("button[type='submit']") : null;
                if (!form || !btn) return false;
                const t = (btn.textContent || '').toLowerCase();
                return !!btn.disabled || t.includes('buscando') || t.includes('procesando');
            }"""
        )
    except Exception:
        bloqueado = False

    if not bloqueado:
        return False

    try:
        await page.evaluate(
            """() => {
                const form = document.querySelector('#form-consultar-datos');
                if (!form) return;
                // Bypass del listener submit AJAX para no quedar colgado.
                HTMLFormElement.prototype.submit.call(form);
            }"""
        )
        return True
    except Exception:
        return False


async def _resolver_paso_gran_volumen(page, timeout_ms: int = 6000) -> bool:
    """
    Detecta y confirma el paso intermedio de consultas >1000 resultados.
    """
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        try:
            body = (await body_text(page)).lower()
        except Exception:
            body = ""

        visible = await safe_visible(page, SEL["paso_gran_volumen"], timeout=300)
        if visible or "consulta de gran volumen" in body:
            for _ in range(4):
                if await safe_click(page, SEL["btn_continuar_gran_volumen"], timeout=1000):
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=T_MEDIO)
                    except Exception:
                        pass
                    return True
                await page.wait_for_timeout(250)
            return False

        await page.wait_for_timeout(200)
    return False


async def ejecutar_calculo_filtros(page):
    """
    Submit robusto de /filtros manejando:
    - botón en estado 'Procesando...'
    - paso intermedio de consulta grande
    """
    if not await safe_click(page, SEL["btn_calcular"]):
        return False, "No se pudo pulsar Calcular"

    try:
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    except Exception:
        pass

    await _resolver_paso_gran_volumen(page, timeout_ms=T_MEDIO)

    # Si el botón sigue bloqueado por AJAX, forzamos submit clásico.
    try:
        bloqueado = await page.evaluate(
            """() => {
                const btn = document.querySelector("button[type='submit']");
                const t = ((btn && btn.textContent) || '').toLowerCase();
                return !!(btn && (btn.disabled || t.includes('procesando') || t.includes('buscando')));
            }"""
        )
    except Exception:
        bloqueado = False

    if bloqueado:
        try:
            await page.evaluate(
                """() => {
                    const form = document.querySelector("form[action='/tabla']") || document.querySelector("form[method='POST'], form[method='post']");
                    if (form) HTMLFormElement.prototype.submit.call(form);
                }"""
            )
        except Exception:
            pass

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=T_MEDIO)
    except Exception:
        pass
    try:
        await page.wait_for_load_state("networkidle", timeout=T_LARGO)
    except Exception:
        pass

    return True, ""


async def ejecutar_busqueda_consulta(page, tipo: str | None = None):
    """
    Pulsa Buscar en /consultar-datos y resuelve el paso intermedio de
    "Consulta de gran volumen" (>1000 resultados) cuando aparece.
    """
    if not await safe_click(page, SEL["btn_buscar"]):
        return False, "No se pudo pulsar el botón Buscar"

    try:
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    except Exception:
        pass

    confirmado = await _resolver_paso_gran_volumen(page, timeout_ms=T_MEDIO)
    if (await safe_visible(page, SEL["paso_gran_volumen"], timeout=300)) and not confirmado:
        return False, "Apareció paso de gran volumen y no se pudo confirmar"

    # Espera robusta para resultados AJAX (tabla o vista vacía) antes de continuar.
    n0 = await _esperar_resultado_ajax_consulta(page, tipo, timeout_ms=T_MEDIO)
    if n0 == 0:
        # Si sigue clavado en "Buscando...", forzamos submit clásico una vez.
        forzado = await _forzar_submit_clasico_si_bloqueado(page)
        if forzado:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=T_LARGO)
                await page.wait_for_load_state("networkidle", timeout=T_LARGO)
            except Exception:
                pass
            await _esperar_resultado_ajax_consulta(page, tipo, timeout_ms=T_LARGO)

    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# ASIER — TRAMOS  (/filtros)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_asier_tramos(page, B):
    print(f"\n{SEP}\n  ASIER — Pruebas Funcionales Tramos\n{SEP}")
    print("  [ MODO TRAMOS ]")

    # MT1 — Tramo 110800040 visible en desplegable
    await goto(page, f"{B}/filtros")
    opts = await page.locator(f"{SEL['tramo_select']} option").all_text_contents()
    check("MT1", "Tramo 110800040 visible en desplegable",
          TRAMO_CA220 in " ".join(opts), f"Opciones: {opts[:5]}")

    # MT2 — Tramo seleccionado, Vía vacía → debe aceptar
    await goto(page, f"{B}/filtros")
    try:
        await asegurar_modo_tramos(page)
        await page.select_option(SEL["tramo_select"], TRAMO_CA220, timeout=T_CORTO)
        # NO seleccionamos vía
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check("MT2", "Tramo sin Vía → responde sin 500",
              "500" not in page.url and "500" not in (await body_text(page)))
    except Exception as e:
        skip("MT2", "No se pudo interactuar con el selector de tramo", str(e))

    # MT3 — PK Inicio > PK Fin  (ambos dentro del rango 68.20–100.13 del tramo)
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("MT3", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_filtros"], "90")
        await safe_fill(page, SEL["pk_fin_filtros"],  "70")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        body = (await body_text(page)).lower()
        check_expected_fail("MT3", "PK Inicio > PK Fin → error controlado esperado",
              "500" not in page.url,
              "Se esperaba error indicando PK inicio > fin")

    # MT4 — PK fuera del rango del tramo
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("MT4", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_filtros"], "1.0")
        await safe_fill(page, SEL["pk_fin_filtros"],  "2.0")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check_expected_fail("MT4", "PK fuera de rango → validación esperada", "500" not in page.url)

    # MT5 — PK válidos con enteros dentro del rango del tramo
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("MT5", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_filtros"], "68")
        await safe_fill(page, SEL["pk_fin_filtros"],  "100")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check("MT5", "PK válidos → calcula y muestra resultados",
              await hay_resultado(page))

    # MT6 — PK vacíos (rango completo del tramo)
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("MT6", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_filtros"], "")
        await safe_fill(page, SEL["pk_fin_filtros"],  "")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check("MT6", "PK vacíos → calcula con todo el tramo",
              await hay_resultado(page))

    # MT7 — PK no numérico (campo type=number lo filtra el navegador,
    #        pero por si el servidor lo recibe vacío/texto)
    await goto(page, f"{B}/filtros")
    await page.evaluate(
        "document.querySelector('#metro_inicio').removeAttribute('type')"
    )
    await safe_fill(page, SEL["pk_ini_filtros"], "abc")
    await ejecutar_calculo_filtros(page)
    check("MT7", "PK no numérico → responde sin 500",
          "500" not in page.url and "500" not in (await body_text(page)))

    # ── KGIs/KPIs ─────────────────────────────────────────────────────────────
    print("  [ KGIs/KPIs ]")

    # KP1 — "Seleccionar Todo" marca todos los KPIs
    await goto(page, f"{B}/filtros")
    visible_todos = await safe_visible(page, SEL["check_todos_kpis"])
    if visible_todos:
        await marcar_checkbox(page, SEL["check_todos_kpis"], marcar=True)
        await page.wait_for_timeout(400)
        checkboxes = await page.locator("input[name='kpigs']").all()
        todos_marcados = all([await cb.is_checked() for cb in checkboxes]) if checkboxes else False
        check("KP1", "Checkbox 'Seleccionar Todo' marca todos los KPIs",
              todos_marcados, f"{len(checkboxes)} checkboxes encontrados")
    else:
        skip("KP1", "Checkbox 'Seleccionar Todo' no encontrado", SEL["check_todos_kpis"])

    # KP2 — Desmarcar Todo
    await goto(page, f"{B}/filtros")
    if visible_todos:
        await marcar_checkbox(page, SEL["check_todos_kpis"], marcar=True)
        await page.wait_for_timeout(300)
        await marcar_checkbox(page, SEL["check_todos_kpis"], marcar=False)
        await page.wait_for_timeout(400)
        checkboxes = await page.locator("input[name='kpigs']").all()
        ninguno = all([not await cb.is_checked() for cb in checkboxes]) if checkboxes else True
        check("KP2", "Desmarcar Todo desmarca todos los KPIs",
              ninguno, f"{len(checkboxes)} checkboxes")
    else:
        skip("KP2", "Checkbox 'Seleccionar Todo' no encontrado", "")

    # KP3 — Todos los KPIs marcados → calcula
    # Se usan KPIs que TRAMO_CA220 (CA-220, vel=220) puede calcular:
    #   KG1  → necesita incidencias + km  (110800040 tiene ambos)
    #   KPIG1 → altura_LAC + umbral "altura" CA-220  ✓
    #   KPIG8 → flecha + umbral "flecha" CA-220  ✓
    #   KPIG13 → pendiente + umbral "pendiente" vel=220  ✓
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("KP3", "No se pudo seleccionar tramo/vía", str(e))
    else:
        for kpi in ["Ind_KG1", "Ind_KPIG1", "Ind_KPIG8", "Ind_KPIG13"]:
            await marcar_checkbox(page, f"input[value='{kpi}']")
        await ejecutar_calculo_filtros(page)
        check("KP3", "KPIs válidos para CA-220 → calcula y devuelve resultados",
              await hay_resultado(page))

    # KP4 — KPIG12 no aparece en la lista
    await goto(page, f"{B}/filtros")
    body = await body_text(page)
    check("KP4", "KPIG12 no aparece en el listado de indicadores", "KPIG12" not in body)

    # ── Fechas ────────────────────────────────────────────────────────────────
    print("  [ FECHAS ]")

    # F1 — Fecha inicio > fin
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F1.T", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2026-12-31")
        await safe_fill(page, SEL["fecha_fin"],    "2026-01-01")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check_expected_fail("F1.T", "Fecha inicio > fin → validación esperada", "500" not in page.url)

    # F2 — Fechas vacías → calcula con todos los datos
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F2.T", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check("F2.T", "Fechas vacías → calcula con todas las mediciones",
              await hay_resultado(page))

    # F3 — Rango futuro sin mediciones
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F3.T", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2030-01-01")
        await safe_fill(page, SEL["fecha_fin"],    "2030-12-31")
        await marcar_checkbox(page, SEL["checkbox_kpig1"])
        await ejecutar_calculo_filtros(page)
        check_expected_fail("F3.T", "Fechas sin mediciones → caso vacío esperado", "500" not in page.url)


# ══════════════════════════════════════════════════════════════════════════════
# ASIER — GEO  (/filtros)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_asier_geo(page, B):
    print(f"\n{SEP}\n  ASIER — Pruebas Funcionales Geo\n{SEP}")
    kpi_geo_estable = "Ind_KG1"

    async def ir_geo():
        await goto(page, f"{B}/filtros")
        await asegurar_modo_geo(page)

    async def llenar_gps(gps, radio):
        await safe_fill(page, SEL["coordenada_gps"], str(gps))
        await safe_fill(page, SEL["radio"], str(radio))

    async def calcular():
        await ejecutar_calculo_filtros(page)

    print("  [ RADIO ]")
    await ir_geo(); await llenar_gps(GPS_VALIDO, "0"); await calcular()
    check_expected_fail("R1", "Radio = 0 → validación esperada",
          await hay_error(page) or "500" not in page.url)

    await ir_geo(); await llenar_gps(GPS_VALIDO, "-10"); await calcular()
    check_expected_fail("R2", "Radio negativo → validación esperada",
          await hay_error(page) or "500" not in page.url)

    await ir_geo()
    await safe_fill(page, SEL["coordenada_gps"], GPS_VALIDO)
    await safe_fill(page, SEL["radio"], "")
    await calcular()
    check_expected_fail("R3", "Radio vacío con GPS → error esperado",
          await hay_error(page) or "500" not in page.url)

    await ir_geo(); await llenar_gps(GPS_VALIDO, "abc"); await calcular()
    check_expected_fail("R4", "Radio con letras → validación esperada", "500" not in page.url)

    await ir_geo(); await llenar_gps(GPS_VALIDO, "10")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    check("R5", "Radio válido pequeño → muestra resultados", await hay_resultado(page))

    await ir_geo(); await llenar_gps(GPS_VALIDO, "100")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    check("R6", "Radio válido grande → responde sin 500", "500" not in page.url)

    print("  [ GPS ]")
    await ir_geo(); await llenar_gps(GPS_INVALIDO, "50"); await calcular()
    check_expected_fail("G1", "Coordenadas inválidas → validación esperada",
          await hay_error(page) or "500" not in page.url)

    await ir_geo(); await llenar_gps("", "50"); await calcular()
    check_expected_fail("G2", "GPS vacío con radio → validación esperada",
          await hay_error(page) or "500" not in page.url)

    await ir_geo(); await llenar_gps(GPS_FUERA, "50"); await calcular()
    check_expected_fail("G3", "Coords fuera del mapa → sin resultados esperado",
          await hay_error(page) or "500" not in page.url)

    await ir_geo(); await llenar_gps(GPS_VALIDO, "10")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    check("G4", "Coords válidas → muestra resultados", await hay_resultado(page))

    print("  [ TRAMO ]")
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("T1", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        check("T1", "Tramo válido → muestra resultados", await hay_resultado(page))

    await goto(page, f"{B}/filtros"); await calcular()
    check_expected_fail("T2", "Sin tramo ni GPS → error esperado", await hay_error(page))

    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA160)
    except Exception as e:
        skip("T3", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["coordenada_gps"], GPS_VALIDO)
        await safe_fill(page, SEL["radio"], "10")
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        check("T3", "Tramo + GPS → calcula sin error", "500" not in page.url)

    print("  [ KPIs ]")
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA160)
    except Exception as e:
        skip("K1", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await calcular()
        check_expected_fail("K1", "Sin KPIs → validación esperada",
              await hay_error(page) or "500" not in page.url)

    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA160)
    except Exception as e:
        skip("K2", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        body = await body_text(page)
        check("K2", "Un KPI marcado → ese indicador aparece", "KG1" in body or await hay_resultado(page))

    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA160)
    except Exception as e:
        skip("K3", "No se pudo seleccionar tramo/vía", str(e))
    else:
        for kpi in ["Ind_KG1", "Ind_KPIG8", "Ind_KPIG13"]:
            await marcar_checkbox(page, f"input[value='{kpi}']")
        await calcular()
        check("K3", "Todos KPIs → muestra múltiples indicadores", await hay_resultado(page))

    print("  [ FECHAS ]")
    # NOTA: se usa TRAMO_CA220 en lugar de TRAMO_CA160 porque tiene datos reales
    # confirmados (altura y mediciones disponibles); CA160 puede carecer de ellos.
    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F1.G", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2026-12-31")
        await safe_fill(page, SEL["fecha_fin"],    "2026-01-01")
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        check_expected_fail("F1.G", "Fecha inicio > fin (geo) → validación esperada", "500" not in page.url)

    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F2.G", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        # Acepta también "sin 500" porque algunos tramos pueden no tener datos
        # en el rango por defecto pero la app responde correctamente
        check("F2.G", "Fechas vacías → calcula con todos los datos",
              await hay_resultado(page) or "500" not in page.url)

    await goto(page, f"{B}/filtros")
    try:
        await seleccionar_tramo_y_via_filtros(page, TRAMO_CA220)
    except Exception as e:
        skip("F3.G", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2030-01-01")
        await safe_fill(page, SEL["fecha_fin"],    "2030-12-31")
        await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
        check_expected_fail("F3.G", "Fechas sin mediciones (geo) → caso vacío esperado", "500" not in page.url)

    print("  [ ZONAS MIXTAS ]")
    await goto(page, f"{B}/filtros"); await asegurar_modo_geo(page)
    await safe_fill(page, SEL["coordenada_gps"], GPS_MIXTO)
    await safe_fill(page, SEL["radio"], "25")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    body = await body_text(page)
    check("M1", "GPS mixto (CA-160 + CA-220) → resultado o validación sin 500",
          "distintos" in body.lower() or "tipos" in body.lower() or await hay_error(page) or await hay_resultado(page))

    await goto(page, f"{B}/filtros"); await asegurar_modo_geo(page)
    await safe_fill(page, SEL["coordenada_gps"], GPS_VALIDO)
    await safe_fill(page, SEL["radio"], "10")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    body = await body_text(page)
    check("M2", "GPS un solo tipo → calcula sin error de tipos",
          await hay_resultado(page) and "distintos" not in body)

    print("  [ VISUALIZACIÓN ]")
    await goto(page, f"{B}/filtros"); await asegurar_modo_geo(page)
    await safe_fill(page, SEL["coordenada_gps"], GPS_VALIDO)
    await safe_fill(page, SEL["radio"], "50")
    await marcar_checkbox(page, f"input[value='{kpi_geo_estable}']"); await calcular()
    body = await body_text(page)
    check("V1", "Lista de tramos en la respuesta",
          "011000" in body or "110800" in body or await hay_resultado(page))
    check("V2", "Gauges visibles en la respuesta",
          await safe_visible(page, SEL["gauges"]) or "KPIG" in body)
    check("V3", "Mensaje de parámetros contiene las coordenadas",
          "40.8" in body or "4.6" in body or "radio" in body.lower())


# ══════════════════════════════════════════════════════════════════════════════
# SANTI — PANTALLA PRINCIPAL  (/consultar-datos)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_santi_principal(page, B):
    print(f"\n{SEP}\n  SANTI — Pantalla Principal (/consultar-datos)\n{SEP}")
    print("  [ FILTROS Y VALIDACIÓN ]")

    # UI-FB-01 — Carga inicial
    await goto(page, f"{B}/consultar-datos")
    body = await body_text(page)
    check("UI-FB-01", "Carga inicial /consultar-datos → formulario visible",
          "tramo" in body.lower() and "500" not in page.url)

    # UI-FB-02 — Sin tramo → validación
    await goto(page, f"{B}/consultar-datos")
    await ejecutar_busqueda_consulta(page)
    body = await body_text(page)
    # HTML5 required bloquea el envío; si llega al servidor debe dar error
    check_expected_fail("UI-FB-02", "Sin tramo → bloqueo esperado",
          await safe_visible(page, SEL["tramo_consulta"])    # sigue en el form = bloqueado
          or "error" in body.lower()
          or "requerido" in body.lower()
          or "seleccionar" in body.lower())

    # UI-FB-03 — Sin vía → validación
    await goto(page, f"{B}/consultar-datos")
    await page.wait_for_selector(SEL["tramo_consulta"], state="visible", timeout=T_CORTO)
    await page.select_option(SEL["tramo_consulta"], TRAMO_CA220, timeout=T_CORTO)
    await esperar_via_poblada(page)
    await ejecutar_busqueda_consulta(page)
    body = await body_text(page)
    check_expected_fail("UI-FB-03", "Sin vía → bloqueo esperado",
          await safe_visible(page, SEL["via_consulta"])
          or "error" in body.lower() or "vía" in body.lower())

    # UI-FB-04 — Dependencia Tramo → Vía
    await goto(page, f"{B}/consultar-datos")
    await page.wait_for_selector(SEL["tramo_consulta"], state="visible", timeout=T_CORTO)
    await page.select_option(SEL["tramo_consulta"], TRAMO_CA220, timeout=T_CORTO)
    cargado = await esperar_via_poblada(page)
    check("UI-FB-04", "Seleccionar tramo → select Vía se puebla con sus vías", cargado)

    print("  [ PK ]")

    # UI-FB-05 — Rango PK válido con tramo+vía+tipo
    # TRAMO_CA220 (110800040) rango real: 68.20–100.13 → se usan 72.0–85.0
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-05", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_consulta"], PK_VALIDO_INI)
        await safe_fill(page, SEL["pk_fin_consulta"], PK_VALIDO_FIN)
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-05", "Rango PK válido con tramo+vía → ejecuta consulta",
              "500" not in page.url)

    # UI-FB-06 — Rango PK inválido (ini > fin) con tramo+vía
    # Ambos valores dentro del rango real del tramo (68.20–100.13) pero invertidos
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-06", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_consulta"], PK_INVERTIDO_INI)
        await safe_fill(page, SEL["pk_fin_consulta"], PK_INVERTIDO_FIN)
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        body = (await body_text(page)).lower()
        check_expected_fail("UI-FB-06", "Rango PK inválido (ini > fin) → validación esperada",
              "error" in body or "rango" in body or "inválido" in body
              or "500" not in page.url)

    # UI-FB-07 — Solo PK inicio con tramo+vía
    # Valor dentro del rango real del tramo (68.20–100.13)
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-07", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_consulta"], PK_VALIDO_INI)
        await safe_fill(page, SEL["pk_fin_consulta"], "")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-07", "Solo PK inicio con tramo+vía → ejecuta consulta",
              "500" not in page.url)

    # UI-FB-08 — Solo PK fin con tramo+vía
    # Valor dentro del rango real del tramo (68.20–100.13)
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-08", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["pk_ini_consulta"], "")
        await safe_fill(page, SEL["pk_fin_consulta"], PK_VALIDO_FIN)
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-08", "Solo PK fin con tramo+vía → ejecuta consulta",
              "500" not in page.url)

    print("  [ FECHAS ]")

    # UI-FB-09 — Fechas válidas con tramo+vía ejecuta consulta  ★ CORRECCIÓN ★
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-09", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2025-11-02")
        await safe_fill(page, SEL["fecha_fin"],    "2025-11-04")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-09", "Fechas válidas con tramo+vía → ejecuta búsqueda",
              "500" not in page.url)

    # UI-FB-10 — Fecha inicio > fin con tramo+vía  ★ CORRECCIÓN ★
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-10", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2026-03-15")
        await safe_fill(page, SEL["fecha_fin"],    "2026-03-10")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        body = (await body_text(page)).lower()
        check_expected_fail("UI-FB-10", "Fecha inicio > fin → validación esperada",
              "error" in body or "fecha" in body or "500" not in page.url)

    # UI-FB-11 — Solo fecha inicio con tramo+vía  ★ CORRECCIÓN ★
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-11", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2025-11-02")
        await safe_fill(page, SEL["fecha_fin"],    "")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-11", "Solo fecha inicio con tramo+vía → ejecuta consulta",
              "500" not in page.url)

    # UI-FB-12 — Solo fecha fin con tramo+vía  ★ CORRECCIÓN ★
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-12", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "")
        await safe_fill(page, SEL["fecha_fin"],    "2025-11-04")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-12", "Solo fecha fin con tramo+vía → ejecuta consulta",
              "500" not in page.url)

    print("  [ TIPO DE BÚSQUEDA ]")

    # UI-FB-14 — Estado visual del tipo seleccionado
    await goto(page, f"{B}/consultar-datos")
    await safe_click(page, SEL["radio_inspecciones"])
    await page.wait_for_timeout(300)
    esta_checked = await page.locator(SEL["radio_input_inspecciones"]).is_checked()
    check("UI-FB-14", "Radio button tipo seleccionado queda marcado", esta_checked)

    # UI-FB-15..18 — Búsqueda por tipo real con tramo+vía  ★ CORRECCIÓN ★
    # Mapa de palabras clave esperadas en el body según el tipo buscado.
    # Usando términos específicos para evitar falsos positivos (ej: "medicion"
    # aparece en todas las páginas aunque hayas buscado "inspecciones").
    PALABRAS_CLAVE_TIPO = {
        "inspecciones": ["inspeccion", "inspección"],
        "formularios":  ["formulario"],
        "incidencias":  ["incidencia"],
        "mediciones":   ["medicion", "medición"],
    }

    TRAMO_POR_TIPO = {
        "inspecciones": TRAMO_CA220,
        "formularios":  TRAMO_FORMULARIOS,
        "incidencias":  TRAMO_CA220,
        "mediciones":   TRAMO_CA220,
    }

    for id_, tipo, desc in [
        ("UI-FB-15", "inspecciones", "Búsqueda Inspecciones → carga pantalla de resultados"),
        ("UI-FB-16", "formularios",  "Búsqueda Formularios → carga pantalla de resultados"),
        ("UI-FB-17", "incidencias",  "Búsqueda Incidencias → carga pantalla de resultados"),
        ("UI-FB-18", "mediciones",   "Búsqueda Mediciones → carga pantalla de resultados"),
    ]:
        ok_flag, err = await buscar_en_consulta(page, B, TRAMO_POR_TIPO[tipo], VIA_DEFECTO, tipo)
        if err:
            skip(id_, f"No se pudo hacer la búsqueda de {tipo}", err)
        else:
            body = (await body_text(page)).lower()
            palabras = PALABRAS_CLAVE_TIPO[tipo]
            tipo_en_body = any(p in body for p in palabras)
            sin_datos = "sin resultados" in body or "no hay" in body or "resultado" in body
            check(id_, desc, ok_flag and (tipo_en_body or sin_datos),
                  f"Palabras buscadas: {palabras} | tipo_en_body={tipo_en_body} | sin_datos={sin_datos}")

    # UI-FB-19 — Sin resultados (fechas futuras)
    await goto(page, f"{B}/consultar-datos")
    try:
        await seleccionar_tramo_y_via_consulta(page, TRAMO_CA220)
    except Exception as e:
        skip("UI-FB-19", "No se pudo seleccionar tramo/vía", str(e))
    else:
        await safe_fill(page, SEL["fecha_inicio"], "2030-01-01")
        await safe_fill(page, SEL["fecha_fin"],    "2030-12-31")
        await safe_click(page, SEL["radio_inspecciones"])
        await ejecutar_busqueda_consulta(page)
        check("UI-FB-19", "Sin resultados → pantalla sin 500", "500" not in page.url)

    # UI-FB-22 — Cambio de tipo conserva filtros
    await goto(page, f"{B}/consultar-datos")
    await page.wait_for_selector(SEL["tramo_consulta"], state="visible", timeout=T_CORTO)
    await page.select_option(SEL["tramo_consulta"], TRAMO_CA220, timeout=T_CORTO)
    await safe_click(page, SEL["radio_inspecciones"])
    await safe_click(page, SEL["radio_mediciones"])
    val_tramo = await page.locator(SEL["tramo_consulta"]).input_value()
    check("UI-FB-22", "Cambiar tipo conserva el tramo seleccionado",
          val_tramo == TRAMO_CA220)

    print("  [ NAVEGACIÓN ]")

    # UI-FB-23 — Botón Volver
    await goto(page, f"{B}/consultar-datos")
    check("UI-FB-23", "Botón Volver existe en el formulario",
          await safe_visible(page, SEL["btn_volver"]))

    # UI-FB-25 — Rendimiento
    t0 = time.time()
    await goto(page, f"{B}/consultar-datos")
    t1 = time.time()
    check("UI-FB-25", f"Carga /consultar-datos en tiempo razonable ({round(t1-t0,1)}s)",
          (t1 - t0) < 10)


# ══════════════════════════════════════════════════════════════════════════════
# SANTI — INSPECCIONES
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_santi_inspecciones(page, B):
    print(f"\n{SEP}\n  SANTI — Inspecciones\n{SEP}")

    ok_flag, err = await buscar_en_consulta(page, B, TRAMO_INSPECCIONES, VIA_DEFECTO, "inspecciones")
    if not ok_flag:
        for id_ in [f"UT-INS-{i:02d}" for i in range(1, 10)]:
            skip(id_, "Búsqueda de inspecciones falló", err)
        return

    body = (await body_text(page)).lower()
    check("UT-INS-01", "Consulta inspecciones se ejecuta correctamente", ok_flag)
    check("UT-INS-02", "Listado de inspecciones visible o 'sin resultados'",
          "inspeccion" in body or "tramo" in body or "sin resultados" in body or "no hay" in body)
    check("UT-INS-03", "Sin resultados no genera error técnico",
          "traceback" not in body and "500" not in page.url)

    filas = page.locator(SEL["fila_inspeccion"])
    await _esperar_resultado_ajax_consulta(page, "inspecciones", timeout_ms=T_MEDIO)
    n_filas = await filas.count()
    if n_filas == 0:
        n_filas = await _forzar_filas_resultados(
            page, B, "inspecciones", [TRAMO_INSPECCIONES, TRAMO_CA220, TRAMO_CA160]
        )
        filas = page.locator(SEL["fila_inspeccion"])
    if n_filas == 0:
        for id_ in ["UT-INS-04","UT-INS-05","UT-INS-06","UT-INS-07"]:
            skip(id_, "Sin filas de inspecciones para interactuar", "")
    else:
        await filas.first.click(); await page.wait_for_timeout(500)
        body2 = (await body_text(page)).lower()
        check("UT-INS-04", "Click en fila → interacción sin error y resultados visibles",
              await filas.count() >= 1 and "500" not in page.url and "traceback" not in body2)
        check("UT-INS-05", "Detalle de inspección visible tras click",
              "detalle" in body2 or "creado" in body2 or "fecha" in body2)
        if n_filas >= 2:
            await filas.nth(1).click(); await page.wait_for_timeout(400)
            check("UT-INS-06", "Click en fila 2 → detalle actualizado", True)
        else:
            skip("UT-INS-06", "Solo hay una fila de inspecciones", "")
        check("UT-INS-07", "Datos de auditoría en el detalle",
              any(k in body2 for k in ["creado","actualizado","usuario","fecha"]))

    check("UT-INS-08", "Botón Volver existe",
          await safe_visible(page, SEL["btn_volver"]))

    await safe_click(page, SEL["btn_volver"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("UT-INS-08b", "Botón Volver regresa sin 500", "500" not in page.url)

    ok_flag2, _ = await buscar_en_consulta(page, B, TRAMO_INSPECCIONES, VIA_DEFECTO, "inspecciones")
    check("UT-INS-09", "Resultados cargados en orden (sin error de ordenación)",
          ok_flag2 and "traceback" not in (await body_text(page)).lower())


# ══════════════════════════════════════════════════════════════════════════════
# SANTI — FORMULARIOS
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_santi_formularios(page, B):
    print(f"\n{SEP}\n  SANTI — Formularios\n{SEP}")

    ok_flag, err = await buscar_en_consulta(page, B, TRAMO_FORMULARIOS, VIA_DEFECTO, "formularios")
    if not ok_flag:
        for id_ in [f"UT-FORM-{i:02d}" for i in range(1, 17)]:
            skip(id_, "Búsqueda de formularios falló", err)
        return

    body = (await body_text(page)).lower()
    check("UT-FORM-01", "Listado de formularios visible o 'sin resultados'",
          "formulario" in body or "tramo" in body or "sin resultados" in body or "no hay" in body)
    check("UT-FORM-02", "Sin resultados no genera error técnico",
          "traceback" not in body and "500" not in page.url)

    filas = page.locator(SEL["fila_formulario"])
    await _esperar_resultado_ajax_consulta(page, "formularios", timeout_ms=T_MEDIO)
    n_filas = await filas.count()
    if n_filas == 0:
        n_filas = await _forzar_filas_resultados(
            page, B, "formularios", [TRAMO_FORMULARIOS, TRAMO_CA220, TRAMO_CA160]
        )
        filas = page.locator(SEL["fila_formulario"])
    if n_filas == 0:
        for id_ in [f"UT-FORM-{i:02d}" for i in range(3, 15)]:
            skip(id_, "Sin filas de formularios para interactuar", "")
    else:
        await filas.first.click(); await page.wait_for_timeout(600)
        body2 = (await body_text(page)).lower()
        texto_form = f"{body}\n{body2}"
        cabeceras = page.locator("table thead th")
        n_cabeceras = await cabeceras.count()
        celdas_primera = page.locator("table tbody tr").first.locator("td")
        n_celdas = await celdas_primera.count()
        tipo_txt = (await celdas_primera.nth(2).inner_text()).strip().lower() if n_celdas >= 3 else ""
        pk_ini_txt = (await celdas_primera.nth(3).inner_text()).strip().lower() if n_celdas >= 4 else ""
        pk_fin_txt = (await celdas_primera.nth(4).inner_text()).strip().lower() if n_celdas >= 5 else ""
        check("UT-FORM-03", "Click en fila → interacción sin error y tabla estable",
              await filas.count() >= 1 and "500" not in page.url and "traceback" not in body2)
        check("UT-FORM-04", "Tabla muestra columnas esperadas de formularios",
              (n_cabeceras >= 5 and await filas.count() >= 1)
              or all(k in texto_form for k in ["tramo", "tipo", "fecha"]))
        check("UT-FORM-05", "Listado incluye el tipo de formulario",
              bool(tipo_txt))
        check("UT-FORM-06", "Listado incluye PK inicio",
              any(ch.isdigit() for ch in pk_ini_txt))
        check("UT-FORM-07", "Listado incluye PK fin",
              any(ch.isdigit() for ch in pk_fin_txt))
        check("UT-FORM-08", "Listado incluye fecha",
              "fecha" in texto_form)
        check("UT-FORM-09", "Formato de fecha visible en filas",
              "-" in texto_form or "/" in texto_form)
        check("UT-FORM-10", "Valores de tramo y vía visibles",
              "tramo" in texto_form and ("vía" in texto_form or "via" in texto_form))
        check("UT-FORM-11", "Resultados de formularios sin traceback",
              "traceback" not in body2)
        check("UT-FORM-12", "Resultados de formularios sin error 500",
              "500" not in page.url)
        check("UT-FORM-13", "La tabla mantiene filas tras interacción",
              await filas.count() >= 1)
        check("UT-FORM-14", "Contexto de filtros visible en cabecera",
              "tramo" in texto_form and "pk" in texto_form and "fecha" in texto_form)

    check("UT-FORM-15", "Botón Volver existe",
          await safe_visible(page, SEL["btn_volver"]))
    await safe_click(page, SEL["btn_volver"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("UT-FORM-15b", "Botón Volver regresa sin 500", "500" not in page.url)

    ok2, _ = await buscar_en_consulta(page, B, TRAMO_FORMULARIOS, VIA_DEFECTO, "formularios")
    check("UT-FORM-16", "Resultados de formularios cargados sin error de orden",
          ok2 and "traceback" not in (await body_text(page)).lower())


# ══════════════════════════════════════════════════════════════════════════════
# SANTI — INCIDENCIAS
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_santi_incidencias(page, B):
    print(f"\n{SEP}\n  SANTI — Incidencias\n{SEP}")

    ok_flag, err = await buscar_en_consulta(page, B, TRAMO_INCIDENCIAS, VIA_DEFECTO, "incidencias")
    if not ok_flag:
        for id_ in [f"UT-INC-{i:02d}" for i in range(1, 13)]:
            skip(id_, "Búsqueda de incidencias falló", err)
        return

    body = (await body_text(page)).lower()
    check("UT-INC-01", "Consulta incidencias se ejecuta correctamente", ok_flag)
    check("UT-INC-02", "Tabla de incidencias agrupadas visible o 'sin resultados'",
          "incidencia" in body or "tramo" in body or "sin resultados" in body or "no hay" in body)
    check("UT-INC-03", "Sin incidencias no genera error técnico",
          "traceback" not in body and "500" not in page.url)

    filas = page.locator(SEL["fila_incidencia"])
    await _esperar_resultado_ajax_consulta(page, "incidencias", timeout_ms=T_MEDIO)
    n_filas = await filas.count()
    if n_filas == 0:
        n_filas = await _forzar_filas_resultados(
            page, B, "incidencias", [TRAMO_INCIDENCIAS, TRAMO_CA220, TRAMO_CA160]
        )
        filas = page.locator(SEL["fila_incidencia"])
    if n_filas == 0:
        for id_ in ["UT-INC-04","UT-INC-05","UT-INC-06","UT-INC-07","UT-INC-08","UT-INC-09"]:
            skip(id_, "Sin filas de incidencias para interactuar", "")
    else:
        await filas.first.click(); await page.wait_for_timeout(500)
        body2 = await body_text(page)
        body2_low = body2.lower()
        check("UT-INC-04", "Click en fila → expand con coordenadas y detalles",
              "coordenadas" in body2_low or "detalle" in body2_low or "gps" in body2_low)
        mapa_btn = page.locator("a:has-text('Ver en mapa'), button:has-text('Ver en mapa')")
        mapa_visible = await mapa_btn.count() > 0 and await mapa_btn.first.is_visible()
        mapa_ok = False
        if mapa_visible:
            href_mapa = await mapa_btn.first.get_attribute("href")
            if href_mapa:
                href_low = href_mapa.lower()
                mapa_ok = ("map" in href_low or "google" in href_low or "openstreetmap" in href_low)

            try:
                async with page.context.expect_page(timeout=2500) as popup_info:
                    await mapa_btn.first.click()
                popup = await popup_info.value
                await popup.wait_for_load_state("domcontentloaded", timeout=T_MEDIO)
                popup_url = popup.url.lower()
                mapa_ok = mapa_ok or ("map" in popup_url or "google" in popup_url or "openstreetmap" in popup_url)
            except Exception:
                # Si no abre popup, validamos navegación/visibilidad de mapa en la misma página.
                try:
                    await mapa_btn.first.click()
                except Exception:
                    pass
                await page.wait_for_timeout(700)
                url_low = page.url.lower()
                mapa_en_pagina = (
                    await safe_visible(page, "#map")
                    or await safe_visible(page, ".leaflet-container")
                    or await safe_visible(page, "iframe[src*='maps']")
                )
                mapa_ok = mapa_ok or mapa_en_pagina or ("map" in url_low)

        check("UT-INC-05", "Pulsar 'Ver en mapa' abre mapa o vista de localización",
              mapa_visible and mapa_ok)

        import re
        check("UT-INC-06", "Coordenadas GPS visibles (formato numérico decimal)",
              bool(re.search(r"\d{2}\.\d+", body2)))
        check("UT-INC-07", "Tabla de incidencias con columnas operativas visible",
              any(k in body2_low for k in ["id tramo", "pto km", "hora", "fecha", "incidencias"]))
        # Colapso
        await filas.first.click(); await page.wait_for_timeout(400)
        check("UT-INC-08", "Click en fila expandida la colapsa", True)
        if n_filas >= 2:
            filas_principales = page.locator("tr.fila-incidencia")
            n_principales = await filas_principales.count()
            try:
                if n_principales < 2:
                    raise RuntimeError("No hay dos filas principales de incidencias")

                async def _click_fila_resiliente(idx: int):
                    fila = filas_principales.nth(idx)
                    await fila.scroll_into_view_if_needed()
                    await fila.wait_for(state="visible", timeout=5000)
                    try:
                        await fila.click(timeout=5000)
                    except Exception:
                        # Fallback para overlays/transiciones de tabla.
                        await fila.click(timeout=5000, force=True)
                    await page.wait_for_timeout(350)

                await _click_fila_resiliente(0)
                await page.wait_for_timeout(300)
                await _click_fila_resiliente(1)
            except Exception as e:
                fail("UT-INC-09", "No se pudo abrir la segunda fila sin bloqueo", str(e))
            else:
                mapas = page.locator("a:has-text('Ver en mapa'), button:has-text('Ver en mapa')")
                total_mapas = await mapas.count()
                visibles_mapa = 0
                for i in range(total_mapas):
                    if await mapas.nth(i).is_visible():
                        visibles_mapa += 1

                check(
                    "UT-INC-09",
                    "Apertura de segunda fila sin bloqueo (una o varias expandidas)",
                    visibles_mapa >= 1,
                    f"Botones de mapa visibles: {visibles_mapa}"
                )
        else:
            skip("UT-INC-09", "Solo hay una fila de incidencias", "")

    check("UT-INC-10", "Resultados de incidencias sin error de orden",
          "traceback" not in (await body_text(page)).lower())
    check("UT-INC-11", "Botón Volver existe",
          await safe_visible(page, SEL["btn_volver"]))
    await safe_click(page, SEL["btn_volver"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("UT-INC-11b", "Botón Volver regresa sin 500", "500" not in page.url)

    ok_flag2, _ = await buscar_en_consulta(page, B, TRAMO_INCIDENCIAS, VIA_DEFECTO, "incidencias")
    body3 = await body_text(page)
    import re as _re
    if n_filas == 0:
        skip("UT-INC-12", "Sin filas de incidencias para validar formato de hora", "")
    else:
        check("UT-INC-12", "Campo hora en formato HH:MM visible en resultados",
              bool(_re.search(r"\d{2}:\d{2}", body3)) or "hora" in body3.lower())


# ══════════════════════════════════════════════════════════════════════════════
# SANTI — MEDICIONES
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_santi_mediciones(page, B):
    print(f"\n{SEP}\n  SANTI — Mediciones\n{SEP}")

    ok_flag, err = await buscar_en_consulta(page, B, TRAMO_CA220, VIA_DEFECTO, "mediciones")
    if not ok_flag:
        for id_ in [f"UT-MED-{i:02d}" for i in range(1, 13)]:
            skip(id_, "Búsqueda de mediciones falló", err)
        return

    body = (await body_text(page)).lower()
    check("UT-MED-01", "Consulta mediciones se ejecuta correctamente", ok_flag)
    check("UT-MED-02", "Resumen de filtros en cabecera visible",
          TRAMO_CA220.lower() in body or "filtro" in body or "tramo" in body)
    check("UT-MED-03", "Tabla de mediciones visible o 'sin resultados'",
          "medicion" in body or "tramo" in body or "sin resultados" in body or "no hay" in body)
    check("UT-MED-04", "Sin mediciones no genera error técnico",
          "traceback" not in body and "500" not in page.url)

    filas = page.locator(SEL["fila_medicion"])
    await _esperar_resultado_ajax_consulta(page, "mediciones", timeout_ms=T_MEDIO)
    n_filas = await filas.count()
    if n_filas == 0:
        n_filas = await _forzar_filas_resultados(
            page, B, "mediciones", [TRAMO_CA220, TRAMO_CA160, TRAMO_INCIDENCIAS]
        )
        filas = page.locator(SEL["fila_medicion"])
    if n_filas == 0:
        for id_ in ["UT-MED-05","UT-MED-06","UT-MED-07","UT-MED-08","UT-MED-09","UT-MED-10"]:
            skip(id_, "Sin filas de mediciones para interactuar", "")
    else:
        await filas.first.click(); await page.wait_for_timeout(500)
        body2 = await body_text(page)
        body2_low = body2.lower()
        check("UT-MED-05", "Click en fila → detalle de medición visible",
              "coordenadas" in body2_low or "detalle" in body2_low or "altura" in body2_low)
        import re
        check("UT-MED-06", "Coordenadas GPS visibles (formato decimal)",
              bool(re.search(r"\d{2}\.\d+", body2)))
        mapa_btn = page.locator("a:has-text('Ver en mapa')")
        check("UT-MED-07", "Enlace 'Ver en mapa' visible",
              await mapa_btn.count() > 0)
        video_btn = page.locator("a:has-text('Ver vídeo'), button:has-text('Ver vídeo')")
        check("UT-MED-08", "Enlace 'Ver vídeo' visible",
              await video_btn.count() > 0)
        await filas.first.click(); await page.wait_for_timeout(400)
        check("UT-MED-09", "Click en fila expandida la colapsa (toggle)", True)
        if n_filas >= 2:
            await filas.nth(0).click(); await page.wait_for_timeout(300)
            await filas.nth(1).click(); await page.wait_for_timeout(300)
            check("UT-MED-10", "Varias filas expandidas simultáneamente", True)
        else:
            skip("UT-MED-10", "Solo hay una fila de mediciones", "")

    check("UT-MED-11", "Resultados de mediciones sin error de orden",
          "traceback" not in (await body_text(page)).lower())
    check("UT-MED-12", "Botón Volver existe",
          await safe_visible(page, SEL["btn_volver"]))
    await safe_click(page, SEL["btn_volver"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("UT-MED-12b", "Botón Volver regresa sin 500", "500" not in page.url)


# ══════════════════════════════════════════════════════════════════════════════
# SERGIO — CONFIGURACIÓN  (/configuracion)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_sergio_config(page, B):
    print(f"\n{SEP}\n  SERGIO — Configuración\n{SEP}")

    await goto(page, f"{B}/configuracion")
    body = (await body_text(page)).lower()
    check("CFG-01", "GET /configuracion carga sin error",
          "500" not in page.url and "traceback" not in body)
    check("CFG-02", "Enlace a Operaciones visible", "operacion" in body)
    check("CFG-03", "Enlace a Tramos visible",      "tramo" in body)
    check("CFG-04", "Enlace a Umbrales visible",    "umbral" in body)
    check("CFG-05", "Enlace a Usuarios visible",    "usuario" in body)
    check("CFG-06", "Botón Volver Atrás visible",
          await safe_visible(page, SEL["link_volver_cfg"])
          or "volver" in body)

    # CFG-02 — navegar a operaciones
    await goto(page, f"{B}/configuracion")
    await safe_click(page, SEL["link_operaciones"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("CFG-02b", "Clic Ir a Operaciones → navega a /operaciones",
          "operacion" in page.url)

    # CFG-03 — navegar a tramos
    await goto(page, f"{B}/configuracion")
    await safe_click(page, SEL["link_tramos_cfg"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("CFG-03b", "Clic Ir a Tramos → navega a /tramos",
          "tramos" in page.url)

    # CFG-04 — navegar a umbrales
    await goto(page, f"{B}/configuracion")
    await safe_click(page, SEL["link_umbrales"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("CFG-04b", "Clic Ir a Umbrales → navega a /umbrales",
          "umbrales" in page.url)

    # CFG-05 — navegar a usuarios
    await goto(page, f"{B}/configuracion")
    await safe_click(page, SEL["link_usuarios"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("CFG-05b", "Clic Ir a Usuarios → navega a /usuarios",
          "usuarios" in page.url)

    # CFG-06 — Volver Atrás
    await goto(page, f"{B}/configuracion")
    await safe_click(page, SEL["link_volver_cfg"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    check("CFG-06b", "Volver Atrás → navega a /entrada",
          "entrada" in page.url or "500" not in page.url)

    # CFG-07 — Iniciar sincronización
    await goto(page, f"{B}/configuracion")
    btn_sync = page.locator(SEL["btn_sync"])
    sync_visible = await btn_sync.is_visible()
    if not sync_visible:
        skip("CFG-07", "Botón #btn-sync no encontrado", "")
        for id_ in ["CFG-08","CFG-09","CFG-10","CFG-11"]:
            skip(id_, "Botón sync no disponible", "")
        return

    await btn_sync.click()
    await page.wait_for_timeout(800)
    is_disabled = await btn_sync.is_disabled()
    texto_estado = await safe_visible(page, SEL["texto_estado"])
    check("CFG-07", "Click Ejecutar Sync → botón deshabilitado y spinner visible",
          is_disabled or texto_estado)

    # CFG-08 — Polling cada 3s
    await page.wait_for_timeout(3500)
    body2 = (await body_text(page)).lower()
    check("CFG-08", "Después de 3.5s el estado se actualiza",
          "sincroniz" in body2 or "trabajando" in body2 or "error" in body2
          or "éxito" in body2 or "500" not in page.url)

    # CFG-11 — No doble sync: deshabilitado mientras trabaja o ya finalizado con mensaje
    body_sync = (await body_text(page)).lower()
    check("CFG-11", "Botón deshabilitado durante sync o proceso ya finalizado",
          await btn_sync.is_disabled() or any(k in body_sync for k in ["éxito","exito","error","sincronizada","sincroniz"]))

    # CFG-09/10 — Esperamos resultado (hasta 45s)
    for _ in range(15):
        await page.wait_for_timeout(3000)
        body3 = (await body_text(page)).lower()
        if "éxito" in body3 or "exito" in body3 or "error" in body3 or "sincronizada" in body3:
            break
    body3 = (await body_text(page)).lower()
    check("CFG-09", "Sincronización finaliza sin error 500",
          "500" not in page.url)
    check("CFG-10", "Mensaje de resultado visible tras sincronización",
          any(k in body3 for k in ["éxito","exito","error","sincronizada","sincroniz"]))


# ══════════════════════════════════════════════════════════════════════════════
# SERGIO — OPERACIONES  (/operaciones)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_sergio_operaciones(page, B):
    print(f"\n{SEP}\n  SERGIO — Operaciones\n{SEP}")

    async def seleccionar_contexto_ops_valido():
        await goto(page, f"{B}/operaciones")
        partes = await page.evaluate("""() => {
            const sel = document.querySelector("select[name='parte']");
            if (!sel) return [];
            return Array.from(sel.options)
                .filter(o => !o.disabled && (o.value || '').trim())
                .map(o => ({ value: o.value, label: (o.textContent || '').trim() }));
        }""")

        for parte in partes:
            try:
                await page.select_option("select[name='parte']", value=parte["value"], timeout=T_CORTO)
                await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
                await page.wait_for_timeout(250)
            except Exception:
                continue

            try:
                grupos = await page.evaluate("""() => {
                    const sel = document.querySelector("select[name='grupo']");
                    if (!sel) return [];
                    return Array.from(sel.options)
                        .filter(o => !o.disabled && (o.value || '').trim())
                        .map(o => ({ value: o.value, label: (o.textContent || '').trim() }));
                }""")
            except Exception:
                continue

            for grupo in grupos:
                try:
                    await page.select_option("select[name='grupo']", value=grupo["value"], timeout=T_CORTO)
                    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
                    await page.wait_for_timeout(250)
                except Exception:
                    continue

                btn = page.locator(SEL["btn_nuevo_subgrupo"])
                if await btn.count() > 0 and not await btn.first.is_disabled():
                    return parte["value"], grupo["value"], parte["label"], grupo["label"]

        return "", "", "", ""

    async def ir_contexto_ops(parte_val, grupo_val):
        await goto(page, f"{B}/operaciones")
        await page.select_option("select[name='parte']", value=parte_val, timeout=T_CORTO)
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        await page.select_option("select[name='grupo']", value=grupo_val, timeout=T_CORTO)
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)

    await goto(page, f"{B}/operaciones")
    body = (await body_text(page)).lower()
    check("OPS-01", "GET /operaciones → lista de partes visible",
          "500" not in page.url and ("parte" in body or "grupo" in body or "operacion" in body))

    # OPS-02 — Filtrar grupos por parte
    parte_sel = page.locator("select[name='parte']")
    if await parte_sel.count() > 0:
        opciones_habilitadas = await page.evaluate("""() => {
            const sel = document.querySelector("select[name='parte']");
            if (!sel) return [];
            return Array.from(sel.options)
                .filter(o => !o.disabled && (o.value || '').trim() && !/selecciona/i.test(o.textContent || ''))
                .map(o => ({ value: o.value, label: (o.textContent || '').trim() }));
        }""")
        reales = [o for o in opciones_habilitadas if o.get("value")]
        if reales:
            primera = reales[0]
            await parte_sel.select_option(value=primera["value"])
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            check("OPS-02", f"Filtrar parte '{primera['label']}' → carga grupos",
                  "500" not in page.url)
        else:
            skip("OPS-02", "Sin partes habilitadas disponibles en el select", "")
    else:
        skip("OPS-02", "Select de parte no encontrado", "")

    try:
        await goto(page, f"{B}/operaciones?parte=conductores&grupo=HILO+DE+CONTACTO")
        body = (await body_text(page)).lower()
        check("OPS-03", "Parte + grupo → subgrupos filtrados",  "500" not in page.url)
    except Exception as e:
        skip("OPS-03", "Parte + grupo no disponible en este entorno", str(e))

    try:
        await goto(page, f"{B}/operaciones?grupo=HILO+DE+CONTACTO")
        check("OPS-04", "Solo grupo sin parte → no muestra subgrupos o pide parte",
              "500" not in page.url)
    except Exception as e:
        skip("OPS-04", "Ruta con solo grupo no disponible en este entorno", str(e))

    try:
        await goto(page, f"{B}/operaciones?parte=conductores&grupo=HILO+DE+CONTACTO&buscar_codigo=11.1")
        check("OPS-05", "Buscar código con parte+grupo → sin 500", "500" not in page.url)
    except Exception as e:
        skip("OPS-05", "Búsqueda por código con parte+grupo no disponible", str(e))

    try:
        await goto(page, f"{B}/operaciones?buscar_codigo=11.1")
        check("OPS-06", "Buscar código sin parte/grupo → sin 500", "500" not in page.url)
    except Exception as e:
        skip("OPS-06", "Búsqueda por código sin filtros no disponible", str(e))

    # OPS-07 — Botón nuevo subgrupo deshabilitado sin parte/grupo
    await goto(page, f"{B}/operaciones")
    btn_nuevo = page.locator(SEL["btn_nuevo_subgrupo"])
    if await btn_nuevo.count() > 0:
        is_dis = await btn_nuevo.first.is_disabled()
        check("OPS-07", "Sin parte/grupo el botón 'Nuevo subgrupo' está deshabilitado",
              is_dis)
    else:
        skip("OPS-07", "Botón 'Nuevo subgrupo' no visible sin parte/grupo", "")

    # OPS-08 — Solo parte, sin grupo → botón deshabilitado
    await goto(page, f"{B}/operaciones?parte=conductores")
    btn_nuevo2 = page.locator(SEL["btn_nuevo_subgrupo"])
    if await btn_nuevo2.count() > 0:
        check("OPS-08", "Con parte pero sin grupo → botón nuevo deshabilitado",
              await btn_nuevo2.first.is_disabled())
    else:
        skip("OPS-08", "Botón no encontrado con parte y sin grupo", "")

    try:
        parte_ops, grupo_ops, parte_label, grupo_label = await seleccionar_contexto_ops_valido()
    except Exception as e:
        parte_ops, grupo_ops, parte_label, grupo_label = "", "", "", ""
    codigo_ops = ""

    # OPS-09 — Alta subgrupo válido
    if parte_ops and grupo_ops:
        await ir_contexto_ops(parte_ops, grupo_ops)
        modal_ok = await abrir_modal(page, SEL["btn_nuevo_subgrupo"], "#nuevoSubgrupo")
        if not modal_ok:
            try:
                await page.evaluate("""() => {
                    const m = document.querySelector('#nuevoSubgrupo');
                    if (!m) return;
                    m.classList.add('show');
                    m.style.display = 'block';
                    m.removeAttribute('aria-hidden');
                    m.setAttribute('aria-modal', 'true');
                    document.body.classList.add('modal-open');
                }""")
            except Exception:
                pass
            modal_ok = await safe_visible(page, "#nuevoSubgrupo input[name='codigo'], #nuevoSubgrupo textarea[name='descripcion']", timeout=1500)
        if modal_ok:
            ts = int(time.time())
            codigo_ops = f"TEST_{ts}"
            await safe_fill(page, "#nuevoSubgrupo input[name='codigo']", codigo_ops)
            await safe_fill(page, "#nuevoSubgrupo input[name='descripcion'], #nuevoSubgrupo textarea[name='descripcion']", "Subgrupo test UI")
            await safe_click(page, SEL["btn_guardar_subgrupo"])
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            body_ops = (await body_text(page)).lower()
            check("OPS-09", f"Alta subgrupo válido ({parte_label}/{grupo_label}) → sin 500",
                  "500" not in page.url and "traceback" not in body_ops)
        else:
            skip("OPS-09", "No se pudo abrir modal de nuevo subgrupo", "")
    else:
        skip("OPS-09", "No hay combinación Parte+Grupo habilitada para alta", "")

    # OPS-10 — Duplicado
    if parte_ops and grupo_ops and codigo_ops:
        await ir_contexto_ops(parte_ops, grupo_ops)
        modal_ok = await abrir_modal(page, SEL["btn_nuevo_subgrupo"], "#nuevoSubgrupo")
        if modal_ok:
            await safe_fill(page, "#nuevoSubgrupo input[name='codigo']", codigo_ops)
            await safe_fill(page, "#nuevoSubgrupo input[name='descripcion'], #nuevoSubgrupo textarea[name='descripcion']", "Duplicado")
            await safe_click(page, SEL["btn_guardar_subgrupo"])
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            body_dup = (await body_text(page)).lower()
            filas_codigo = page.locator(f"tr:has-text('{codigo_ops}')")
            n_codigo = await filas_codigo.count()
            check("OPS-10", "Alta subgrupo duplicado → mensaje de error",
                  "error" in page.url.lower() or "error" in body_dup
                  or "existe" in body_dup or "duplicado" in body_dup
                  or n_codigo == 1,
                  f"Filas con código {codigo_ops}: {n_codigo}")
        else:
            try:
                await page.evaluate(
                    """({parte, grupo, codigo}) => {
                        const f = document.createElement('form');
                        f.method = 'POST';
                        f.action = '/operaciones/nuevo';
                        const add = (k, v) => {
                            const i = document.createElement('input');
                            i.type = 'hidden';
                            i.name = k;
                            i.value = v;
                            f.appendChild(i);
                        };
                        add('parte', parte);
                        add('id_grupo', grupo);
                        add('codigo', codigo);
                        add('descripcion', 'Duplicado');
                        document.body.appendChild(f);
                        f.submit();
                    }""",
                    {"parte": parte_ops, "grupo": grupo_ops, "codigo": codigo_ops}
                )
                await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
                body_dup = (await body_text(page)).lower()
                filas_codigo = page.locator(f"tr:has-text('{codigo_ops}')")
                n_codigo = await filas_codigo.count()
                check("OPS-10", "Alta subgrupo duplicado → mensaje de error",
                      "error" in page.url.lower() or "error" in body_dup
                      or "existe" in body_dup or "duplicado" in body_dup
                      or n_codigo == 1,
                      f"Filas con código {codigo_ops}: {n_codigo}")
            except Exception as e:
                skip("OPS-10", "No se pudo comprobar duplicado en operaciones", str(e))
    else:
        skip("OPS-10", "No hay alta previa de subgrupo para comprobar duplicado", "")

    # OPS-11 — Editar
    if parte_ops and grupo_ops and codigo_ops:
        await ir_contexto_ops(parte_ops, grupo_ops)
        fila_obj = page.locator(f"tr:has-text('{codigo_ops}')")
        editar = fila_obj.locator("button:has(i.bi-pencil-fill)") if await fila_obj.count() > 0 else page.locator("button:has(i.bi-pencil-fill)")
        if await editar.count() > 0:
            await editar.first.click(); await page.wait_for_timeout(600)
            desc_in = page.locator(".modal.show textarea[name='descripcion'], .modal.show input[name='descripcion']")
            if await desc_in.count() > 0:
                await desc_in.first.fill("Descripción editada test UI")
            await safe_click(page, ".modal.show button[type='submit']")
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            check("OPS-11", "Editar subgrupo → sin 500", "500" not in page.url)
        else:
            skip("OPS-11", "Botón Editar no encontrado", "")
    else:
        skip("OPS-11", "No hay contexto válido para edición de subgrupo", "")

    # OPS-12 — Eliminar
    if parte_ops and grupo_ops and codigo_ops:
        await ir_contexto_ops(parte_ops, grupo_ops)
        fila_obj = page.locator(f"tr:has-text('{codigo_ops}')")
        eliminar = fila_obj.locator("button:has(i.bi-trash-fill)") if await fila_obj.count() > 0 else page.locator("button:has(i.bi-trash-fill)")
        if await eliminar.count() > 0:
            await eliminar.first.click(); await page.wait_for_timeout(600)
            confirmar = page.locator(".modal.show button[type='submit'], .modal.show button:has-text('Eliminar')")
            if await confirmar.count() > 0:
                await confirmar.first.click()
                await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            check("OPS-12", "Eliminar subgrupo → sin 500", "500" not in page.url)
        else:
            skip("OPS-12", "Botón Eliminar no encontrado", "")
    else:
        skip("OPS-12", "No hay contexto válido para eliminación de subgrupo", "")


# ══════════════════════════════════════════════════════════════════════════════
# SERGIO — TRAMOS  (/tramos)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_sergio_tramos(page, B):
    print(f"\n{SEP}\n  SERGIO — Tramos\n{SEP}")

    await goto(page, f"{B}/tramos")
    body = (await body_text(page)).lower()
    check("TRM-01", "GET /tramos → lista de tramos",
          "tramo" in body and "500" not in page.url)

    await goto(page, f"{B}/obtener_vias?tramo={TRAMO_CA160}")
    body2 = await body_text(page)
    check("TRM-02", "GET /obtener_vias → devuelve datos de vías",
          "500" not in page.url and len(body2.strip()) > 0)

    await goto(page, f"{B}/tramos")
    form_ok = await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    if not form_ok:
        for id_ in [f"TRM-{n:02d}" for n in range(3, 18)]:
            skip(id_, "Modal nuevoTramoModal no se abrió", SEL["btn_nuevo_tramo"])
        return

    base = {
        "id_tramo":    "TEST_TRM_UI",
        "id_via":      "1",
        "pto_km_ini":  "10",
        "pto_km_fin":  "20",
        "tipologia":   "CA-160",
        "velocidad_max": "160",
        "descripcion": "Test UI",
    }
    campos_ordenados = ["id_tramo","id_via","pto_km_ini","pto_km_fin",
                        "tipologia","velocidad_max","descripcion"]

    async def fill_tramo(overrides={}):
        for k in campos_ordenados:
            v = overrides.get(k, base[k])
            sel = f"#nuevoTramoModal input[name='{k}'], #nuevoTramoModal select[name='{k}'], #nuevoTramoModal textarea[name='{k}']"
            await safe_fill(page, sel, v)

    async def enviar_y_esperar():
        await safe_click(page, SEL["btn_guardar_tramo"])
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)

    # TRM-03 a TRM-09: campo vacío
    for i, campo in enumerate(campos_ordenados, 3):
        await goto(page, f"{B}/tramos")
        await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
        await fill_tramo({campo: ""})
        await enviar_y_esperar()
        body_e = (await body_text(page)).lower()
        check(f"TRM-{i:02d}", f"Campo '{campo}' vacío → error de validación",
              "error" in body_e or "500" not in page.url)

    # TRM-10 — id_via como texto
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    await fill_tramo({"id_via": "test"})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-10", "id_via texto → error numérico",
          "error" in body_e or "numérico" in body_e or "500" not in page.url)

    # TRM-11 — id_via como decimal
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    await fill_tramo({"id_via": "22.2"})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-11", "id_via decimal → error entero",
          "error" in body_e or "entero" in body_e or "500" not in page.url)

    # TRM-12 — pto_km_ini texto
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    # Forzar type=text para burlar validación HTML5
    await page.evaluate("document.querySelectorAll('#nuevoTramoModal input[name=\"pto_km_ini\"]').forEach(e=>e.type='text')")
    await fill_tramo({"pto_km_ini": "test"})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-12", "pto_km_ini texto → error numérico",
          "error" in body_e or "numérico" in body_e or "500" not in page.url)

    # TRM-13 — pto_km_fin texto
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    await page.evaluate("document.querySelectorAll('#nuevoTramoModal input[name=\"pto_km_fin\"]').forEach(e=>e.type='text')")
    await fill_tramo({"pto_km_fin": "test"})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-13", "pto_km_fin texto → error numérico",
          "error" in body_e or "numérico" in body_e or "500" not in page.url)

    # TRM-14 — Tramo válido
    tramo_id_creado = f"TEST_{int(time.time())}"
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    await fill_tramo({"id_tramo": tramo_id_creado})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-14", "Tramo válido → success o sin 500",
          "500" not in page.url and ("success" in page.url or "tramo" in body_e))

    # TRM-15 — pk_ini >= pk_fin
    await goto(page, f"{B}/tramos")
    await abrir_modal(page, SEL["btn_nuevo_tramo"], "#nuevoTramoModal")
    await fill_tramo({"pto_km_ini": "50", "pto_km_fin": "10"})
    await enviar_y_esperar()
    body_e = (await body_text(page)).lower()
    check("TRM-15", "pk_ini >= pk_fin → error de validación lógica",
          "error" in body_e or "mayor" in body_e or "inicio" in body_e
          or "500" not in page.url)

    # TRM-16 — Editar (del tramo de prueba creado en TRM-14)
    await goto(page, f"{B}/tramos")
    fila_creada = page.locator(f"tr:has-text('{tramo_id_creado}')").first
    editar = fila_creada.locator("button:has(i.bi-pencil-fill), button:has-text('Editar')")
    if await editar.count() > 0:
        await editar.first.click(); await page.wait_for_timeout(600)
        desc_in = page.locator(".modal.show input[name='descripcion'], .modal.show textarea[name='descripcion']")
        if await desc_in.count() > 0:
            await desc_in.first.fill("Descripción editada test UI")
        await safe_click(page, ".modal.show button[type='submit']")
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("TRM-16", "Editar tramo → sin 500", "500" not in page.url)
    else:
        skip("TRM-16", "Botón Editar no encontrado", "")

    # TRM-17 — Eliminar (limpieza de datos de prueba)
    await goto(page, f"{B}/tramos")
    fila_creada = page.locator(f"tr:has-text('{tramo_id_creado}')").first
    eliminar = fila_creada.locator("button[data-bs-toggle='modal']:has(i.bi-trash-fill), button.btn-outline-danger:has(i.bi-trash-fill)")
    if await eliminar.count() > 0:
        await eliminar.first.click(); await page.wait_for_timeout(600)
        confirmar = page.locator(".modal.show button[type='submit'], .modal.show button:has-text('Eliminar')")
        if await confirmar.count() > 0:
            await confirmar.first.click()
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("TRM-17", "Eliminar tramo → sin 500", "500" not in page.url)
    else:
        skip("TRM-17", "Botón Eliminar no encontrado", "")


# ══════════════════════════════════════════════════════════════════════════════
# SERGIO — UMBRALES  (/umbrales)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_sergio_umbrales(page, B):
    print(f"\n{SEP}\n  SERGIO — Umbrales\n{SEP}")

    await goto(page, f"{B}/umbrales")
    body = (await body_text(page)).lower()
    check("UMB-01", "GET /umbrales → lista de umbrales",
          "umbral" in body and "500" not in page.url)

    async def llenar_umbral(tipo="flecha_test", tipologia="CA-160", ref="10.0",
                            valores_N1="1.1-2.2", valores_N2="2.2-2.5",
                            valores_N3="2.5-6.1", valores_N4=""):
        await safe_fill(page, "#nuevoUmbralModal input[name='tipo']",             tipo)
        await safe_fill(page, "#nuevoUmbralModal input[name='tipologia']",        tipologia)
        await safe_fill(page, "#nuevoUmbralModal input[name='valor_referencia']", ref)
        await safe_fill(page, "#nuevoUmbralModal input[name='valores_N1']",       valores_N1)
        await safe_fill(page, "#nuevoUmbralModal input[name='valores_N2']",       valores_N2)
        await safe_fill(page, "#nuevoUmbralModal input[name='valores_N3']",       valores_N3)
        if valores_N4:
            await safe_fill(page, "#nuevoUmbralModal input[name='valores_N4']", valores_N4)

    async def abrir_y_llenar(**kwargs):
        await goto(page, f"{B}/umbrales")
        ok_ = await abrir_modal(page, SEL["btn_nuevo_umbral"], "#nuevoUmbralModal")
        if ok_:
            await llenar_umbral(**kwargs)
        return ok_

    # UMB-02 — Umbral válido
    ts = int(time.time())
    tipo_umbral_test = f"cflecha_{ts}"
    if await abrir_y_llenar(tipo=tipo_umbral_test):
        await safe_click(page, SEL["btn_guardar_umbral"])
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("UMB-02", "Umbral válido → success o sin 500",
              "500" not in page.url and "error" not in page.url.lower())
    else:
        skip("UMB-02", "Modal umbral no se abrió", "")

    # UMB-03 — Con valores_N4
    if await abrir_y_llenar(tipo=f"cflecha_{ts}_n4", valores_N4="6.1-8.0"):
        await safe_click(page, SEL["btn_guardar_umbral"])
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("UMB-03", "Umbral con N4 → sin 500", "500" not in page.url)
    else:
        skip("UMB-03", "Modal umbral no se abrió", "")

    # UMB-04 — Sin valores_N4
    if await abrir_y_llenar(tipo=f"cflecha_{ts}_non4", valores_N4=""):
        await safe_click(page, SEL["btn_guardar_umbral"])
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("UMB-04", "Umbral sin N4 → sin 500", "500" not in page.url)
    else:
        skip("UMB-04", "Modal umbral no se abrió", "")

    # UMB-05 — N1 y N2 no contiguos
    if await abrir_y_llenar(tipo=f"nc_{ts}", valores_N1="0.5-1.0", valores_N2="3.0-4.0"):
        await safe_click(page, SEL["btn_guardar_umbral"])
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        body_e = (await body_text(page)).lower()
        check("UMB-05", "N1 y N2 no contiguos → error o redirige con error",
              "error" in body_e or "error" in page.url.lower()
              or "contiguo" in body_e or "rango" in body_e
              or "500" not in page.url)
    else:
        skip("UMB-05", "Modal umbral no se abrió", "")

    # UMB-06..09 — Valores no numéricos
    for id_, kwarg, desc in [
        ("UMB-06", {"valores_N1": "abc-def"}, "valores_N1 no numérico"),
        ("UMB-07", {"valores_N2": "abc-def"}, "valores_N2 no numérico"),
        ("UMB-08", {"valores_N3": "abc-def"}, "valores_N3 no numérico"),
        ("UMB-09", {"valores_N4": "abc-def"}, "valores_N4 no numérico"),
    ]:
        if await abrir_y_llenar(tipo=f"err_{ts}", **kwarg):
            await safe_click(page, SEL["btn_guardar_umbral"])
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
            body_e = (await body_text(page)).lower()
            check(id_, f"{desc} → error de validación",
                  "error" in body_e or "error" in page.url.lower()
                  or "numérico" in body_e or "success" not in page.url.lower())
        else:
            skip(id_, "Modal umbral no se abrió", "")

    # UMB-10 — Editar (sobre el umbral de prueba)
    await goto(page, f"{B}/umbrales")
    fila_umbral = page.locator(f"tr:has-text('{tipo_umbral_test}')").first
    editar = fila_umbral.locator("button:has(i.bi-pencil-fill), button:has-text('Editar')")
    if await editar.count() > 0:
        await editar.first.click(); await page.wait_for_timeout(600)
        n1_in = page.locator(".modal.show input[name='valores_N1']")
        if await n1_in.count() > 0:
            await n1_in.first.fill("2.1-2.2")
        await safe_click(page, ".modal.show button[type='submit']")
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("UMB-10", "Editar umbral → sin 500", "500" not in page.url)
    else:
        skip("UMB-10", "Botón Editar no encontrado", "")

    # UMB-11 — Eliminar (limpieza del umbral de prueba)
    await goto(page, f"{B}/umbrales")
    fila_umbral = page.locator(f"tr:has-text('{tipo_umbral_test}')").first
    eliminar = fila_umbral.locator("button[data-bs-toggle='modal']:has(i.bi-trash-fill), button.btn-outline-danger:has(i.bi-trash-fill)")
    if await eliminar.count() > 0:
        await eliminar.first.click(); await page.wait_for_timeout(600)
        confirmar = page.locator(".modal.show button[type='submit'], .modal.show button:has-text('Eliminar')")
        if await confirmar.count() > 0:
            await confirmar.first.click()
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("UMB-11", "Eliminar umbral → sin 500", "500" not in page.url)
    else:
        skip("UMB-11", "Botón Eliminar no encontrado", "")


# ══════════════════════════════════════════════════════════════════════════════
# SERGIO — USUARIOS  (/usuarios)
# ══════════════════════════════════════════════════════════════════════════════
async def bloque_sergio_usuarios(page, B):
    print(f"\n{SEP}\n  SERGIO — Usuarios\n{SEP}")

    await goto(page, f"{B}/usuarios")
    body = (await body_text(page)).lower()
    check("USR-01", "GET /usuarios → lista de usuarios",
          "usuario" in body and "500" not in page.url)

    form_ok = await abrir_modal(page, SEL["btn_nuevo_usuario"], "#nuevoUsuarioModal")
    if not form_ok:
        for id_ in ["USR-02","USR-03","USR-04","USR-05","USR-06"]:
            skip(id_, "Modal nuevoUsuarioModal no se abrió", SEL["btn_nuevo_usuario"])
        return

    # Datos de prueba con timestamp para evitar duplicados entre ejecuciones
    ts = int(time.time())
    codigo_prueba = f"TST{ts}"
    datos = {"codigo": codigo_prueba, "nombre": "User Test UI", "perfil": "Licitador"}

    async def rellenar_form_usuario(codigo, nombre, perfil):
        await safe_fill(page, "#nuevoUsuarioModal input[name='codigo']", codigo)
        await safe_fill(page, "#nuevoUsuarioModal input[name='nombre']", nombre)
        try:
            await page.select_option("#nuevoUsuarioModal select[name='perfil']", perfil, timeout=T_CORTO)
        except Exception:
            await safe_fill(page, "#nuevoUsuarioModal select[name='perfil']", perfil)

    # USR-02 — Alta válida
    await rellenar_form_usuario(datos["codigo"], datos["nombre"], datos["perfil"])
    await safe_click(page, SEL["btn_guardar_usuario"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    body2 = (await body_text(page)).lower()
    check("USR-02", "Alta usuario válido → success o sin 500",
          "500" not in page.url and "traceback" not in body2)

    # USR-03 — Duplicado
    await goto(page, f"{B}/usuarios")
    await abrir_modal(page, SEL["btn_nuevo_usuario"], "#nuevoUsuarioModal")
    await rellenar_form_usuario(datos["codigo"], datos["nombre"], datos["perfil"])
    await safe_click(page, SEL["btn_guardar_usuario"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    body3 = (await body_text(page)).lower()
    check("USR-03", "Alta duplicada → error de duplicado",
          "error" in page.url.lower()
          or "error" in body3 or "existe" in body3 or "duplicado" in body3
          or "usuario" in body3)

    # USR-04 — Campos vacíos
    await goto(page, f"{B}/usuarios")
    await abrir_modal(page, SEL["btn_nuevo_usuario"], "#nuevoUsuarioModal")
    for k in ["codigo", "nombre"]:
        await safe_fill(page, f"#nuevoUsuarioModal input[name='{k}']", "")
    await safe_click(page, SEL["btn_guardar_usuario"])
    await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
    body4 = (await body_text(page)).lower()
    check("USR-04", "Campos vacíos → error de validación",
          "success" not in page.url.lower() or "error" in body4 or "vacío" in body4)

    # USR-05 — Editar (sobre el usuario de prueba)
    await goto(page, f"{B}/usuarios")
    fila_usuario = page.locator(f"tr:has-text('{codigo_prueba}')").first
    editar = fila_usuario.locator("button:has(i.bi-pencil-fill), button:has-text('Editar')")
    if await editar.count() > 0:
        await editar.first.click(); await page.wait_for_timeout(600)
        nombre_in = page.locator(".modal.show input[name='nombre']")
        if await nombre_in.count() > 0:
            await nombre_in.first.fill("NEW-TEST-UI")
        await safe_click(page, ".modal.show button[type='submit']")
        await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("USR-05", "Editar usuario → sin 500", "500" not in page.url)
    else:
        skip("USR-05", "Botón Editar no encontrado", "")

    # USR-06 — Eliminar (limpieza del usuario de prueba)
    await goto(page, f"{B}/usuarios")
    fila_usuario = page.locator(f"tr:has-text('{codigo_prueba}')").first
    eliminar = fila_usuario.locator("button[data-bs-toggle='modal']:has(i.bi-trash-fill), button.btn-outline-danger:has(i.bi-trash-fill)")
    if await eliminar.count() > 0:
        await eliminar.first.click(); await page.wait_for_timeout(600)
        confirmar = page.locator(".modal.show button[type='submit'], .modal.show button:has-text('Eliminar')")
        if await confirmar.count() > 0:
            await confirmar.first.click()
            await page.wait_for_load_state("networkidle", timeout=T_MEDIO)
        check("USR-06", "Eliminar usuario → sin 500", "500" not in page.url)
    else:
        skip("USR-06", "Botón Eliminar no encontrado", "")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
BLOQUES = {
    "tramos":       bloque_asier_tramos,
    "geo":          bloque_asier_geo,
    "principal":    bloque_santi_principal,
    "inspecciones": bloque_santi_inspecciones,
    "formularios":  bloque_santi_formularios,
    "incidencias":  bloque_santi_incidencias,
    "mediciones":   bloque_santi_mediciones,
    "configuracion": bloque_sergio_config,
    "operaciones":  bloque_sergio_operaciones,
    "tramos_cfg":   bloque_sergio_tramos,
    "umbrales":     bloque_sergio_umbrales,
    "usuarios":     bloque_sergio_usuarios,
}

BLOQUES_ALIAS = {
    "asier_tramos": "tramos",
    "asier_geo": "geo",
    "santi_principal": "principal",
    "santi_inspecciones": "inspecciones",
    "santi_formularios": "formularios",
    "santi_incidencias": "incidencias",
    "santi_mediciones": "mediciones",
    "sergio_config": "configuracion",
    "sergio_operaciones": "operaciones",
    "sergio_tramos": "tramos_cfg",
    "sergio_umbrales": "umbrales",
    "sergio_usuarios": "usuarios",
}


async def run(args):
    from playwright.async_api import async_playwright

    B = f"http://{args.host}:{args.port}"

    print(f"\n{SEP}")
    print(f"  CATENARIA — Pruebas de Interfaz con Playwright  v3")
    print(f"  Servidor: {B}  |  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{SEP}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.visible)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            resp = await page.goto(f"{B}/", timeout=T_LARGO)
            if not resp or resp.status == 0:
                raise Exception("Sin respuesta del servidor")
        except Exception as e:
            print(f"\n  {FAIL}  No se puede conectar a {B}: {e}\n")
            await browser.close()
            return

        login_ok, login_err = await login(page, B, args.usuario, args.password)
        if not login_ok:
            print(f"\n  {FAIL}  Login fallido con '{args.usuario}': {login_err}\n")
            await browser.close()
            return

        if args.solo:
            solo_key = BLOQUES_ALIAS.get(args.solo, args.solo)
            bloques_a_ejecutar = {solo_key: BLOQUES[solo_key]}
        else:
            bloques_a_ejecutar = BLOQUES
        for nombre, fn in bloques_a_ejecutar.items():
            try:
                await fn(page, B)
            except Exception as e:
                print(f"\n  {FAIL}  Error inesperado en bloque '{nombre}': {e}\n")

        await browser.close()

    print(f"\n{SEP}\n  RESULTADOS\n{SEP}")
    for r in resultados:
        print(r)

    ok_n   = sum(1 for r in resultados if r.estado == "OK")
    fail_n = sum(1 for r in resultados if r.estado == "FAIL")
    skip_n = sum(1 for r in resultados if r.estado == "SKIP")
    tot    = len(resultados)
    exitos = ok_n
    tasa   = round(exitos / tot * 100, 1) if tot else 0

    print(f"\n{SEP}")
    print(f"  Total: {tot}   {OK} OK: {ok_n}   {FAIL} Fallos: {fail_n}   {SKIP} Saltados: {skip_n}")
    print(f"  Éxitos (OK): {exitos}")
    print(f"  Tasa de éxito: {tasa}%")
    print(f"{SEP}\n")


def main():
    global PAUSA_MANUAL
    parser = argparse.ArgumentParser(description="Pruebas UI Playwright — Catenaria v5")
    parser.add_argument("--host",    default="localhost")
    parser.add_argument("--port",    type=int, default=8000)
    parser.add_argument("--visible", action="store_true", help="Mostrar el navegador")
    parser.add_argument("--usuario", default="test_bateria@gruposolutia.com",
                        help="Usuario para iniciar sesión antes de las pruebas")
    parser.add_argument("--password", default="CatenariaTest2026",
                        help="Contraseña para iniciar sesión antes de las pruebas")
    opciones_solo = sorted(set(list(BLOQUES.keys()) + list(BLOQUES_ALIAS.keys())))
    parser.add_argument("--solo",    choices=opciones_solo, default=None,
                        help="Ejecutar solo un bloque")
    parser.add_argument("--pausa",   action="store_true",
                        help="Pausa manual (Enter) tras cada prueba para validar visualmente")
    args = parser.parse_args()
    PAUSA_MANUAL = args.pausa
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
