
# valida_umbral.py
# -----------------------------------------------------------------------------
# Validador independiente para documentos de Umbrales.
# Devuelve SIEMPRE (ok, code):
#   - ok=True  => code=None
#   - ok=False => code es un identificador estable (string) que interfaz.py mapeará vía messages.py
# -----------------------------------------------------------------------------

from typing import Dict, List, Tuple, Optional
from decimal import Decimal, InvalidOperation
# Tipos donde la velocidad es obligatoria y tipología debe ir vacía
SPEED_TYPES = {"pendiente", "var_pendiente"}

# Tipos conocidos en los que la tipología es obligatoria y la velocidad debe ir vacía.
# Amplía esta lista si el cliente añade más tipos no-velocidad.
KNOWN_NON_SPEED_TYPES = {"altura", "descentramiento_recta", "descentramiento_curva_poste", "descentramiento_curva_vano", "flecha", "contraflecha"}

# ---------- Utilidades internas (lanzan ValueError con CÓDIGOS literales) -----
def _to_decimal(s: str) -> Decimal:
    s = (str(s) if s is not None else "").strip().replace(",", ".")
    if s == "":
        raise InvalidOperation("VACIO")
    return Decimal(s)

def _pair_to_decimals(pair: Optional[List[str]]) -> Tuple[Decimal, Decimal]:
    if not isinstance(pair, list) or len(pair) != 2:
        raise ValueError("PAIR_SHAPE")
    a = (pair[0] or "").strip()
    b = (pair[1] or "").strip()
    if a == "" or b == "":
        raise ValueError("PAIR_EMPTY")
    try:
        da = _to_decimal(a)
        db = _to_decimal(b)
    except InvalidOperation:
        raise ValueError("PAIR_NOT_NUMERIC")
    if da < 0 or db < 0:
        raise ValueError("NEGATIVE_VALUE")
    if not (da < db):
        raise ValueError("PAIR_MIN_GE_MAX")
    return da, db



def _detect_direction(n1: Tuple[Decimal, Decimal], n2: Tuple[Decimal, Decimal]) -> str:
    if n1[0] == n2[1]:
        return "DESC"
    if n1[1] == n2[0]:
        return "ASC"
    raise ValueError("DIR_UNDETERMINED")

def _check_chain(direction: str,
                 n1: Tuple[Decimal, Decimal],
                 n2: Tuple[Decimal, Decimal],
                 n3: Tuple[Decimal, Decimal],
                 n4: Optional[Tuple[Decimal, Decimal]]) -> None:
    if direction == "ASC":
        if not (n1[1] == n2[0]):
            raise ValueError("ASC_N1N2")
        if not (n2[1] == n3[0]):
            raise ValueError("ASC_N2N3")
        if n4 is not None and not (n3[1] == n4[0]):
            raise ValueError("ASC_N3N4")
    else:  # DESC
        if not (n1[0] == n2[1]):
            raise ValueError("DESC_N1N2")
        if not (n2[0] == n3[1]):
            raise ValueError("DESC_N2N3")
        if n4 is not None and not (n3[0] == n4[1]):
            raise ValueError("DESC_N3N4")

def _vref_outside_ranges(vref: Decimal,
                         ranges: List[Tuple[Decimal, Decimal]]) -> bool:
    for (mn, mx) in ranges:
        if mn <= vref <= mx:
            return False
    return True

def _validate_tipo_tipologia_velocidad(tipo: str, tipologia: Optional[str], velocidad: Optional[object]) -> None:
    """
    Reglas:
      - t in SPEED_TYPES: velocidad obligatoria (num >=0) y tipologia vacía.
      - t in KNOWN_NON_SPEED_TYPES: tipologia obligatoria y velocidad vacía.
      - otro tipo: XOR → exactamente uno de {tipologia, velocidad}; si velocidad, num >=0.
    Lanza ValueError con códigos literales para mapear en messages.py.
    """
    t = (tipo or "").strip().lower()
    tip = (tipologia or "").strip()
    vel_raw = "" if velocidad in (None, "", "None") else str(velocidad).strip()

    if t in SPEED_TYPES:
        if not vel_raw:
            raise ValueError("SPEED_REQUIRED")
        try:
            v = _to_decimal(vel_raw)
        except InvalidOperation:
            raise ValueError("SPEED_NOT_NUMERIC")
        if v < 0:
            raise ValueError("SPEED_NEGATIVE")
        if tip:
            raise ValueError("TIPOLOGIA_MUST_BE_EMPTY")
        return

    if t in KNOWN_NON_SPEED_TYPES:
        if not tip:
            raise ValueError("REQ_TIPOLOGIA")
        if vel_raw:
            raise ValueError("VELOCIDAD_MUST_BE_EMPTY")
        return

    # Tipo desconocido → XOR
    has_tip = bool(tip)
    has_vel = bool(vel_raw)
    if has_vel:
        try:
            v = _to_decimal(vel_raw)
        except InvalidOperation:
            raise ValueError("SPEED_NOT_NUMERIC")
        if v < 0:
            raise ValueError("SPEED_NEGATIVE")

    if has_tip == has_vel:  # ambos vacíos o ambos informados
        raise ValueError("XOR_TIPOLOGIA_VELOCIDAD")


