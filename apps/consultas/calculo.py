"""Cálculo de indicadores y generación de gráficos para consultas.

Funciones extraídas del antiguo `interfaz.py` (servidor HTTP legacy).
Sirven para:
  - Confirmar consultas grandes (umbral de aviso).
  - Obtener datos brutos de Couchbase para un tramo / vía / rango.
  - Calcular KPIs geométricos a partir de mediciones.
  - Pintar dashboards Plotly (gauges + incidencias) como HTML.
"""

import textwrap
from html import escape as html_escape

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

from apps.core.messages import GENERIC


LIMITE_AVISO_CONSULTA_GRANDE = 1000


def page_confirmacion_consulta_grande(
    limite,
    tramo,
    via,
    tipo_busqueda,
    fecha_inicio,
    fecha_fin,
    pto_km_ini_raw,
    pto_km_fin_raw,
):
    """Muestra una confirmación antes de lanzar consultas de gran volumen."""
    hidden_fields = [
        ("tramo", tramo or ""),
        ("via", via or ""),
        ("tipo_busqueda", tipo_busqueda or "mediciones"),
        ("fecha_inicio", fecha_inicio or ""),
        ("fecha_fin", fecha_fin or ""),
        ("pto_km_ini", pto_km_ini_raw or ""),
        ("pto_km_fin", pto_km_fin_raw or ""),
        ("confirmar_consulta_grande", "1"),
    ]

    hidden_html = "\n".join(
        f'<input type="hidden" name="{html_escape(k)}" value="{html_escape(str(v))}">'
        for k, v in hidden_fields
    )

    return f"""
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Confirmar consulta grande</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-8 col-lg-6">
                <div class="card shadow-sm border-0">
                    <div class="card-body p-4">
                        <h1 class="h4 mb-3">Consulta de gran volumen</h1>
                        <div class="alert alert-warning mb-4" role="alert">
                            Esta consulta puede devolver <strong>mas de {int(limite)}</strong> resultados.
                            Puede tardar bastante en ejecutarse.
                        </div>
                        <form method="POST" action="/consultar-datos">
                            {hidden_html}
                            <div class="d-flex gap-2 justify-content-end">
                                <a class="btn btn-outline-secondary" href="/consultar-datos">Cancelar</a>
                                <button type="submit" class="btn btn-primary">Continuar de todos modos</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

def obtener_umbrales(cluster, clausula_FROM):
    """ Esta funcion permite obtener los umbrales de la entidad Maestro_Umbrales por algunos criterios de selección"""

    query = "SELECT tipo, tipologia,velocidad,valor_referencia, valores_N1, valores_N2, valores_N3, valores_N4 " + \
        clausula_FROM + "`Maestro_Umbrales`"
    try:
        result = cluster.query(query)
        return [row for row in result]
    except Exception as e:
        # print(f"Error obteniendo umbrales: {e}")
        return {}

def obtener_todos_los_datos(cluster, clausula_FROM, id_tramo=None, fecha_inicio=None, fecha_fin=None,pto_km_ini=None, pto_km_fin=None, id_via = None):
    """ Esta funcion permite obtener todos los datos de incidencias segun criterios de seleccion"""

    condiciones_comunes = []
    if id_tramo:
        if isinstance(id_tramo, list):
            ids = ", ".join(f"'{t}'" for t in id_tramo)
            condiciones_comunes.append(f"id_tramo IN [{ids}]")
        else:
            condiciones_comunes.append(f"id_tramo = '{id_tramo}'")

    if id_via and id_via != "Selecciona una vía" and not isinstance(id_tramo, list):
        condiciones_comunes.append(f"id_via = '{id_via}'")

    fecha_inicio = fecha_inicio.replace("-", "") if fecha_inicio else None
    fecha_fin = fecha_fin.replace("-", "") if fecha_fin else None

    if fecha_inicio and fecha_fin:
        condiciones_comunes.append(f"fecha >= '{fecha_inicio}' AND fecha <= '{fecha_fin}'")
    elif fecha_inicio:
        condiciones_comunes.append(f"fecha >= '{fecha_inicio}'")
    elif fecha_fin:
        condiciones_comunes.append(f"fecha <= '{fecha_fin}'")

    condiciones_km = []

    if pto_km_ini is not None and pto_km_fin is not None:
        condiciones_km.append(f"pto_km >= {pto_km_ini} AND pto_km <= {pto_km_fin}")
    
    filtro_incidencias = "WHERE " + " AND ".join(condiciones_comunes + condiciones_km) if (condiciones_comunes or condiciones_km) else ""
    filtro_mediciones = filtro_incidencias
    filtro_km_tramos = "WHERE " + " AND ".join(condiciones_comunes) if condiciones_comunes else ""
    print("filtro_mediciones=", filtro_mediciones)
    print("filtro_km_tramos=", filtro_km_tramos)
    queries = {
        'incidencias': f"""
            SELECT 
                nivel,
                tipo,
                SUM(valor_medido) as suma_valor,
                COUNT(*) as conteo
            {clausula_FROM}`Incidencias`
            {filtro_incidencias}
            GROUP BY nivel, tipo;
        """,
        'mediciones': f"""
            SELECT 
                -- Medidas generales
                AVG(TO_NUMBER(altura_LAC)) as altura_media,
                AVG(TO_NUMBER(flecha)) as flecha_media,
                AVG(TO_NUMBER(contraflecha)) as contraflecha_media,
                MAX(TO_NUMBER(flecha)) as flecha_max,
                MIN(TO_NUMBER(altura_LAC)) as altura_min,
                MAX(TO_NUMBER(altura_LAC)) as altura_max,
                MAX(ABS(TO_NUMBER(contraflecha))) as contraflecha_max,
                
                -- Descentramiento para tramos rectos (radio_curvatura = 0)
                AVG(CASE WHEN TO_NUMBER(radio_curvatura) = 0 THEN TO_NUMBER(descentramiento) ELSE NULL END) as descentramiento_recta_media,
                MAX(CASE WHEN TO_NUMBER(radio_curvatura) = 0 THEN ABS(TO_NUMBER(descentramiento)) ELSE NULL END) as descentramiento_recta_max,
                COUNT(CASE WHEN TO_NUMBER(radio_curvatura) = 0 THEN 1 END) as muestras_rectas,
                
                -- Descentramiento curvo en poste (radio_curvatura ≠ 0 Y poste tiene contenido)
                AVG(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND poste IS NOT NULL AND poste != '' 
                    THEN TO_NUMBER(descentramiento) ELSE NULL END) as descentramiento_curva_poste_media,
                MAX(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND poste IS NOT NULL AND poste != '' 
                    THEN ABS(TO_NUMBER(descentramiento)) ELSE NULL END) as descentramiento_curva_poste_max,
                COUNT(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND poste IS NOT NULL AND poste != '' 
                    THEN 1 END) as muestras_curvas_poste,
                
                -- Descentramiento curvo en vano (radio_curvatura ≠ 0 Y poste vacío)
                AVG(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND (poste IS NULL OR poste = '') 
                    THEN TO_NUMBER(descentramiento) ELSE NULL END) as descentramiento_curva_vano_media,
                MAX(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND (poste IS NULL OR poste = '') 
                    THEN ABS(TO_NUMBER(descentramiento)) ELSE NULL END) as descentramiento_curva_vano_max,
                COUNT(CASE WHEN TO_NUMBER(radio_curvatura) != 0 AND (poste IS NULL OR poste = '') 
                    THEN 1 END) as muestras_curvas_vano,

                ARRAY_AGG(TO_NUMBER(flecha)) as flechas_individuales,
                ARRAY_AGG(TO_NUMBER(altura_LAC)) as alturas,
                ARRAY_AGG(TO_NUMBER(contraflecha)) as contraflecha_individuales,
                ARRAY_AGG(TO_NUMBER(pendiente)) as pendientes_individuales,
                ARRAY_AGG(TO_NUMBER(variacion_pendiente)) as variacion_pendiente_individuales

            {clausula_FROM}`Medicion_Individual`
            {filtro_mediciones}
        """,
        'km': f"""
        SELECT
            SUM(
                LEAST(pto_km_fin, {pto_km_fin}) - GREATEST(pto_km_ini, {pto_km_ini})
            ) AS km_auscultados
        {clausula_FROM}`Maestro_Tramos`
        {filtro_km_tramos}
          AND pto_km_fin > {pto_km_ini}
          AND pto_km_ini < {pto_km_fin};
    """,
        'tramos': f"""
           SELECT DISTINCT id_tramo, id_via, pto_km_ini, pto_km_fin, descripcion, tipologia, velocidad_max
           {clausula_FROM}`Maestro_Tramos` 
            WHERE id_tramo IS NOT MISSING AND id_tramo IS NOT NULL;
        """,
    }

    resultados = {}
    for key, query in queries.items():
        try:
            result = cluster.query(query)
            rows = [row for row in result.rows()]  
            if key in ['incidencias', 'mediciones'] and not result:
                raise ValueError(f"No hay datos disponibles en '{key}' para los filtros seleccionados (fechas u otros).")
            
            if key == 'incidencias':
                datos = {}
                conteo_incidencias = {}
                for row in rows:
                    nivel = row['nivel']
                    tipo = row['tipo']
                    valor = row['suma_valor'] or 0
                    conteo = row['conteo'] or 0

                    if nivel not in datos:
                        datos[nivel] = {}
                    datos[nivel][tipo] = valor

                    if tipo not in conteo_incidencias:
                        conteo_incidencias[tipo] = 0
                    conteo_incidencias[tipo] += conteo
                
                conteo_incidencias["KGIT1"] = sum(conteo_incidencias.values())
                resultados[key] = datos
                resultados['conteo_inc'] = conteo_incidencias

            elif key == 'mediciones':
                resultados[key] = rows[0] if rows else {}

                mediciones = resultados[key]
                if not mediciones:
                    raise ValueError("No hay datos disponibles para los filtros seleccionados (fechas u otros).")

                vacio = True
                for valor in mediciones.values():
                    if valor is None:
                        continue
                    if isinstance(valor, (list, tuple, set)) and len(valor) == 0:
                        continue
                    if isinstance(valor, (int, float)) and valor == 0:
                        continue
                    vacio = False
                    break

                if vacio:
                    raise ValueError("No hay datos disponibles para los filtros seleccionados (fechas u otros).")

            elif key == 'km':
                km = rows[0].get('km_auscultados') if rows else 0
                resultados[key] = km if km is not None else 0
            elif key == 'tramos':
                resultados[key] = rows
        except Exception as e:
            resultados[key] = {} if key == 'mediciones' else 0 if key == 'km' else []
            print(f"{GENERIC['unexpected']}: {e}")

    resultados['umbrales'] = obtener_umbrales(cluster, clausula_FROM)


    total_incidencias = resultados.get('conteo_inc', {}).get('KGIT1', 0)
    km_auscultados = resultados.get('km', 0)

    if km_auscultados > 0:
        resultados['conteo_inc']['KGIT2'] = round(total_incidencias / km_auscultados, 2)

    # print(json.dumps(resultados, indent=4, ensure_ascii=False))
    return resultados

def obtener_tipologia(tramos, id_tramo, umbrales, tipo, velocidad_tramo=None, pto_km_ini=None, pto_km_fin=None, id_via=None):
    
    if pto_km_ini is not None and pto_km_fin is not None:
        try:
            km_ini = float(pto_km_ini)
            km_fin = float(pto_km_fin)
        except (TypeError, ValueError):
            raise ValueError(f"Rango PK inválido: {pto_km_ini}-{pto_km_fin}")

        if km_ini > km_fin:
            raise ValueError(f"Rango PK inválido: {pto_km_ini}-{pto_km_fin}")

        partes_solapadas = []
        for tramo in tramos:
            if tramo.get('id_tramo') != id_tramo:
                continue
            if id_via is not None and tramo.get('id_via') != id_via:
                continue

            try:
                tramo_ini = float(tramo.get('pto_km_ini'))
                tramo_fin = float(tramo.get('pto_km_fin'))
            except (TypeError, ValueError):
                continue

            if tramo_fin >= km_ini and tramo_ini <= km_fin:
                partes_solapadas.append(tramo)

        if not partes_solapadas:
            raise ValueError(f"No se encontró el tramo con los puntos km {pto_km_ini}-{pto_km_fin}")

        if tipo in ['pendiente', 'var_pendiente']:
            vel_set = {
                p.get('velocidad_max') for p in partes_solapadas
                if p.get('velocidad_max') is not None
            }
            vel_ref = velocidad_tramo if velocidad_tramo is not None else (next(iter(vel_set)) if len(vel_set) == 1 else None)
            if vel_ref is None:
                raise ValueError(
                    f"El tramo {id_tramo} no tiene velocidad_max definida, "
                    f"necesaria para calcular umbrales de tipo '{tipo}'"
                )
            umbral = obtener_umbral(umbrales, tipo, None, vel_ref)
            if umbral is None:
                raise ValueError(
                    f"No se encontró umbral de tipo '{tipo}' para velocidad {vel_ref} km/h"
                )
            tipologia_ref = partes_solapadas[0].get('tipologia')
            if not tipologia_ref:
                raise ValueError("La parte del tramo no tiene tipología definida.")
            return tipologia_ref

        tipologias_validas = []
        for parte in partes_solapadas:
            tipologia = parte.get('tipologia')
            if not tipologia:
                continue
            umbral = obtener_umbral(umbrales, tipo, tipologia, velocidad_tramo)
            if umbral is not None:
                tipologias_validas.append(tipologia)

        if not tipologias_validas:
            raise ValueError(f"No se encontraron umbrales válidos para el tramo {id_tramo} y tipo {tipo}")

        tipologias_unicas = list(set(tipologias_validas))
        if len(tipologias_unicas) == 1:
            return tipologias_unicas[0]

        raise ValueError(
            f"Las distintas partes del tramo {id_tramo}" +
            (f" en la vía {id_via}" if id_via else "") +
            " tienen tipologías diferentes con umbrales válidos. No se puede determinar una única."
        )

    partes_tramo = [
        t for t in tramos 
        if t['id_tramo'] == id_tramo and (id_via is None or t.get('id_via') == id_via)
    ]

    # print(f"Partes del tramo encontradas (id_tramo={id_tramo}, id_via={id_via}):")

    # for p in partes_tramo:
    #     print(f" - Pto_km_ini: {p.get('Pto_km_ini')}, Pto_km_fin: {p.get('Pto_km_fin')}, tipologia: {p.get('tipologia')}")

    if not partes_tramo:
        raise ValueError(f"No se encontraron partes del tramo con id_tramo={id_tramo}" +
                         (f" e id_via={id_via}" if id_via else ""))

   
    if tipo in ['pendiente', 'var_pendiente']:
        if velocidad_tramo is None:
            raise ValueError(
                f"El tramo {id_tramo} no tiene velocidad_max definida, "
                f"necesaria para calcular umbrales de tipo '{tipo}'"
            )
        umbral = obtener_umbral(umbrales, tipo, None, velocidad_tramo)
        if umbral is None:
            raise ValueError(
                f"No se encontró umbral de tipo '{tipo}' para velocidad {velocidad_tramo} km/h"
            )
        return partes_tramo[0].get('tipologia') or 'N/A'
   
    tipologias_validas = []

    for parte in partes_tramo:
        tipologia = parte.get('tipologia')
        if not tipologia:
            # print("Parte sin tipología definida.")
            continue

        umbral = obtener_umbral(umbrales, tipo, tipologia, velocidad_tramo)
        if umbral is None:
            # print(f"Tipología '{tipologia}' no tiene umbral en '{tipo}'.")
            continue

        tipologias_validas.append(tipologia)

    if not tipologias_validas:
        raise ValueError(f"No se encontraron umbrales válidos para el tramo {id_tramo} y tipo {tipo}")

    tipologias_unicas = list(set(tipologias_validas))

    if len(tipologias_unicas) == 1:
        return tipologias_unicas[0]
    else:
        raise ValueError(f"Las distintas partes del tramo {id_tramo}" +
                         (f" en la vía {id_via}" if id_via else "") +
                         " tienen tipologías diferentes con umbrales válidos. No se puede determinar una única.")

def obtener_velocidad(tramos, id_tramo, pto_km_ini, pto_km_fin):
    if pto_km_ini is None or pto_km_fin is None:
        for tramo in tramos:
            if tramo.get('id_tramo') == id_tramo:
                return tramo.get('velocidad_max')
        return None

    try:
        km_ini = float(pto_km_ini)
        km_fin = float(pto_km_fin)
    except (TypeError, ValueError):
        return None

    velocidades = set()
    for tramo in tramos:
        if tramo.get('id_tramo') != id_tramo:
            continue
        try:
            tramo_ini = float(tramo.get('pto_km_ini'))
            tramo_fin = float(tramo.get('pto_km_fin'))
        except (TypeError, ValueError):
            continue

        if tramo_fin >= km_ini and tramo_ini <= km_fin:
            vel = tramo.get('velocidad_max')
            if vel is not None:
                velocidades.add(vel)

    if len(velocidades) == 1:
        return next(iter(velocidades))
    if len(velocidades) > 1:
        return sorted(velocidades)[0]
    return None

def obtener_umbral(umbrales, tipo, tipologia, velocidad_tramo=None):
    """ Esta funcion permite obtener los umbrales segun algunos criterios de selección"""
    tipo_norm = str(tipo).strip().lower() if tipo is not None else ""
    tipologia_norm = str(tipologia).strip().upper() if tipologia is not None else ""

    if tipo_norm in ['pendiente', 'var_pendiente'] and velocidad_tramo is not None:
        try:
            velocidad_tramo = int(velocidad_tramo)
        except ValueError:
            # print(f"No se puede convertir la velocidad del tramo: {velocidad_tramo}")
            return None

        for umbral in umbrales:
            umbral_tipo = str(umbral.get("tipo", "")).strip().lower()
            if umbral_tipo == tipo_norm and umbral.get("velocidad") == velocidad_tramo:
                return umbral
    else:
        for umbral in umbrales:
            umbral_tipo = str(umbral.get("tipo", "")).strip().lower()
            umbral_tipologia = str(umbral.get("tipologia", "")).strip().upper()
            if umbral_tipo == tipo_norm and umbral_tipologia == tipologia_norm:
                return umbral
    # print("No se encontró umbral")
    return None

def calcular_indicadores(datos, kpigs_seleccionados, id_tramo, pto_km_ini, pto_km_fin, id_via):
    """ Esta funcion permite calcular los indicadores segun algunos criterios de selección"""

    resultados = []
    incidencias = datos.get('incidencias', {})
    mediciones = datos.get('mediciones', {})
    umbrales = datos.get('umbrales', {})
    km_auscultados = datos.get('km', 0)
    tramos = datos.get('tramos',{})

    velocidad_tramo = obtener_velocidad(tramos,id_tramo,pto_km_ini,pto_km_fin)

    def calcular_M(nivel, tipos_kpit, factor_vpt=0.25):
        nivel_data = incidencias.get(nivel, {})
        total = 0
        for kpit in tipos_kpit:
            if kpit == 'KPIT4':
                total += factor_vpt * nivel_data.get(kpit, 0)
            else:
                total += nivel_data.get(kpit, 0)

        return total 

    if any(k in kpigs_seleccionados for k in ['Ind_K1', 'Ind_KG1']):

        M1 = calcular_M(1, ['KPIT1', 'KPIT2', 'KPIT3', 'KPIT4'])
        M2 = calcular_M(2, ['KPIT1', 'KPIT2', 'KPIT3', 'KPIT4'])
        Ma3 = calcular_M(3, ['KPIT1'])
        Mpd3 = calcular_M(3, ['KPIT2', 'KPIT3', 'KPIT4'])  
        M4 = calcular_M(4, ['KPIT1', 'KPIT2', 'KPIT3', 'KPIT4'])

        K1 = (M1 + 2*M2 + 3*Ma3 + 6*Mpd3 + 10*M4) / km_auscultados if km_auscultados else 0
        KG1 = 0.0008 * (min(K1, 99) ** 2) - 0.1704 * min(K1, 99) + 10
        
        if "Ind_KG1" in kpigs_seleccionados:
            resultados.append(['Ind_KG1', round(KG1, 2), id_tramo, 'S'])

    
    if "Ind_KPIG1" in kpigs_seleccionados:
        altura_media = round(mediciones.get('altura_media') or 0, 3)
        valor_maximo = round(mediciones.get('altura_max')or 0, 3)


        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"altura",velocidad_tramo,pto_km_ini,pto_km_fin)
        umbral_KPIG1 = obtener_umbral(umbrales, "altura", tipologia_tramo)

        resultados.append(['Ind_KPIG1', altura_media, id_tramo, 'S',umbral_KPIG1,valor_maximo])

    if "Ind_KPIG2" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"descentramiento_recta",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_recto = obtener_umbral(umbrales, "descentramiento_recta", tipologia_tramo)
        umbral_curva_poste = obtener_umbral(umbrales, "descentramiento_curva_poste", tipologia_tramo)
        umbral_curva_vano = obtener_umbral(umbrales, "descentramiento_curva_vano", tipologia_tramo)

        detalle_kpig2 = {}
        valores_medios = []
        cantidad = []
        valor_maximo_total = 0 

        # 1. Para rectas
        if mediciones.get('muestras_rectas', 0) > 0:
            valor_recto = mediciones.get('descentramiento_recta_media', 0)
            valor_recto_max = mediciones.get('descentramiento_recta_max', 0)
            valores_medios.append(valor_recto)
            cantidad.append(mediciones['muestras_rectas'])
            valor_maximo_total = max(valor_maximo_total, valor_recto_max)
            detalle_kpig2['recto'] = {
                'valor': round(valor_recto, 2),
                'valor_max': round(valor_recto_max, 2),
                'muestras': mediciones['muestras_rectas'],
                'referencia': umbral_recto.get('valor_referencia', 20) if umbral_recto else 20
            }
    
    # 2. Para curvas en poste
        if mediciones.get('muestras_curvas_poste', 0) > 0:
            valor_curva_poste = mediciones.get('descentramiento_curva_poste_media', 0)
            valor_curva_poste_max = mediciones.get('descentramiento_curva_poste_max', 0)
            valores_medios.append(valor_curva_poste)
            cantidad.append(mediciones['muestras_curvas_poste'])
            valor_maximo_total = max(valor_maximo_total, valor_curva_poste_max)
            detalle_kpig2['curva_poste'] = {
                'valor': round(valor_curva_poste, 2),
                'valor_max': round(valor_curva_poste_max, 2),
                'muestras': mediciones['muestras_curvas_poste'],
                'referencia': umbral_curva_poste.get('valor_referencia', 20) if umbral_curva_poste else 20
            }
    
    # 3. Para curvas en vano
        if mediciones.get('muestras_curvas_vano', 0) > 0:
            valor_curva_vano = mediciones.get('descentramiento_curva_vano_media', 0)
            valor_curva_vano_max = mediciones.get('descentramiento_curva_vano_max', 0)
            valores_medios.append(valor_curva_vano)
            cantidad.append(mediciones['muestras_curvas_vano'])
            valor_maximo_total = max(valor_maximo_total, valor_curva_vano_max)
            detalle_kpig2['curva_vano'] = {
                'valor': round(valor_curva_vano, 2),
                'valor_max': round(valor_curva_vano_max, 2),
                'muestras': mediciones['muestras_curvas_vano'],
                'referencia': umbral_curva_vano.get('valor_referencia', 20) if umbral_curva_vano else 20
            }

        KPIG2 = 0
        if valores_medios:
            if sum(cantidad) > 0:
                KPIG2 = sum(v * p for v, p in zip(valores_medios, cantidad)) / sum(cantidad)
    
        KPIG2 = round(KPIG2, 2)
        valor_maximo_total = round(valor_maximo_total, 2)
    
        resultados.append(['Ind_KPIG2', KPIG2, id_tramo, 'S', {'recto': umbral_recto,'curva_poste': umbral_curva_poste,'curva_vano': umbral_curva_vano}, detalle_kpig2, valor_maximo_total])


    if "Ind_KPIG3" in kpigs_seleccionados:
        altura_media = round(mediciones.get('altura_media') or 0, 3)
        valor_maximo = round(mediciones.get('altura_max')or 0, 3)
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"altura",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG3 = obtener_umbral(umbrales, "altura", tipologia_tramo)

        altura_ref = umbral_KPIG3.get('valor_referencia', 0)
        KPIG3 = abs((altura_media - altura_ref) / altura_ref) * 100

        resultados.append(['Ind_KPIG3', round(KPIG3, 2), id_tramo, 'S', umbral_KPIG3,valor_maximo])



    if "Ind_KPIG4" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"altura",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG4 = obtener_umbral(umbrales, 'altura', tipologia_tramo)
        altura_ref = umbral_KPIG4.get('valor_referencia', 0)
        alturas_medidas = mediciones.get('alturas', [])  

        alturas_inferiores = [h for h in alturas_medidas if h < altura_ref]

        if alturas_inferiores and altura_ref != 0:
            altura_min = min(alturas_inferiores)
            KPIG4 = abs(altura_min - altura_ref ) / altura_ref * 100
        else:
            KPIG4 = 0 
        
        valor_maximo = max(alturas_medidas) if alturas_medidas else 0

        resultados.append(['Ind_KPIG4', round(KPIG4, 2), id_tramo, 'S', umbral_KPIG4, valor_maximo])

    if "Ind_KPIG5" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"altura",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG5 = obtener_umbral(umbrales, 'altura', tipologia_tramo)
        altura_ref = umbral_KPIG5.get('valor_referencia', 0)
        alturas_LAC = mediciones.get('alturas', [])  
    
        diferencias_superiores = [h - altura_ref for h in alturas_LAC if h > altura_ref and altura_ref != 0]
    
        if diferencias_superiores:
            max_diferencia = max(diferencias_superiores)
            KPIG5 = (max_diferencia / altura_ref) * 100
        else:
            KPIG5 = 0

        valor_maximo = max(alturas_LAC) if alturas_LAC else 0

        resultados.append(['Ind_KPIG5', round(KPIG5, 2), id_tramo, 'S', umbral_KPIG5, valor_maximo])


    if "Ind_KPIG6" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"descentramiento_recta",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_recto = obtener_umbral(umbrales, "descentramiento_recta", tipologia_tramo)
        umbral_curva_poste = obtener_umbral(umbrales, "descentramiento_curva_poste", tipologia_tramo)
        umbral_curva_vano = obtener_umbral(umbrales, "descentramiento_curva_vano", tipologia_tramo)

        detalle_kpig6 = {}
        variaciones = []
        cantidad = []
        max_variacion_total = 0 

        # 1. Para rectas
        if mediciones.get('muestras_rectas', 0) > 0 and umbral_recto:
            ref_recto = umbral_recto.get('valor_referencia', 0)
            if ref_recto != 0:
                valor_recto = mediciones.get('descentramiento_recta_media', 0)
                valor_recto_max = mediciones.get('descentramiento_recta_max', 0)
                variacion_recta = abs((valor_recto - ref_recto) / ref_recto) * 100
                variacion_recta_max = abs((valor_recto_max - ref_recto) / ref_recto) * 100
                variaciones.append(variacion_recta)
                cantidad.append(mediciones['muestras_rectas'])
                max_variacion_total = max(max_variacion_total, variacion_recta_max)
                detalle_kpig6['recto'] = {
                    'valor': round(variacion_recta, 2),
                    'valor_max': round(valor_recto_max, 2),
                    'muestras': mediciones['muestras_rectas'],
                    'valor_medio': round(valor_recto, 2),
                    'referencia': round(ref_recto, 2)
                }
        
        # 2. Para curvas en poste
        if mediciones.get('muestras_curvas_poste', 0) > 0 and umbral_curva_poste:
            ref_curva_poste = umbral_curva_poste.get('valor_referencia', 0)
            if ref_curva_poste != 0:
                valor_curva_poste = mediciones.get('descentramiento_curva_poste_media', 0)
                valor_curva_poste_max = mediciones.get('descentramiento_curva_poste_max', 0)
                variacion_curva_poste = abs((valor_curva_poste - ref_curva_poste) / ref_curva_poste) * 100
                variacion_curva_poste_max = abs((valor_curva_poste_max - ref_curva_poste) / ref_curva_poste) * 100
                variaciones.append(variacion_curva_poste)
                cantidad.append(mediciones['muestras_curvas_poste'])
                max_variacion_total = max(max_variacion_total, variacion_curva_poste_max)
                detalle_kpig6['curva_poste'] = {
                    'valor': round(variacion_curva_poste, 2),
                    'valor_max': round(valor_curva_poste_max, 2),
                    'muestras': mediciones['muestras_curvas_poste'],
                    'valor_medio': round(valor_curva_poste, 2),
                    'referencia': round(ref_curva_poste, 2)
                }
        
        # 3. Para curvas en vano
        if mediciones.get('muestras_curvas_vano', 0) > 0 and umbral_curva_vano:
            ref_curva_vano = umbral_curva_vano.get('valor_referencia', 0)
            if ref_curva_vano != 0:
                valor_curva_vano = mediciones.get('descentramiento_curva_vano_media', 0)
                valor_curva_vano_max = mediciones.get('descentramiento_curva_vano_max', 0)
                variacion_curva_vano = abs((valor_curva_vano - ref_curva_vano) / ref_curva_vano) * 100
                variacion_curva_vano_max = abs((valor_curva_vano_max - ref_curva_vano) / ref_curva_vano) * 100
                variaciones.append(variacion_curva_vano)
                cantidad.append(mediciones['muestras_curvas_vano'])
                max_variacion_total = max(max_variacion_total, variacion_curva_vano_max)
                detalle_kpig6['curva_vano'] = {
                    'valor': round(variacion_curva_vano, 2),
                    'valor_max': round(valor_curva_vano_max, 2),
                    'muestras': mediciones['muestras_curvas_vano'],
                    'valor_medio': round(valor_curva_vano, 2),
                    'referencia': round(ref_curva_vano, 2)
                }

        KPIG6 = 0
        if variaciones:
            if sum(cantidad) > 0:
                KPIG6 = sum(v * p for v, p in zip(variaciones, cantidad)) / sum(cantidad)
        
        KPIG6 = max(0, min(100, round(KPIG6, 2)))
        max_variacion_total = round(max_variacion_total,2)
        resultados.append(['Ind_KPIG6', KPIG6, id_tramo, 'S', {'recto': umbral_recto,'curva_poste': umbral_curva_poste,'curva_vano': umbral_curva_vano},detalle_kpig6,max_variacion_total])
    if "Ind_KPIG7" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"descentramiento_recta",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_recto = obtener_umbral(umbrales, "descentramiento_recta", tipologia_tramo)
        umbral_curva_poste = obtener_umbral(umbrales, "descentramiento_curva_poste", tipologia_tramo)
        umbral_curva_vano = obtener_umbral(umbrales, "descentramiento_curva_vano", tipologia_tramo)

        detalle_kpig7 = {}
        desviaciones = []
        cantidades = []
        max_desviacion_total = 0

        # 1. Para rectas
        if mediciones.get('muestras_rectas', 0) > 0 and umbral_recto:
            ref_recto = umbral_recto.get('valor_referencia', 0)
            if ref_recto != 0:
                valor_recto_max = mediciones.get('descentramiento_recta_max', 0)
                valor_recto_medio = mediciones.get('descentramiento_recta_media', 0)
                desviacion_recta = abs((valor_recto_max - ref_recto) / ref_recto) * 100
                desviacion_recta_medio = abs((valor_recto_medio - ref_recto) / ref_recto) * 100
                desviaciones.append(desviacion_recta)
                cantidades.append(mediciones['muestras_rectas'])
                max_desviacion_total = max(max_desviacion_total, desviacion_recta)
                detalle_kpig7['recto'] = {
                    'valor': round(desviacion_recta, 2),
                    'valor_max': round(valor_recto_max, 2),
                    'muestras': mediciones['muestras_rectas'],
                    'valor_medio': round(valor_recto_medio, 2),
                    'referencia': round(ref_recto, 2)
                }

        # 2. Para curvas en poste
        if mediciones.get('muestras_curvas_poste', 0) > 0 and umbral_curva_poste:
            ref_curva_poste = umbral_curva_poste.get('valor_referencia', 0)
            if ref_curva_poste != 0:
                valor_curva_poste_max = mediciones.get('descentramiento_curva_poste_max', 0)
                valor_curva_poste_medio = mediciones.get('descentramiento_curva_poste_media', 0)
                desviacion_curva_poste = abs((valor_curva_poste_max - ref_curva_poste) / ref_curva_poste) * 100
                desviacion_curva_poste_medio = abs((valor_curva_poste_medio - ref_curva_poste) / ref_curva_poste) * 100
                desviaciones.append(desviacion_curva_poste)
                cantidades.append(mediciones['muestras_curvas_poste'])
                max_desviacion_total = max(max_desviacion_total, desviacion_curva_poste)
                detalle_kpig7['curva_poste'] = {
                    'valor': round(desviacion_curva_poste, 2),
                    'valor_max': round(valor_curva_poste_max, 2),
                    'muestras': mediciones['muestras_curvas_poste'],
                    'valor_medio': round(valor_curva_poste_medio, 2),
                    'referencia': round(ref_curva_poste, 2)
                }

        # 3. Para curvas en vano
        if mediciones.get('muestras_curvas_vano', 0) > 0 and umbral_curva_vano:
            ref_curva_vano = umbral_curva_vano.get('valor_referencia', 0)
            if ref_curva_vano != 0:
                valor_curva_vano_max = mediciones.get('descentramiento_curva_vano_max', 0)
                valor_curva_vano_medio = mediciones.get('descentramiento_curva_vano_media', 0)
                desviacion_curva_vano = abs((valor_curva_vano_max - ref_curva_vano) / ref_curva_vano) * 100
                desviacion_curva_vano_medio = abs((valor_curva_vano_medio - ref_curva_vano) / ref_curva_vano) * 100
                desviaciones.append(desviacion_curva_vano)
                cantidades.append(mediciones['muestras_curvas_vano'])
                max_desviacion_total = max(max_desviacion_total, desviacion_curva_vano)
                detalle_kpig7['curva_vano'] = {
                    'valor': round(desviacion_curva_vano, 2),
                    'valor_max': round(valor_curva_vano_max, 2),
                    'muestras': mediciones['muestras_curvas_vano'],
                    'valor_medio': round(valor_curva_vano_medio, 2),
                    'referencia': round(ref_curva_vano, 2)
                }

        KPIG7 = 0
        if desviaciones and sum(cantidades) > 0:
            KPIG7 = sum(d * c for d, c in zip(desviaciones, cantidades)) / sum(cantidades)

        KPIG7 = max(0, min(100, round(KPIG7, 2)))
        max_desviacion_total = round(max_desviacion_total, 2)         

        resultados.append(['Ind_KPIG7', KPIG7, id_tramo, 'S', {'recto': umbral_recto, 'curva_poste': umbral_curva_poste, 'curva_vano': umbral_curva_vano}, detalle_kpig7, max_desviacion_total])


    if "Ind_KPIG8" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"flecha",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG8 = obtener_umbral(umbrales, "flecha", tipologia_tramo)
        referencia = umbral_KPIG8.get('valor_referencia', 0)

        mediciones_flecha_media = mediciones.get('flecha_media', [])
        valor_maximo = round(mediciones.get('flecha_max')or 0, 3)

        KPIG8 = mediciones_flecha_media
        KPIG8 = max(0, min(100, round(KPIG8, 2)))

        resultados.append(['Ind_KPIG8', KPIG8, id_tramo, 'S', umbral_KPIG8,valor_maximo])

    if "Ind_KPIG9" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"flecha",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG9 = obtener_umbral(umbrales, "flecha", tipologia_tramo)
        referencia = umbral_KPIG9.get('valor_referencia', 13)  
    
        flechas_individuales = mediciones.get('flechas_individuales', [])
        valor_maximo = round(mediciones.get('flecha_max')or 0, 3)
    
        max_desviacion = 0
    
        for flecha in flechas_individuales:
            if flecha is not None:
                desviacion_absoluta = abs(flecha - referencia)/referencia
                if desviacion_absoluta > max_desviacion:
                    max_desviacion = desviacion_absoluta
    
        KPIG9 = round(max_desviacion, 2)
    
        resultados.append(['Ind_KPIG9', KPIG9, id_tramo, 'S', umbral_KPIG9,valor_maximo])

    if "Ind_KPIG10" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"contraflecha",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG10 = obtener_umbral(umbrales, "contraflecha", tipologia_tramo)
        contraflecha_media = round(mediciones.get('contraflecha_media', 0), 2)
        valor_maximo = round(mediciones.get('flecha_max')or 0, 3)
        resultados.append(['Ind_KPIG10', contraflecha_media, id_tramo, 'S',umbral_KPIG10,valor_maximo])

    if "Ind_KPIG11" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"contraflecha",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)

        umbral_KPIG11 = obtener_umbral(umbrales, "contraflecha", tipologia_tramo)
        referencia = umbral_KPIG11.get('valor_referencia', 0)
    
        contraflechas_individuales = mediciones.get('contraflecha_individuales', [])
        contraflechas_validas = [cf for cf in contraflechas_individuales if cf is not None]

        if contraflechas_validas:
            valor_maximo = max(contraflechas_validas)
            desviacion = abs(valor_maximo - referencia) / referencia if referencia != 0 else 0
            KPIG11 = round(min(desviacion, 100), 2)
        else:
            valor_maximo = 0
            KPIG11 = 0
        
        resultados.append(['Ind_KPIG11', KPIG11, id_tramo, 'S', umbral_KPIG11,valor_maximo])

    if "Ind_KPIG13" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"pendiente",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG13 = obtener_umbral(umbrales, "pendiente", tipologia_tramo,velocidad_tramo)
        referencia = umbral_KPIG13.get('valor_referencia', 0)
    
        pendientes_individuales = mediciones.get('pendientes_individuales', [])
        pendientes_validas = [p for p in pendientes_individuales if p is not None]
        
        valor_maximo = max(pendientes_validas) if pendientes_validas else 0
        max_desviacion = 0
    
        for pendiente in pendientes_validas:
            if referencia != 0:
                desviacion_absoluta = abs(pendiente - referencia) / referencia
                if desviacion_absoluta > max_desviacion:
                    max_desviacion = desviacion_absoluta
    
        KPIG13 = round(max_desviacion, 2) 
    
        resultados.append(['Ind_KPIG13', KPIG13, id_tramo, 'S', umbral_KPIG13, valor_maximo])
    
    if "Ind_KPIG14" in kpigs_seleccionados:
        tipologia_tramo = obtener_tipologia(tramos, id_tramo,umbrales,"var_pendiente",velocidad_tramo,pto_km_ini,pto_km_fin,id_via)
        umbral_KPIG14 = obtener_umbral(umbrales, "var_pendiente", tipologia_tramo, velocidad_tramo)
        referencia = umbral_KPIG14.get('valor_referencia', 0)
    
        variaciones_pendiente = mediciones.get('variacion_pendiente_individuales', [])
        variaciones_validas = [v for v in variaciones_pendiente if v is not None]
    
        if variaciones_validas and referencia != 0:
            max_variacion = max(abs(v) for v in variaciones_validas)
            KPIG14 = round(max_variacion / referencia, 2)
            valor_maximo = max(variaciones_validas)
        else: 
            KPIG14 = 0
            valor_maximo = 0
    
        resultados.append(['Ind_KPIG14', KPIG14, id_tramo, 'S', umbral_KPIG14, valor_maximo])
        
    return resultados

def pintar(data, output_file='gauges_output.html'):
    """ Esta funcion permite graficar la estructura y categorizacion de los distiintos tipos de indicadores"""

    colors = [
        {"name": "Mala", "color": "#D73027"},
        {"name": "Deficiente", "color": "#FC8D59"},
        {"name": "Regular", "color": "#FEE08B"},
        {"name": "Aceptable", "color": "#91CF60"},
        {"name": "Buena", "color": "#1A9850"}
    ]
    
    colors_dict = {item["name"]: item["color"] for item in colors}

    kg1_thresholds = {
        'valores_N4': [0, 2],
        'valores_N3': [2, 3.5],   
        'valores_N2': [3.5, 5.5],  
        'valores_N1': [5.5, 7],   
        'valores_N0': [7, 10]      
    }

    descripciones = {
        "Ind_KPIG1": "KPIG1. Altura media del HC respecto del plano de la vía",
        "Ind_KPIG2": "KPIG2. Descentramiento medio del HC respecto al eje longitudinal",
        "Ind_KPIG3": "KPIG3. Desviación de altura en curva",
        "Ind_KPIG4": "KPIG4. Desviación inferior máxima de la altura del HC",
        "Ind_KPIG5": "KPIG5. Desviación superior máxima de la altura del HC",
        "Ind_KPIG6": "KPIG6. Desviación media de descentramiento del HC",
        "Ind_KPIG7": "KPIG7. Desviación máxima de descentramiento del HC ",
        "Ind_KPIG8": "KPIG8. Flecha media del HC",
        "Ind_KPIG9": "KPIG9. Contraflecha máxima del HC",
        "Ind_KPIG10": "KPIG10. Contraflecha media del HC",
        "Ind_KPIG11": "KPIG11. Desviación máxima de la contraflecha del HC",
        "Ind_KPIG12": "KPIG12. Efecto tijera en zonas comunes o de solape",
        "Ind_KPIG13": "KPIG13. Desviación máxima de la pendiente del HC ",
        "Ind_KPIG14": "KPIG14. Desviación máxima de la Δ de la pendiente del HC ",
        "Ind_KG1": "KG1. Índice de Calidad de Geometría",
    }

    unidades = {
        "Ind_KPIG1": "m",
        "Ind_KPIG2": "cm",
        "Ind_KPIG3": "%",
        "Ind_KPIG4": "%",
        "Ind_KPIG5": "%",
        "Ind_KPIG6": "%",
        "Ind_KPIG8": "%",
        "Ind_KPIG7": "%",
        "Ind_KPIG9": "%",
        "Ind_KPIG10": "cm",
        "Ind_KPIG11": "%",
        "Ind_KPIG12": "%",
        "Ind_KPIG13": "%",
        "Ind_KPIG14": "%",
        "Ind_KG1": "",
    }

    def _build_indicator_title(name: str, unit: str, tipo_label: str | None = None) -> str:
        """Construye el título: KPI grande (h2) + descripción debajo (h3)."""
        descripcion = descripciones.get(name, name)
        if ". " in descripcion:
            descripcion = descripcion.split(". ", 1)[1].strip()
        if tipo_label:
            descripcion = f"{descripcion} - {tipo_label}"
        if unit:
            descripcion = f"{descripcion} ({unit})"

        descripcion_lines = textwrap.wrap(
            descripcion,
            width=42,
            break_long_words=False,
            break_on_hyphens=False,
        ) or [descripcion]
        descripcion_html = "<br>".join(html_escape(line) for line in descripcion_lines)

        return (
            f"<span style='font-size:1.5rem;font-weight:700;line-height:1.1'>{html_escape(name)}</span>"
            f"<br><span style='font-size:1.15rem;font-weight:600;line-height:1.2'>{descripcion_html}</span>"
        )


    def get_zones_from_threshold(umbral, valor_maximo, value=None):
        if not umbral:
            return [], None, None, [], None, None

        try:
            thresholds = {}
            has_zero_zone = False
            for i in range(0, 5):
                key = f'valores_N{i}'
                if key in umbral:
                    thresholds[i] = list(map(float, umbral[key]))
                    if i == 0 or 0 in thresholds[i]:
                        has_zero_zone = True
        except:
            return [], None, None, [], None, None

        max_val = float(valor_maximo) if valor_maximo is not None else max(max(v) for v in thresholds.values() if v)

        available_colors = [item["color"] for item in colors]
        available_names = [item["name"] for item in colors]

        zonas_reales = []
        sorted_levels = sorted([k for k in thresholds.keys() if k != 0], reverse=True)
    
        for i, level in enumerate(sorted_levels):
            zonas_reales.append({
                'min': thresholds[level][0],
                'max': thresholds[level][1],
                'color': available_colors[i],
                'name': available_names[i]
            })

        if has_zero_zone:
            last_threshold_max = thresholds[sorted_levels[-1]][1]
            zonas_reales.append({
                'min': last_threshold_max,
                'max': max_val,
                'color': colors_dict["Buena"],
                'name': "Buena"
            })
        else:
            first_threshold_min = thresholds[sorted_levels[-1]][0]
            zonas_reales.insert(0, {
                'min': 0,
                'max': first_threshold_min,
                'color': colors_dict["Buena"],
                'name': "Buena"
            })

        zonas_reales = sorted(zonas_reales, key=lambda x: x['min'])

        num_zones = len(zonas_reales)
        step_size = max_val / num_zones
    
        steps = []
        for i, zona in enumerate(zonas_reales):
            steps.append({
                "range": [i * step_size, (i + 1) * step_size],
                "color": zona['color']
            })

        adjusted_value = None
        if value is not None and zonas_reales:
            for i, zona in enumerate(zonas_reales):
                if zona['min'] <= value <= zona['max']:
                    zone_ratio = (value - zona['min']) / (zona['max'] - zona['min'])
                    adjusted_value = i * step_size + zone_ratio * step_size
                    break
            # else:
            #     adjusted_value = max_val


        valor_ref_original = float(umbral.get('valor_referencia')) if 'valor_referencia' in umbral else None
        valor_ref_adjusted = None
        
        if valor_ref_original is not None and zonas_reales:
            for i, zona in enumerate(zonas_reales):
                if zona['min'] <= valor_ref_original <= zona['max']:
                    zone_ratio = (valor_ref_original - zona['min']) / (zona['max'] - zona['min'])
                    valor_ref_adjusted = i * step_size + zone_ratio * step_size
                    break

        return steps, max_val, valor_ref_original, zonas_reales, adjusted_value, valor_ref_adjusted


    kg1_entry = None
    kpig_entries = []

    for entry in data:
        if entry[0] == "Ind_KG1":
            kg1_entry = entry
        else:
            kpig_entries.append(entry)
    

    def kpig_sort_key(entry):
        name = entry[0]
        num = int(name.replace("Ind_KPIG", "")) if "Ind_KPIG" in name else float('inf')
        return num

    kpig_entries.sort(key=kpig_sort_key)

    sorted_data = []
    if kg1_entry:
        sorted_data.append(kg1_entry)
    sorted_data.extend(kpig_entries)

    valid_entries = []
    special_kpigs = []  

    for entry in data:
        if len(entry) < 2 or not isinstance(entry[1], (int, float)):
            continue

        name = entry[0]
        
        if name == "Ind_KG1":
            value = float(entry[1])
            max_val = 10  
            
            steps, max_val_visual, _, zonas_reales, adjusted_value, _ = get_zones_from_threshold(kg1_thresholds, max_val, value)
            
            unit = unidades.get(name, "")
            label = _build_indicator_title(name, unit)
            
            leyenda_html = ""
            if zonas_reales:
                leyenda_html += "<br><span style='font-size:13px'>"
                zonas_ordenadas = sorted(zonas_reales, key=lambda x: x['min'])
                for zona in zonas_ordenadas:
                    leyenda_html += f"<span style='color:{zona['color']};'>■</span> {zona['min']:.2f}–{zona['max']:.2f}&nbsp;&nbsp;"
                leyenda_html += "</span>"
            
            label += leyenda_html
            
            valid_entries.append({
                'name': name,
                'label': label,
                'value': value,
                'max_val': max_val_visual,
                'steps': steps,
                'valor_ref_original': None,
                'valor_ref_adjusted': None,
                'unit': unit,
                'adjusted_value': adjusted_value,
                'original_name': name
            })
            continue
        
        if name in ("Ind_KPIG6", "Ind_KPIG2","Ind_KPIG7") and len(entry) > 5 and isinstance(entry[5], dict):
            detalle = entry[5] 
            for tipo, datos in detalle.items():
                tipo_label = {
                    'recto': 'Recta',
                    'curva_poste': 'Curva Poste',
                    'curva_vano': 'Curva Vano'
                }.get(tipo, tipo)
                
                new_name = f"{name}_{tipo}"
                value = datos['valor']
                valor_maximo = datos['valor_max']
                umbral = entry[4].get(tipo) 
                
                steps, max_val_visual, valor_ref_original, zonas_reales, adjusted_value, valor_ref_adjusted = get_zones_from_threshold(
                    umbral, valor_maximo, value)
                
                unit = "%"
                label = _build_indicator_title(name, unit, tipo_label)
                
                if valor_ref_original is not None:
                    label += f"<br><span style='font-size:12px;color:#666'>Valor Ref: {valor_ref_original:.2f}</span>"
                
                leyenda_html = ""
                if zonas_reales:
                    leyenda_html += "<br><span style='font-size:13px'>"
                    zonas_ordenadas = sorted(zonas_reales, key=lambda x: x['min'])
                    for zona in zonas_ordenadas:
                        leyenda_html += f"<span style='color:{zona['color']};'>■</span> {zona['min']:.2f}–{zona['max']:.2f}&nbsp;&nbsp;"
                    leyenda_html += "</span>"
                
                label += leyenda_html
                
                special_kpigs.append({
                    'name': new_name,
                    'label': label,
                    'value': value,
                    'max_val': max_val_visual,
                    'steps': steps,
                    'valor_ref_original': valor_ref_original,
                    'valor_ref_adjusted': valor_ref_adjusted,
                    'unit': unit,
                    'adjusted_value': adjusted_value,
                    'original_name': name
                })
            
            continue  
        
        value = float(entry[1])
        umbral = entry[4] if len(entry) > 4 else None
        valor_maximo = entry[5] if len(entry) > 5 else None
        unit = unidades.get(name, "")

        label = _build_indicator_title(name, unit)

        steps, max_val_visual, valor_ref_original, zonas_reales, adjusted_value, valor_ref_adjusted = get_zones_from_threshold(umbral, valor_maximo, value)

        leyenda_html = ""
        if zonas_reales:
            leyenda_html += "<br><span style='font-size:13px'>"
            zonas_ordenadas = sorted(zonas_reales, key=lambda x: x['min'])
            for zona in zonas_ordenadas:
                leyenda_html += f"<span style='color:{zona['color']};'>■</span> {zona['min']:.2f}–{zona['max']:.2f}&nbsp;&nbsp;"
            leyenda_html += "</span>"

        if valor_ref_original is not None:
            label += f"<br><span style='font-size:12px;color:#666'>Valor Ref: {valor_ref_original:.2f}</span>"

        label += leyenda_html

        valid_entries.append({
            'name': name,
            'label': label,
            'value': value,
            'max_val': max_val_visual,
            'steps': steps,
            'valor_ref_original': valor_ref_original,
            'valor_ref_adjusted': valor_ref_adjusted,
            'unit': unit,
            'adjusted_value': adjusted_value,
            'original_name': name
        })    
    all_entries = valid_entries + special_kpigs
    
    special_kpig_groups = {
        "Ind_KPIG2": [],
        "Ind_KPIG6": [],
        "Ind_KPIG7": []
    }
    
    for entry in all_entries:
        if entry['original_name'] in special_kpig_groups:
            special_kpig_groups[entry['original_name']].append(entry)
    
    special_kpig_groups = {k: v for k, v in special_kpig_groups.items() if v}
    
    normal_entries = [entry for entry in all_entries if entry['original_name'] not in special_kpig_groups]
    
    
    cols_normal = 2
    cols_special = 3  
    
    rows_normal = (len(normal_entries) + cols_normal - 1) // cols_normal
    
    special_rows = 0
    special_group_layout = {}
    
    for group_name, group_entries in special_kpig_groups.items():
        group_rows = (len(group_entries) + cols_special - 1) // cols_special
        special_rows += group_rows
        special_group_layout[group_name] = {
            'entries': group_entries,
            'rows': group_rows
        }
    
    total_rows = rows_normal + special_rows
    
    max_cols = max(cols_normal, cols_special)
    
    specs = []
    current_row = 0
    
    for group_name, group_info in special_group_layout.items():
        group_entries = group_info['entries']
        group_rows = group_info['rows']
        
        for row_in_group in range(group_rows):
            row_entries = group_entries[row_in_group*cols_special : (row_in_group+1)*cols_special]
            spec_row = [{"type": "indicator"} for _ in range(len(row_entries))]
            
            if len(row_entries) < max_cols:
                spec_row.extend([None] * (max_cols - len(row_entries)))
            
            specs.append(spec_row)
            current_row += 1
    
    for row in range(rows_normal):
        spec_row = [{"type": "indicator"} for _ in range(cols_normal)]
        
        if cols_normal < max_cols:
            spec_row.extend([None] * (max_cols - cols_normal))
        
        specs.append(spec_row)
    

    if total_rows == 0:
        raise ValueError("No hay datos para mostrar en la visualización.")

    fig = make_subplots(
        rows=total_rows,
        cols=max_cols,
        specs=specs,
        horizontal_spacing=0.1
    )
    
    current_row = 1
    
    for group_name, group_info in special_group_layout.items():
        group_entries = group_info['entries']
        group_rows = group_info['rows']
        
        for row_in_group in range(group_rows):
            row_entries = group_entries[row_in_group*cols_special : (row_in_group+1)*cols_special]
            
            for col, entry in enumerate(row_entries, start=1):
                if entry['valor_ref_adjusted'] is not None and entry['max_val'] is not None:
                    entry['steps'].append({
                        "range": [entry['valor_ref_adjusted'] - 0.001 * entry['max_val'], 
                                 entry['valor_ref_adjusted'] + 0.001 * entry['max_val']],
                        "color": "black"
                    })

                gauge_config = {
                    "axis": {
                        "range": [0, entry['max_val']] if entry['max_val'] is not None else None,
                        "tickwidth": 1,
                        "showticklabels": False,
                        "tickcolor": "darkgray"
                    },
                    "bar": {"color": "darkblue", "thickness": 0.00},
                    "steps": entry['steps'],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": entry['adjusted_value']
                    },
                    "shape": "angular",
                    "bgcolor": "white"
                }

                if entry['adjusted_value'] is not None and entry['adjusted_value'] > 0:
                    gauge_config["steps"] = [step for step in gauge_config["steps"] if step.get("color") != "darkblue"]
                    gauge_config["steps"].append({
                        "range": [0, entry['adjusted_value']],
                        "color": "darkblue",
                        "thickness": 0.5
                    })

                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=entry['value'],
                    number={
                        "valueformat": ".2f",
                        "suffix": f" {entry['unit']}" if entry['unit'] else ""
                    },
                    title={"text": entry['label'], "font": {"size": 20}},
                    gauge=gauge_config
                ), row=current_row, col=col)
            
            current_row += 1
    
    for i, entry in enumerate(normal_entries):
        row = current_row + (i // cols_normal)
        col = (i % cols_normal) + 1
        
        if entry['valor_ref_adjusted'] is not None and entry['max_val'] is not None:
            entry['steps'].append({
                "range": [entry['valor_ref_adjusted'] - 0.001 * entry['max_val'], 
                         entry['valor_ref_adjusted'] + 0.001 * entry['max_val']],
                "color": "black"
            })

        gauge_config = {
            "axis": {
                "range": [0, entry['max_val']] if entry['max_val'] is not None else None,
                "tickwidth": 1,
                "showticklabels": False,
                "tickcolor": "darkgray"
            },
            "bar": {"color": "darkblue", "thickness": 0.00},
            "steps": entry['steps'],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": entry['adjusted_value']
            },
            "shape": "angular",
            "bgcolor": "white"
        }

        if entry['adjusted_value'] is not None and entry['adjusted_value'] > 0:
            gauge_config["steps"] = [step for step in gauge_config["steps"] if step.get("color") != "darkblue"]
            gauge_config["steps"].append({
                "range": [0, entry['adjusted_value']],
                "color": "darkblue",
                "thickness": 0.5
            })

        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=entry['value'],
            number={
                "valueformat": ".2f",
                "suffix": f" {entry['unit']}" if entry['unit'] else ""
            },
            title={"text": entry['label'], "font": {"size": 20}},
            gauge=gauge_config
        ), row=row, col=col)

    fig.update_layout(
        height=400 * total_rows,
        width=500 * max_cols,
        margin=dict(t=130, b=80, l=50, r=50),
        font=dict(family="Arial", size=12),
    )

    pio.write_html(fig, file=output_file, auto_open=False)

def pintar_incidencias(conteo_incidencias, incidencias_seleccionadas, output_file='incidencias.html'):
    """ Esta funcion permite pintar las incidencias"""

    # print(conteo_incidencias)
    mapeo_incidencias = {
        "Por defecto de altura": "KPIT1",
        "Por defecto de descentramiento": "KPIT2",
        "Por defecto de pendiente": "KPIT3",
        "Por defecto de la variación de la pendiente": "KPIT4",
        "Por defecto de flecha": "KPIT5",
        "Por defecto de contraflecha": "KPIT6",
        "Por defecto de tijera": "KPIT7",
        "Por contacto fuera de la zona de trabajo del pantógrafo": "KPIT8",
        "Número global de incidencias": "KGIT1",
        "Índice global de evaluación de la tasa de fallos de la catenaria": "KGIT2",
        "Otras causas": "KPIT9"
    }
    
    descripciones_cortas = {
        "KPIT1": "Altura",
        "KPIT2": "Descentramiento",
        "KPIT3": "Pendiente",
        "KPIT4": "Variación de la pendiente",
        "KPIT5": "Flecha",
        "KPIT6": "Contraflecha",
        "KPIT7": "Tijera",
        "KPIT8": "Contacto fuera de la zona del pantógrafo",
        "KGIT1": "Nº global incidencias",
        "KGIT2": "Índice global tasa de fallos",
        "KPIT9": "otras causas"
    }

    datos = [
        {"codigo": mapeo_incidencias[nombre], 
         "valor": conteo_incidencias[mapeo_incidencias[nombre]],
         "descripcion": descripciones_cortas[mapeo_incidencias[nombre]]}
        for nombre in incidencias_seleccionadas
        if mapeo_incidencias[nombre] in conteo_incidencias
    ]
    
    if not datos:
        return f"<p>{GENERIC['no_data']}</p>"
    
    datos.sort(key=lambda d: d["codigo"], reverse=True)

    fig = go.Figure(data=[
        go.Bar(
            x=[d["valor"] for d in datos],
            y=[f"{d['codigo']}&nbsp;<br><span style='font-size:10px'>{d['descripcion']}</span>&nbsp;" for d in datos],
            orientation='h',
            text=[f"  {d['valor']}" for d in datos], 
            textposition='inside',
            insidetextanchor='start'
        )
    ])

    fig.update_layout(
        title='Incidencias',
        showlegend=False,
        paper_bgcolor='white',
        bargap=0.4,
        yaxis=dict(tickfont=dict(size=12)),
        margin=dict(l=150, r=40, t=40, b=40)
        
    )
    config = {
    'staticPlot': True,     
    'displayModeBar': False, 
    'displaylogo': True
    }
    
    pio.write_html(fig,file=output_file,auto_open=False,config=config)
    
    return output_file

estado_sync = {"trabajando": False, "mensaje": ""}


