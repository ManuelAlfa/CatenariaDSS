"""
Servicio de Análisis Predictivo para Catenaria ADIF.

Implementa modelos predictivos para:
- Indicadores geométricos (regresión lineal)
- Índices KG1/KG2 (ARIMA)
- Incidencias (Poisson/ARIMA)
- Indicadores operativos (regresión lineal)
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sklearn.linear_model import LinearRegression
from collections import defaultdict

# Intentar importar statsmodels, si no está disponible usar implementación básica
try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    from statsmodels.genmod.families import Poisson
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False


def calcular_regresion_lineal(
    fechas: List[datetime],
    valores: List[float],
    dias_proyeccion: int = 90
) -> Dict[str, Any]:
    """
    Calcula regresión lineal simple y proyecta valores futuros.
    
    Args:
        fechas: Lista de fechas
        valores: Lista de valores medidos
        dias_proyeccion: Número de días a proyectar
    
    Returns:
        Dict con coeficientes, predicciones e intervalos de confianza
    """
    if len(fechas) < 2 or len(valores) < 2:
        return {
            "error": "Se necesitan al menos 2 puntos de datos",
            "pendiente": 0.0,
            "intercepto": valores[-1] if valores else 0.0,
            "predicciones": [],
            "r2": 0.0
        }
    
    # Convertir fechas a días desde el inicio
    dias = np.array([(f - fechas[0]).days for f in fechas]).reshape(-1, 1)
    valores_arr = np.array(valores)
    
    # Ajustar modelo
    modelo = LinearRegression()
    modelo.fit(dias, valores_arr)
    
    # Calcular R²
    r2 = modelo.score(dias, valores_arr)
    
    # Generar predicciones futuras
    ultimo_dia = dias[-1][0]
    dias_futuros = np.arange(ultimo_dia + 1, ultimo_dia + dias_proyeccion + 1).reshape(-1, 1)
    predicciones = modelo.predict(dias_futuros)
    
    # Calcular fechas futuras
    fechas_futuras = [fechas[-1] + timedelta(days=int(d)) for d in range(1, dias_proyeccion + 1)]
    
    return {
        "pendiente": float(modelo.coef_[0]),
        "intercepto": float(modelo.intercept_),
        "r2": float(r2),
        "predicciones": [
            {"fecha": f.isoformat(), "valor": float(v)}
            for f, v in zip(fechas_futuras, predicciones)
        ],
        "tendencia": "creciente" if modelo.coef_[0] > 0.001 else "decreciente" if modelo.coef_[0] < -0.001 else "estable"
    }


def calcular_dias_hasta_umbral(
    valor_actual: float,
    pendiente: float,
    umbral: float
) -> Optional[int]:
    """
    Calcula cuántos días faltan hasta superar un umbral.
    
    Args:
        valor_actual: Valor actual del indicador
        pendiente: Tasa de cambio diaria
        umbral: Valor umbral a superar
    
    Returns:
        Número de días hasta superar el umbral, o None si no se supera
    """
    if pendiente == 0:
        return None
    
    dias = (umbral - valor_actual) / pendiente
    
    if dias <= 0:
        return None  # Ya se superó o nunca se superará
    
    return int(dias)


def _normalizar_unidades_servicio(valor, campo):
    """Normaliza unidades de mediciones a metros."""
    if valor is None:
        return None
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return None

    # Ya en metros (rango esperado)
    # Altura: 5.0-6.5 m
    if campo == "altura_LAC":
        if v > 100:  # Probablemente en centímetros (p.ej. 550 cm = 5.5 m)
            return v / 100.0
        return v  # Ya está en metros

    # Descentramiento, flecha, contraflecha: 0.001-0.300 m
    # Pendiente, variacion_pendiente: valores pequeños
    if v > 10:     # Probablemente en milímetros (p.ej. 45 mm = 0.045 m)
        return v / 1000.0
    if v > 1:      # Probablemente en centímetros (p.ej. 4.5 cm = 0.045 m)
        return v / 100.0
    return v  # Ya está en metros


def proyectar_indicador_geometrico(
    datos: List[Dict[str, Any]],
    campo_valor: str,
    umbrales: Optional[Dict[str, float]] = None,
    dias_proyeccion: int = 90
) -> Dict[str, Any]:
    """
    Proyecta un indicador geométrico usando regresión lineal.
    
    Args:
        datos: Lista de dicts con 'fecha' y el campo_valor
        campo_valor: Nombre del campo a proyectar
        umbrales: Dict con umbrales N1, N2, N3, N4
        dias_proyeccion: Días a proyectar
    
    Returns:
        Resultados de la proyección
    """
    # Ordenar por fecha
    datos_ordenados = sorted(datos, key=lambda x: x.get('fecha', ''))
    
    # Extraer fechas y valores
    fechas = []
    valores = []
    
    for d in datos_ordenados:
        try:
            fecha_str = d.get('fecha', '')
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
            else:
                fecha = fecha_str
            # Normalizar unidades antes de procesar
            val_raw = d.get(campo_valor)
            if val_raw is None:
                continue
            val_normalizado = _normalizar_unidades_servicio(val_raw, campo_valor)
            if val_normalizado is None:
                continue
            valor = float(val_normalizado)
            # Filtrar ceros reales (podrían ser datos malos)
            if valor == 0.0 and len(valores) > 3:
                continue
            fechas.append(fecha)
            valores.append(valor)
        except (ValueError, TypeError):
            continue
    
    if len(fechas) < 2:
        return {
            "error": "Datos insuficientes",
            "valor_actual": valores[-1] if valores else None,
            "predicciones": []
        }
    
    # Calcular regresión
    resultado_regresion = calcular_regresion_lineal(fechas, valores, dias_proyeccion)
    
    valor_actual = valores[-1]
    pendiente = resultado_regresion["pendiente"]
    
    # Calcular días hasta cada umbral
    dias_umbrales = {}
    if umbrales:
        for nivel, umbral in umbrales.items():
            dias = calcular_dias_hasta_umbral(valor_actual, pendiente, umbral)
            is_superado = dias is None and ((pendiente > 0 and valor_actual >= umbral) or (pendiente < 0 and valor_actual <= umbral))
            # Buscar la fecha real en que el valor cruzó el umbral por primera vez
            fecha_superado = None
            superado_desde_inicio = False
            if is_superado:
                # Buscar transición: primer punto above precedido de un punto below
                prev_was_below = True
                for f, v in zip(fechas, valores):
                    is_above = (pendiente > 0 and v >= umbral) or (pendiente < 0 and v <= umbral)
                    if is_above and prev_was_below:
                        fecha_superado = f.strftime("%Y-%m-%d") if hasattr(f, "strftime") else str(f).split("T")[0]
                        break
                    prev_was_below = not is_above
                # Si no hubo transición (ya estaba superado desde el primer dato)
                if not fecha_superado:
                    superado_desde_inicio = True
                    if fechas:
                        primera = fechas[0]
                        fecha_superado = primera.strftime("%Y-%m-%d") if hasattr(primera, "strftime") else str(primera).split("T")[0]
            dias_umbrales[nivel] = {
                "dias": dias,
                "superado": is_superado,
                "superado_desde_inicio": superado_desde_inicio,
                "umbral": umbral,
                "valor_actual": round(float(valor_actual), 4),
                "fecha_superado": fecha_superado,
            }
    
    return {
        "indicador": campo_valor,
        "valor_actual": valor_actual,
        "valor_inicial": valores[0],
        "dias_datos": len(fechas),
        "tendencia": resultado_regresion["tendencia"],
        "pendiente_diaria": pendiente,
        "r2": resultado_regresion["r2"],
        "predicciones": resultado_regresion["predicciones"],
        "umbrales": dias_umbrales,
        "modelo": "regresion_lineal"
    }


def proyectar_incidencias_poisson(
    datos: List[Dict[str, Any]],
    tipo_incidencia: str,
    dias_proyeccion: int = 30
) -> Dict[str, Any]:
    """
    Proyecta recuento de incidencias. Analiza automáticamente la distribución
    de los datos para elegir el mejor método de cálculo.

    - Si los datos están bien distribuidos en el tiempo (alta densidad) → tasa diaria real
    - Si los datos están concentrados en pocas fechas (inspecciones) → suavizado inteligente
    - Si hay suficientes datos históricos → modelo Poisson GLM
    """
    # Filtrar por tipo
    incidencias_tipo = [d for d in datos if d.get('tipo') == tipo_incidencia]

    if not incidencias_tipo:
        return {
            "error": f"No hay datos para el tipo {tipo_incidencia}",
            "tipo": tipo_incidencia,
            "total_historico": 0,
            "prediccion_30d": 0
        }

    # Agrupar por día
    conteo_diario = defaultdict(int)
    fechas = []

    for inc in incidencias_tipo:
        try:
            fecha_str = inc.get('fecha', '')
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
            else:
                fecha = fecha_str.date() if hasattr(fecha_str, 'date') else fecha_str
            conteo_diario[fecha] += 1
            if fecha not in fechas:
                fechas.append(fecha)
        except (ValueError, TypeError):
            continue

    if not fechas:
        return {
            "error": "No se pudieron procesar las fechas",
            "tipo": tipo_incidencia,
            "total_historico": len(incidencias_tipo),
            "prediccion_30d": 0
        }

    fechas_ordenadas = sorted(fechas)
    dias_totales = (fechas_ordenadas[-1] - fechas_ordenadas[0]).days + 1
    total_incidencias = len(incidencias_tipo)
    num_fechas_unicas = len(fechas_ordenadas)

    # ═══ ANÁLISIS AUTÓNOMO DE LA DISTRIBUCIÓN DE DATOS ═══
    # Calcular densidad: proporción de días con datos respecto al total
    densidad = num_fechas_unicas / max(dias_totales, 1)

    # Calcular intervalo promedio entre fechas con datos
    if num_fechas_unicas > 1:
        intervalos = [(fechas_ordenadas[i] - fechas_ordenadas[i-1]).days
                      for i in range(1, num_fechas_unicas)]
        intervalo_medio = sum(intervalos) / len(intervalos)
    else:
        intervalo_medio = dias_totales

    # Determinar la ventana efectiva de observación según la densidad
    # Si hay muy pocas fechas únicas (<5), tratar como concentrado aunque sean contiguas
    if num_fechas_unicas < 5:
        # Pocas observaciones → asumir frecuencia mensual
        ventana_efectiva = num_fechas_unicas * 30
        patron = "concentrado"
    elif densidad >= 0.3:
        # Datos bien distribuidos → usar el calendario real
        ventana_efectiva = dias_totales
        patron = "distribuido"
    elif densidad >= 0.1:
        # Densidad media → suavizado suave
        # Interpolar entre días reales y un mínimo razonable
        ventana_efectiva = max(dias_totales, num_fechas_unicas * 14)
        patron = "semi_distribuido"
    else:
        # Datos muy concentrados (días de inspección) →
        # Usar la fecha única como unidad de observación
        # Asumir frecuencia de inspección mensual
        ventana_efectiva = max(dias_totales, num_fechas_unicas * 30)
        patron = "concentrado"

    if ventana_efectiva > 0:
        tasa_diaria = total_incidencias / ventana_efectiva
    else:
        tasa_diaria = float(total_incidencias)

    # Proyección
    prediccion = tasa_diaria * dias_proyeccion

    # ═══ CONFIANZA AUTÓNOMA ═══
    # Basada en: cantidad de datos, distribución temporal, y patrón
    if total_incidencias >= 30 and dias_totales >= 90 and densidad >= 0.2:
        confianza = "alta"
    elif total_incidencias >= 10 and dias_totales >= 30:
        confianza = "media"
    elif total_incidencias >= 10 and num_fechas_unicas >= 3:
        confianza = "media"
    else:
        confianza = "baja"

    # ═══ MODELO AVANZADO (Poisson GLM) ═══
    modelo_usado = "tasa_autonomica"
    if STATSMODELS_AVAILABLE and num_fechas_unicas > 7 and densidad > 0.05:
        try:
            serie = pd.Series([conteo_diario.get(f, 0) for f in fechas_ordenadas])
            X = sm.add_constant(np.arange(len(serie)))
            modelo = sm.GLM(serie, X, family=Poisson()).fit()
            X_futuro = sm.add_constant(np.arange(len(serie), len(serie) + dias_proyeccion))
            predicciones_poisson = modelo.predict(X_futuro)
            prediccion = float(sum(predicciones_poisson))
            modelo_usado = "poisson_glm"
            if confianza != "baja":
                confianza = "alta"  # GLM da más confianza
        except Exception:
            pass

    return {
        "tipo": tipo_incidencia,
        "total_historico": total_incidencias,
        "dias_historico": dias_totales,
        "fechas_unicas": num_fechas_unicas,
        "densidad": round(densidad, 3),
        "patron": patron,
        "tasa_diaria": float(tasa_diaria),
        "prediccion_30d": float(prediccion),
        "modelo": modelo_usado,
        "confianza": confianza,
    }


def proyectar_serie_temporal_arima(
    datos: List[Dict[str, Any]],
    campo_valor: str,
    dias_proyeccion: int = 90
) -> Dict[str, Any]:
    """
    Proyecta una serie temporal usando ARIMA.
    
    Args:
        datos: Lista de dicts con 'fecha' y campo_valor
        campo_valor: Campo a proyectar
        dias_proyeccion: Días a proyectar
    
    Returns:
        Proyección ARIMA
    """
    if not STATSMODELS_AVAILABLE:
        # Fallback a regresión lineal
        return proyectar_indicador_geometrico(datos, campo_valor, None, dias_proyeccion)
    
    # Ordenar por fecha
    datos_ordenados = sorted(datos, key=lambda x: x.get('fecha', ''))
    
    # Crear serie temporal
    fechas = []
    valores = []
    
    for d in datos_ordenados:
        try:
            fecha_str = d.get('fecha', '')
            if isinstance(fecha_str, str):
                fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
            else:
                fecha = fecha_str
            valor = float(d.get(campo_valor, 0))
            fechas.append(fecha)
            valores.append(valor)
        except (ValueError, TypeError):
            continue
    
    if len(fechas) < 7:
        return {
            "error": "Se necesitan al menos 7 días de datos para ARIMA",
            "modelo": "insuficiente"
        }
    
    try:
        # Crear serie pandas
        serie = pd.Series(valores, index=pd.DatetimeIndex(fechas))
        serie = serie.resample('D').mean().fillna(method='ffill')
        
        # Ajustar ARIMA(1,1,1) con estacionalidad semanal
        modelo = SARIMAX(serie, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7))
        resultado = modelo.fit(disp=False)
        
        # Predecir
        prediccion = resultado.get_forecast(steps=dias_proyeccion)
        pred_mean = prediccion.predicted_mean
        pred_ci = prediccion.conf_int()
        
        # Convertir a lista de dicts
        predicciones = []
        for fecha, valor in pred_mean.items():
            predicciones.append({
                "fecha": fecha.isoformat(),
                "valor": float(valor),
                "ci_lower": float(pred_ci.loc[fecha, 'lower ' + campo_valor]) if campo_valor in str(pred_ci.columns) else None,
                "ci_upper": float(pred_ci.loc[fecha, 'upper ' + campo_valor]) if campo_valor in str(pred_ci.columns) else None
            })
        
        return {
            "indicador": campo_valor,
            "valor_actual": valores[-1],
            "predicciones": predicciones,
            "aic": float(resultado.aic),
            "bic": float(resultado.bic),
            "modelo": "arima(1,1,1)_seasonal"
        }
        
    except Exception as e:
        # Fallback a regresión lineal
        resultado = proyectar_indicador_geometrico(datos, campo_valor, None, dias_proyeccion)
        resultado["error_arima"] = str(e)
        return resultado


def calcular_indicadores_predictivos(
    mediciones: List[Dict[str, Any]],
    incidencias: List[Dict[str, Any]],
    umbrales: Optional[Dict[str, Dict[str, float]]] = None,
    dias_proyeccion: int = 90
) -> Dict[str, Any]:
    """
    Calcula todos los indicadores predictivos.
    
    Args:
        mediciones: Lista de mediciones
        incidencias: Lista de incidencias
        umbrales: Dict de umbrales por indicador
    
    Returns:
        Dict con todas las proyecciones
    """
    resultados = {
        "fecha_calculo": datetime.now().isoformat(),
        "indicadores_geometricos": {},
        "incidencias": {},
        "alertas": []
    }
    
    # Proyectar indicadores geométricos principales
    campos_geometricos = [
        "altura_LAC",
        "descentramiento",
        "flecha",
        "contraflecha",
        "pendiente"
    ]
    
    for campo in campos_geometricos:
        if any(campo in m for m in mediciones):
            umbrales_campo = umbrales.get(campo, {}) if umbrales else None
            proyeccion = proyectar_indicador_geometrico(mediciones, campo, umbrales_campo, dias_proyeccion)
            resultados["indicadores_geometricos"][campo] = proyeccion
            
            # Generar alertas si se superará umbral en menos de 30 días
            if proyeccion.get("umbrales"):
                for nivel, info in proyeccion["umbrales"].items():
                    if info.get("dias") and info["dias"] <= 30:
                        resultados["alertas"].append({
                            "tipo": "umbral_proximo",
                            "indicador": campo,
                            "nivel": nivel,
                            "dias": info["dias"],
                            "mensaje": f"{campo} superará umbral {nivel} en {info['dias']} días"
                        })
    
    # Proyectar incidencias
    tipos_incidencias = ["KPIT1", "KPIT2", "KPIT3", "KPIT4", "KPIT5", "KPIT6"]
    
    for tipo in tipos_incidencias:
        proyeccion = proyectar_incidencias_poisson(incidencias, tipo)
        resultados["incidencias"][tipo] = proyeccion
    
    return resultados


def generar_recomendaciones(
    resultados: Dict[str, Any]
) -> List[str]:
    """
    Genera recomendaciones basadas en los resultados predictivos.
    
    Args:
        resultados: Resultados del cálculo predictivo
    
    Returns:
        Lista de recomendaciones
    """
    recomendaciones = []
    
    # Recomendaciones basadas en alertas
    for alerta in resultados.get("alertas", []):
        if alerta["tipo"] == "umbral_proximo":
            recomendaciones.append(
                f"🚨 Priorizar inspección de {alerta['indicador']} - "
                f"umbral {alerta['nivel']} en {alerta['dias']} días"
            )
    
    # Recomendaciones basadas en tendencias
    for indicador, datos in resultados.get("indicadores_geometricos", {}).items():
        tendencia = datos.get("tendencia", "estable")
        r2 = datos.get("r2", 0)
        
        if tendencia == "creciente" and r2 > 0.7:
            recomendaciones.append(
                f"📈 {indicador} muestra deterioro consistente (R²={r2:.2f}). "
                f"Programar mantenimiento preventivo."
            )
        elif tendencia == "decreciente" and r2 > 0.7:
            recomendaciones.append(
                f"📉 {indicador} muestra mejora consistente (R²={r2:.2f}). "
                f"Continuar con protocolos actuales."
            )
    
    # Recomendaciones basadas en incidencias
    for tipo, datos in resultados.get("incidencias", {}).items():
        prediccion = datos.get("prediccion_30d", 0)
        if prediccion > 5:
            recomendaciones.append(
                f"⚠️ Se esperan {prediccion:.1f} incidencias {tipo} en 30 días. "
                f"Reforzar inspecciones."
            )
    
    if not recomendaciones:
        recomendaciones.append("✅ No se detectan problemas inminentes. Mantener vigilancia habitual.")

    return recomendaciones


def _calcular_kg1_serie_temporal(
    incidencias: List[Dict[str, Any]],
    km_auscultados: float,
    ventana_dias: int = 30
) -> List[Dict[str, Any]]:
    """
    Calcula KG1 en ventanas temporales (mensual) para generar una serie
    temporal que se pueda proyectar con ARIMA.
    
    Devuelve [{fecha, kg1_valor}, ...] ordenado cronológicamente.
    """
    if not incidencias or not km_auscultados:
        return []
    
    # Extraer fechas únicas de incidencias
    fechas_inc = []
    for inc in incidencias:
        try:
            f = inc.get("fecha", "")
            if isinstance(f, str) and len(f) >= 10:
                fechas_inc.append(datetime.fromisoformat(f[:10].replace('Z', '')))
            elif isinstance(f, datetime):
                fechas_inc.append(f)
        except (ValueError, TypeError):
            pass
    
    if not fechas_inc:
        return []
    
    fecha_min = min(fechas_inc)
    fecha_max = max(fechas_inc)
    delta = (fecha_max - fecha_min).days
    
    if delta < ventana_dias:
        # Poca variabilidad temporal → usar todo como una sola ventana
        kg1_val = _calcular_kg1(incidencias, km_auscultados)
        if kg1_val is not None:
            return [{"fecha": fecha_min.isoformat(), "kg1_valor": kg1_val}]
        return []
    
    # Dividir en ventanas de ventana_dias días
    ventanas = []
    cursor = fecha_min
    while cursor <= fecha_max:
        fin_ventana = cursor + timedelta(days=ventana_dias)
        inc_ventana = [
            inc for inc in incidencias
            if _fecha_incidencia(inc) is not None and cursor <= _fecha_incidencia(inc) < fin_ventana
        ]
        if inc_ventana:
            kg1_val = _calcular_kg1(inc_ventana, km_auscultados)
            if kg1_val is not None:
                ventanas.append({
                    "fecha": cursor.isoformat(),
                    "kg1_valor": kg1_val,
                })
        cursor = fin_ventana
    
    return ventanas


def _fecha_incidencia(inc: Dict[str, Any]) -> Optional[datetime]:
    """Extrae un datetime de una incidencia de forma robusta."""
    try:
        f = inc.get("fecha", "")
        if isinstance(f, str) and len(f) >= 10:
            return datetime.fromisoformat(f[:10].replace('Z', ''))
        elif isinstance(f, datetime):
            return f
    except (ValueError, TypeError):
        pass
    return None


def _calcular_kg2(
    mediciones: List[Dict[str, Any]],
    incidencias: List[Dict[str, Any]],
    km_auscultados: float,
    dias_proyeccion: int = 90
) -> Tuple[float, float, str, List[Dict[str, Any]]]:
    """
    Calcula KG2 - Índice de Estado de Compensación de Catenaria.
    
    Basado en la especificación ADIF: evalúa estado de compensación
    (flecha, contraflecha y efecto tijera).
    
    Escala 0-10 (mayor = mejor), mismo formato que KG1.
    
    Returns:
        (valor_actual, valor_proyectado, nombre_modelo, serie_temporal)
    """
    # ── Componente geométrica: estado de flecha y contraflecha ──
    # Extraer valores de flecha y contraflecha de mediciones
    flechas = []
    contraflechas = []
    for m in mediciones:
        try:
            f = m.get("flecha")
            cf = m.get("contraflecha")
            if f is not None:
                flechas.append(float(_normalizar_unidades_servicio(f, "flecha") or 0))
            if cf is not None:
                contraflechas.append(float(_normalizar_unidades_servicio(cf, "contraflecha") or 0))
        except (ValueError, TypeError):
            pass
    
    # Puntuación base desde flecha/contraflecha (0-10)
    # Valores bajos = buen estado → puntuación alta
    if flechas:
        flecha_media = sum(flechas) / len(flechas)
        # Normalizar: 0m = 10pts, 0.150m = 5pts, 0.300m+ = 0pts
        score_flecha = max(0, 10 - (flecha_media / 0.030))
    else:
        score_flecha = 5  # Neutral si no hay datos
    
    if contraflechas:
        cf_media = sum(contraflechas) / len(contraflechas)
        score_contraflecha = max(0, 10 - (cf_media / 0.030))
    else:
        score_contraflecha = 5
    
    # ── Componente de incidencias: KPIT4 (flecha/contraflecha), KPIT5 (tijera) ──
    inc_fc = [i for i in incidencias if i.get("tipo") in ("KPIT4", "KPIT5")]
    total_fc = len(inc_fc)
    
    # Penalización por incidencias (similar a KG1 pero más suave)
    penalizacion = min(total_fc / max(km_auscultados, 1) * 20, 5)
    
    # Puntuación compuesta: 60% geométrico + 40% incidencias
    score_geo = (score_flecha * 0.5 + score_contraflecha * 0.5)
    kg2_val = round(max(0, min(10, score_geo * 0.6 + (10 - penalizacion) * 0.4)), 4)
    
    # ── Proyección ARIMA si hay suficientes datos históricos ──
    # Construir serie temporal agrupando mediciones por fecha
    serie_kg2 = []
    if mediciones:
        from collections import defaultdict
        fechas_geo = defaultdict(lambda: {"flechas": [], "contraflechas": []})
        for m in mediciones:
            try:
                f_str = m.get("fecha", "")
                if isinstance(f_str, str) and len(f_str) >= 10:
                    f_dt = datetime.fromisoformat(f_str[:10].replace('Z', '')).date()
                elif isinstance(f_str, datetime):
                    f_dt = f_str.date()
                else:
                    continue
                flecha_val = m.get("flecha")
                cf_val = m.get("contraflecha")
                if flecha_val is not None:
                    fechas_geo[f_dt]["flechas"].append(float(flecha_val))
                if cf_val is not None:
                    fechas_geo[f_dt]["contraflechas"].append(float(cf_val))
            except (ValueError, TypeError):
                continue
        
        # Agrupar por mes
        meses = defaultdict(lambda: {"flechas": [], "contraflechas": []})
        for f_dt, v in fechas_geo.items():
            mes_key = f_dt.replace(day=1)
            meses[mes_key]["flechas"].extend(v["flechas"])
            meses[mes_key]["contraflechas"].extend(v["contraflechas"])
        
        for mes_key in sorted(meses.keys()):
            v = meses[mes_key]
            f_media = sum(v["flechas"]) / len(v["flechas"]) if v["flechas"] else 0
            cf_media = sum(v["contraflechas"]) / len(v["contraflechas"]) if v["contraflechas"] else 0
            s_f = max(0, 10 - (f_media / 0.030)) if v["flechas"] else 5
            s_cf = max(0, 10 - (cf_media / 0.030)) if v["contraflechas"] else 5
            s_geo_mes = s_f * 0.5 + s_cf * 0.5
            kg2_mes = round(max(0, min(10, s_geo_mes * 0.6 + 10 * 0.4)), 4)
            serie_kg2.append({"fecha": mes_key.isoformat(), "kg2_valor": kg2_mes})
    
    modelo_kg2 = "Regresión lineal"
    kg2_proy = kg2_val  # Fallback: mismo valor
    
    if len(serie_kg2) >= 3:
        proy_kg2 = proyectar_serie_temporal_arima(serie_kg2, "kg2_valor", dias_proyeccion)
        if "predicciones" in proy_kg2 and proy_kg2["predicciones"]:
            kg2_proy = round(float(proy_kg2["predicciones"][-1]["valor"]), 4)
            modelo_kg2 = "ARIMA"
    
    return kg2_val, kg2_proy, modelo_kg2, serie_kg2


def _calcular_kg1(incidencias: List[Dict[str, Any]], km_auscultados: float) -> Optional[float]:
    """
    Calcula KG1 - Índice de Calidad de Geometría según ADIF.
    
    K1 = (M1 + 2*M2 + 3*Ma3 + 6*Mpd3 + 10*M4) / km_auscultados
    KG1 = 0.0008 * min(K1,99)² - 0.1704 * min(K1,99) + 10
    
    Donde M(nivel) suma incidencias KPIT1-4 de ese nivel de gravedad.
    """
    if not incidencias or not km_auscultados:
        return None
    
    # Agrupar incidencias por nivel
    por_nivel = defaultdict(lambda: defaultdict(int))
    for inc in incidencias:
        nivel = inc.get("nivel")
        tipo = inc.get("tipo", "")
        if nivel is not None and tipo in ("KPIT1", "KPIT2", "KPIT3", "KPIT4"):
            try:
                por_nivel[int(nivel)][tipo] += 1
            except (ValueError, TypeError):
                pass
    
    def M(nivel, tipos):
        return sum(por_nivel[nivel].get(t, 0) for t in tipos)
    
    M1 = M(1, ["KPIT1", "KPIT2", "KPIT3", "KPIT4"])
    M2 = M(2, ["KPIT1", "KPIT2", "KPIT3", "KPIT4"])
    Ma3 = M(3, ["KPIT1"])
    Mpd3 = M(3, ["KPIT2", "KPIT3", "KPIT4"])
    M4 = M(4, ["KPIT1", "KPIT2", "KPIT3", "KPIT4"])
    
    K1 = (M1 + 2*M2 + 3*Ma3 + 6*Mpd3 + 10*M4) / km_auscultados
    K1_capped = min(K1, 99)
    KG1 = 0.0008 * (K1_capped ** 2) - 0.1704 * K1_capped + 10
    
    return round(KG1, 4)


def _estimar_km_auscultados(mediciones: List[Dict[str, Any]]) -> float:
    """
    Estima kilómetros auscultados a partir de los PKs de las mediciones.
    """
    pks = []
    for m in mediciones:
        pk = m.get("pto_km")
        if pk is not None:
            try:
                pks.append(float(pk))
            except (ValueError, TypeError):
                pass
    if len(pks) < 2:
        return 1.0
    return max(pks) - min(pks) or 1.0


def _calcular_nivel_simple(valor, umbrales_campo):
    """Calcula nivel N (0-4) según umbrales del campo."""
    if valor is None or not umbrales_campo or not isinstance(umbrales_campo, dict):
        return 0
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return 0

    n4 = umbrales_campo.get("N4")
    n3 = umbrales_campo.get("N3")
    n2 = umbrales_campo.get("N2")
    n1 = umbrales_campo.get("N1")

    # Para altura: valores más bajos son peores (descending danger)
    # Para descentramiento/flecha/contraflecha: valores más altos son peores
    # Detectamos la dirección según el campo
    # Simplificamos: si N4 < N1, es descending (altura)
    if n4 is not None and n1 is not None:
        try:
            is_descending = float(n4) < float(n1)
        except (ValueError, TypeError):
            is_descending = False
    else:
        is_descending = False

    if is_descending:
        # Valores más bajos = peor (altura)
        if n4 is not None and v < float(n4): return 4
        if n3 is not None and v < float(n3): return 3
        if n2 is not None and v < float(n2): return 2
        if n1 is not None and v < float(n1): return 1
    else:
        # Valores más altos = peor (descentramiento, flecha, etc.)
        if n4 is not None and v >= float(n4): return 4
        if n3 is not None and v >= float(n3): return 3
        if n2 is not None and v >= float(n2): return 2
        if n1 is not None and v >= float(n1): return 1
    return 0


# ──────────────────────────────────────────────
# NUEVA FUNCIÓN: solo valor proyectado + fecha
# ──────────────────────────────────────────────

CAMPOS_GEOMETRICOS = [
    ("altura_LAC", "Altura media del HC", "m"),
    ("descentramiento", "Descentramiento medio del HC", "m"),
    ("flecha", "Flecha media del HC", "m"),
    ("contraflecha", "Contraflecha media", "m"),
    ("pendiente", "Pendiente", "‰/m"),
    ("variacion_pendiente", "Desviación de la pendiente", "‰/m"),
]

TIPOS_INCIDENCIAS = [
    ("KPIT1", "Incidencias por altura"),
    ("KPIT2", "Incidencias por descentramiento"),
    ("KPIT3", "Incidencias por pendiente"),
    ("KPIT4", "Incidencias por flecha/contraflecha"),
    ("KPIT5", "Incidencias por tijera"),
    ("KPIT6", "Incidencias por otras causas"),
]


def obtener_proyecciones_simplificadas(
    mediciones: List[Dict[str, Any]],
    incidencias: List[Dict[str, Any]],
    umbrales: Optional[Dict[str, Dict[str, float]]] = None,
    dias_proyeccion: int = 90
) -> Dict[str, Any]:
    """
    Calcula proyecciones y devuelve SOLO el valor proyectado con su fecha,
    organizado por categorías. Sin gráficos ni datos históricos completos.
    """
    fecha_hoy = datetime.now()
    fecha_objetivo = fecha_hoy + timedelta(days=dias_proyeccion)
    fecha_proyectada = fecha_objetivo.strftime("%Y-%m-%d")

    # Calcular cuántos días hay desde la última medición hasta la fecha objetivo.
    # La regresión genera predicciones hacia adelante *desde la última medición*,
    # no desde hoy. Si los datos son históricos (lo habitual), necesitamos ampliar
    # el horizonte de la proyección para que el último punto coincida con
    # fecha_hoy + dias_proyeccion y no con ultima_medicion + dias_proyeccion.
    ultima_fecha_medicion: Optional[datetime] = None
    for _m in mediciones:
        _f = _m.get("fecha", "")
        if _f:
            try:
                _fd = datetime.fromisoformat(str(_f).replace("Z", "+00:00")) if isinstance(_f, str) else _f
                if ultima_fecha_medicion is None or _fd > ultima_fecha_medicion:
                    ultima_fecha_medicion = _fd
            except (ValueError, TypeError):
                pass
    if ultima_fecha_medicion is not None and ultima_fecha_medicion < fecha_objetivo:
        dias_proyeccion_real = max((fecha_objetivo - ultima_fecha_medicion).days, 1)
    else:
        dias_proyeccion_real = dias_proyeccion

    resultado = {
        "fecha_calculo": fecha_hoy.isoformat(),
        "dias_proyeccion": dias_proyeccion,
        "fecha_proyectada": fecha_proyectada,
        "categorias": []
    }
    
    # ═══ CATEGORÍA 1: Indicadores Geométricos ═══
    categoria_geometricos = {
        "nombre": "Indicadores Geométricos",
        "icono": "bi bi-bezier2",
        "modelo": "Regresión lineal",
        "indicadores": []
    }

    for campo, label, unidad in CAMPOS_GEOMETRICOS:
        umbrales_campo = umbrales.get(campo, {}) if umbrales else {}
        # Usar dias_proyeccion_real para que el último punto de la serie caiga
        # exactamente en fecha_hoy + dias_proyeccion, independientemente de
        # cuándo fue la última medición.
        proy = proyectar_indicador_geometrico(mediciones, campo, umbrales_campo, dias_proyeccion_real)
        if "predicciones" in proy and proy["predicciones"]:
            ult_val = proy["predicciones"][-1]["valor"]
            val_act = proy.get("valor_actual", 0)
            nivel_act = _calcular_nivel_simple(val_act, umbrales_campo)
            nivel_proy = _calcular_nivel_simple(ult_val, umbrales_campo)
            categoria_geometricos["indicadores"].append({
                "nombre": label,
                "clave": campo,
                "valor_actual": round(float(val_act), 4),
                "nivel_actual": nivel_act,
                "valor_proyectado": round(float(ult_val), 4),
                "nivel_proyectado": nivel_proy,
                "fecha_proyectada": fecha_proyectada,  # siempre hoy + dias_proyeccion
                "unidad": unidad,
                "tendencia": proy.get("tendencia", "estable"),
                "r2": round(proy.get("r2", 0), 4),
                "modelo": "regresión lineal",
                "umbrales": proy.get("umbrales", {}),
            })
        else:
            categoria_geometricos["indicadores"].append({
                "nombre": label,
                "clave": campo,
                "valor_actual": "—",
                "nivel_actual": 0,
                "valor_proyectado": "—",
                "nivel_proyectado": 0,
                "fecha_proyectada": "—",
                "unidad": unidad,
                "tendencia": "sin datos",
                "r2": 0,
                "modelo": "regresión lineal",
            })
    
    if categoria_geometricos["indicadores"]:
        resultado["categorias"].append(categoria_geometricos)
    
    # ═══ CATEGORÍA 2: Incidencias ═══
    categoria_incidencias = {
        "nombre": "Incidencias",
        "icono": "bi bi-exclamation-triangle-fill",
        "modelo": "Poisson / ARIMA de recuentos",
        "indicadores": []
    }
    
    for tipo, label in TIPOS_INCIDENCIAS:
        # Calcular proyección directamente desde los datos
        inc_tipo = [d for d in incidencias if d.get('tipo') == tipo]
        total_hist = len(inc_tipo)
        
        if total_hist > 0:
            # Extraer fechas de forma robusta
            fechas_inc = []
            for d in inc_tipo:
                f = d.get('fecha', '')
                if f and isinstance(f, str) and len(f) >= 8:
                    try:
                        fechas_inc.append(f[:10])
                    except Exception:
                        pass
            
            fechas_unicas = len(set(fechas_inc))
            
            # Calcular tasa con ventana mínima de 30 días
            if fechas_unicas < 5:
                ventana = fechas_unicas * 30
                patron = "concentrado"
            else:
                ventana = max(len(fechas_inc), 30)
                patron = "distribuido"
            
            tasa = total_hist / max(ventana, 1)
            proy_valor = round(tasa * dias_proyeccion, 1)
            
            # Confianza
            if total_hist >= 30 and fechas_unicas >= 10:
                conf = "alta"
            elif total_hist >= 10 and fechas_unicas >= 3:
                conf = "media"
            else:
                conf = "baja"
        else:
            proy_valor = 0
            conf = "sin datos"
            patron = "—"
            ventana = 1
        
        categoria_incidencias["indicadores"].append({
            "nombre": label,
            "clave": tipo,
            "total_historico": total_hist,
            "valor_proyectado": proy_valor if total_hist > 0 else "—",
            "fecha_proyectada": fecha_proyectada if total_hist > 0 else "—",
            "unidad": "incidencias",
            "confianza": conf,
            "patron": patron,
            "tasa_diaria": round(tasa, 4) if total_hist > 0 else 0,
            "densidad": round(fechas_unicas / max(ventana, 1), 3) if total_hist > 0 else 0,
            "modelo": "Poisson",
        })
    
    if categoria_incidencias["indicadores"]:
        resultado["categorias"].append(categoria_incidencias)
    
    # ═══ CATEGORÍA 3: Indicadores Operativos ═══
    # Los operativos se derivan de los datos disponibles
    total_mediciones = len(mediciones)
    categoria_operativos = {
        "nombre": "Indicadores Operativos de Inspección",
        "icono": "bi bi-clipboard-check",
        "modelo": "Regresión lineal",
        "indicadores": [
            {
                "nombre": "Nº de inspecciones realizadas",
                "clave": "inspecciones",
                "valor_actual": total_mediciones,
                "valor_proyectado": round(total_mediciones * (1 + dias_proyeccion / 365), 0),
                "fecha_proyectada": fecha_proyectada,
                "unidad": "inspecciones",
                "tendencia": "creciente" if total_mediciones > 10 else "estable",
                "modelo": "regresión lineal",
            },
            {
                "nombre": "Nº de incidencias totales",
                "clave": "incidencias_totales",
                "valor_actual": len(incidencias),
                "valor_proyectado": round(len(incidencias) * (1 + dias_proyeccion / 365), 0) if incidencias else 0,
                "fecha_proyectada": fecha_proyectada,
                "unidad": "incidencias",
                "tendencia": "—",
                "modelo": "regresión lineal",
            },
        ]
    }
    
    resultado["categorias"].append(categoria_operativos)
    
    # ═══ CATEGORÍA 4: Índices Normativos ADIF ═══
    kg1_thresholds = {
        'valores_N4': [0, 2], 'valores_N3': [2, 3.5],
        'valores_N2': [3.5, 5.5], 'valores_N1': [5.5, 7], 'valores_N0': [7, 10],
    }
    kg2_thresholds = {
        'valores_N4': [0, 2], 'valores_N3': [2, 3.5],
        'valores_N2': [3.5, 5.5], 'valores_N1': [5.5, 7], 'valores_N0': [7, 10],
    }
    km_ausc = _estimar_km_auscultados(mediciones)
    
    # ── Serie temporal de KG1 (mensual) para proyección ARIMA ──
    kg1_serie = _calcular_kg1_serie_temporal(incidencias, km_ausc)
    proy_kg1 = {}
    if len(kg1_serie) >= 3:
        proy_kg1 = proyectar_serie_temporal_arima(kg1_serie, "kg1_valor", dias_proyeccion)
        if "predicciones" in proy_kg1 and proy_kg1["predicciones"]:
            kg1_val_proy = round(float(proy_kg1["predicciones"][-1]["valor"]), 4)
            kg1_val_act = round(float(kg1_serie[-1]["kg1_valor"]), 4)
            modelo_kg1 = "ARIMA"
        else:
            kg1_val = _calcular_kg1(incidencias, km_ausc) or 0
            kg1_val_proy = kg1_val
            kg1_val_act = kg1_val
            modelo_kg1 = "ARIMA (estimación puntual)"
    else:
        kg1_val = _calcular_kg1(incidencias, km_ausc) or 0
        kg1_val_proy = kg1_val
        kg1_val_act = kg1_val
        modelo_kg1 = "ARIMA (estimación puntual)"
    
    # ── KG2: estado de compensación (flecha, contraflecha, tijera) ──
    kg2_val_act, kg2_val_proy, modelo_kg2, kg2_serie = _calcular_kg2(
        mediciones, incidencias, km_ausc, dias_proyeccion
    )
    
    # ── KG: media de KG1 y KG2 ──
    kg_val_act = round((kg1_val_act + kg2_val_act) / 2, 4)
    kg_val_proy = round((kg1_val_proy + kg2_val_proy) / 2, 4)
    
    def _nivel_kg(valor, thresholds):
        for n in [4, 3, 2, 1]:
            r = thresholds[f'valores_N{n}']
            if r[0] <= valor <= r[1]:
                return n
        return 0
    
    kg1_nivel_act = _nivel_kg(kg1_val_act, kg1_thresholds)
    kg1_nivel_proy = _nivel_kg(kg1_val_proy, kg1_thresholds)
    kg2_nivel_act = _nivel_kg(kg2_val_act, kg2_thresholds)
    kg2_nivel_proy = _nivel_kg(kg2_val_proy, kg2_thresholds)
    kg_nivel_act = _nivel_kg(kg_val_act, kg1_thresholds)
    kg_nivel_proy = _nivel_kg(kg_val_proy, kg1_thresholds)
    
    categoria_adif = {
        "nombre": "Índices Normativos ADIF",
        "icono": "bi bi-file-earmark-text",
        "modelo": "ARIMA / regresión lineal",
        "indicadores": [],
    }
    
    tend_kg1 = "creciente" if kg1_val_proy > kg1_val_act * 1.01 else "decreciente" if kg1_val_proy < kg1_val_act * 0.99 else "estable"
    tend_kg2 = "creciente" if kg2_val_proy > kg2_val_act * 1.01 else "decreciente" if kg2_val_proy < kg2_val_act * 0.99 else "estable"
    tend_kg = "creciente" if kg_val_proy > kg_val_act * 1.01 else "decreciente" if kg_val_proy < kg_val_act * 0.99 else "estable"
    
    categoria_adif["indicadores"].append({
        "nombre": "KG1 – Índice de Calidad de Geometría",
        "clave": "Ind_KG1",
        "valor_actual": kg1_val_act,
        "valor_proyectado": kg1_val_proy,
        "nivel_actual": kg1_nivel_act,
        "nivel_proyectado": kg1_nivel_proy,
        "fecha_proyectada": fecha_proyectada,
        "unidad": "puntos",
        "tendencia": tend_kg1,
        "r2": round(proy_kg1.get("r2", 0), 4) if isinstance(proy_kg1, dict) else 0,
        "modelo": modelo_kg1,
    })
    
    categoria_adif["indicadores"].append({
        "nombre": "KG2 – Índice de Estado de Compensación",
        "clave": "Ind_KG2",
        "valor_actual": kg2_val_act,
        "valor_proyectado": kg2_val_proy,
        "nivel_actual": kg2_nivel_act,
        "nivel_proyectado": kg2_nivel_proy,
        "fecha_proyectada": fecha_proyectada,
        "unidad": "puntos",
        "tendencia": tend_kg2,
        "modelo": modelo_kg2,
    })
    
    categoria_adif["indicadores"].append({
        "nombre": "KG – Índice Global de Calidad de Catenaria",
        "clave": "Ind_KG",
        "valor_actual": kg_val_act,
        "valor_proyectado": kg_val_proy,
        "nivel_actual": kg_nivel_act,
        "nivel_proyectado": kg_nivel_proy,
        "fecha_proyectada": fecha_proyectada,
        "unidad": "puntos",
        "tendencia": tend_kg,
        "modelo": "ARIMA (combinación KG1+KG2)",
    })
    
    if categoria_adif["indicadores"]:
        resultado["categorias"].append(categoria_adif)
    
    return resultado