def _validate_speed_by_type(tipo: str, velocidad: Optional[object]) -> None:
    t = (tipo or "").strip().lower()
    if t in ("pendiente", "var_pendiente"):
        if velocidad is None or str(velocidad).strip() == "":
            raise ValueError("SPEED_REQUIRED")
        try:
            v = _to_decimal(str(velocidad))
        except InvalidOperation:
            raise ValueError("SPEED_NOT_NUMERIC")
        if v < 0:
            raise ValueError("SPEED_NEGATIVE")
    else:
        if velocidad not in (None, "", "None"):
            raise ValueError("SPEED_NOT_APPLICABLE")

# ---------- API pública -------------------------------------------------------
def validar_umbral_doc(doc: Dict):
    """
    Valida un documento de umbral y devuelve (ok, code).
    Claves esperadas en doc:
      tipo, tipologia, velocidad, valor_referencia, valores_N1, valores_N2, valores_N3, valores_N4 (opcional)
    """
    try:
        tipo             = doc.get("tipo", "")
        tipologia        = doc.get("tipologia", "")
        velocidad        = doc.get("velocidad", None)
        valor_referencia = doc.get("valor_referencia", "")
        vN1              = doc.get("valores_N1", None)
        vN2              = doc.get("valores_N2", None)
        vN3              = doc.get("valores_N3", None)
        vN4              = doc.get("valores_N4", None)

                # 1) Tipo + Reglas de cruce tipología/velocidad (validamos esto primero)
        try:
            _validate_tipo_tipologia_velocidad(tipo, tipologia, velocidad)
        except ValueError as e:
            return False, str(e)

        # 2) valor_referencia: solo forma/numérico/≥0 (NO comprobamos todavía si cae en rangos)
        try:
            vref = _to_decimal(str(valor_referencia))
        except InvalidOperation:
            return False, "VREF_NOT_NUMERIC"
        if vref < 0:
            return False, "VREF_NEGATIVE"

        # 3) N1..N3 obligatorios; N4 opcional (validamos rangos y que min < max)
        try:
            n1 = _pair_to_decimals(vN1)
        except ValueError as e:
            return False, f"N1_{str(e)}"

        try:
            n2 = _pair_to_decimals(vN2)
        except ValueError as e:
            return False, f"N2_{str(e)}"

        try:
            n3 = _pair_to_decimals(vN3)
        except ValueError as e:
            return False, f"N3_{str(e)}"

        n4 = None
        if vN4 is not None and len(vN4) > 0:
            try:
                n4 = _pair_to_decimals(vN4)
            except ValueError as e:
                return False, f"N4_{str(e)}"

        # 4) Dirección y contigüidad entre N* (asc/desc según N1/N2)
        try:
            direction = _detect_direction(n1, n2)  # 'ASC' o 'DESC'
        except ValueError as e:
            return False, str(e)

        try:
            _check_chain(direction, n1, n2, n3, n4)
        except ValueError as e:
            return False, str(e)

        # 5) AHORA sí: verificar que valor_referencia NO cae en ningún rango N*
        ranges = [n1, n2, n3] + ([n4] if n4 else [])
        if not _vref_outside_ranges(vref, ranges):
            return False, "VREF_IN_RANGE"

        # OK
        return True, None


    except Exception:
        # Fallback genérico ante cualquier excepción no controlada
        return False, "VALIDATION_FAILED"