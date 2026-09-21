from typing import List, Dict, Any
from couchbase.exceptions import DocumentNotFoundException, DocumentExistsException
from couchbase.options import QueryOptions
def obtener_umbrales_crud(cluster, clausula_FROM) -> List[Dict[str, Any]]:
    """Esta funcion es para la consulta de umbrales"""
    consulta = f'''
        SELECT
            META(u).id AS doc_id,
            u.tipo,
            u.tipologia,
            u.velocidad,
            u.valor_referencia,
            u.valores_N1,
            u.valores_N2,
            u.valores_N3,
            u.valores_N4
        {clausula_FROM}`Maestro_Umbrales` u
        ORDER BY u.tipo, u.tipologia, u.velocidad; 
    '''
    resultado = cluster.query(consulta)
    umbrales = []
    for fila in resultado:
        umbrales.append({
            "doc_id": fila.get("doc_id"),
            "tipo": fila.get("tipo", ""),
            "tipologia": fila.get("tipologia", ""),
            "velocidad": fila.get("velocidad", None),
            "valor_referencia": fila.get("valor_referencia", ""),
            "valores_N1": fila.get("valores_N1", []),
            "valores_N2": fila.get("valores_N2", []),
            "valores_N3": fila.get("valores_N3", []),
            "valores_N4": fila.get("valores_N4", []),
        })
    return umbrales
def obtener_umbrales(cluster, clausula_FROM):
    query = (
        "SELECT tipo, tipologia, velocidad, valor_referencia, valores_N1, valores_N2, valores_N3, valores_N4 "
        + clausula_FROM + "`Maestro_Umbrales`"
    )
    result = cluster.query(query)
    return [row for row in result]

def _normalizar_clave(valor: Any) -> str:
    """
    Devuelve siempre una cadena para comparar claves de umbral.
    Trimea y convierte None en cadena vacía.
    """
    if valor in (None, "", "None"):
        return ""
    return str(valor).strip()

def _existe_umbral_con_clave(scope, tipo: str, tipologia: str, velocidad: str, excluir_doc_id: str = None) -> bool:
    """
    Comprueba si existe un documento con la combinación única de clave.
    Se compara en modo case-sensitive, tal y como se persisten los datos.
    """
    query = """
        SELECT META(u).id AS doc_id
        FROM `Maestro_Umbrales` u
        WHERE u.tipo = $tipo
          AND IFNULL(u.tipologia, '') = $tipologia
          AND IFNULL(TOSTRING(u.velocidad), '') = $velocidad
    """
    parametros = {
        "tipo": tipo,
        "tipologia": tipologia,
        "velocidad": velocidad,
    }

    if excluir_doc_id:
        query += " AND META(u).id != $excluir_id"
        parametros["excluir_id"] = excluir_doc_id

    query += " LIMIT 1;"

    resultado = scope.query(query, QueryOptions(named_parameters=parametros))
    return any(resultado)

def existe_umbral_con_clave(cluster, bucket_name, scope_name, tipo: Any, tipologia: Any, velocidad: Any, excluir_doc_id: str = None) -> bool:
    scope = cluster.bucket(bucket_name).scope(scope_name)
    tipo_norm = _normalizar_clave(tipo)
    tipologia_norm = _normalizar_clave(tipologia)
    velocidad_norm = _normalizar_clave(velocidad)
    excluir_id = _normalizar_clave(excluir_doc_id) or None
    return _existe_umbral_con_clave(scope, tipo_norm, tipologia_norm, velocidad_norm, excluir_id)
def crear_umbral(cluster, bucket_name, scope_name, documento):
    """
    Crea un umbral en la colección Maestro_Umbrales con UUID como clave.
    Devuelve el doc_id creado.
    Persistimos los campos tal cual (valores_N* como strings), según formato del cliente.
    """
    scope = cluster.bucket(bucket_name).scope(scope_name)
    tipo = _normalizar_clave(documento.get("tipo"))
    tipologia = _normalizar_clave(documento.get("tipologia"))
    velocidad = _normalizar_clave(documento.get("velocidad"))

    if _existe_umbral_con_clave(scope, tipo, tipologia, velocidad):
        raise DocumentExistsException("duplicate_umbral")

    coll = scope.collection("Maestro_Umbrales")
    from uuid import uuid4
    coll.insert(str(uuid4()), documento)

def actualizar_umbral(cluster, bucket_name: str, scope_name: str, doc_id: str, datos_actualizados: dict) -> None:
    """
    Actualiza (upsert) un umbral existente. Lanza DocumentNotFoundException si no existe.
    """
    scope = cluster.bucket(bucket_name).scope(scope_name)
    coll = scope.collection("Maestro_Umbrales")
    existente = coll.get(doc_id).content_as[dict]  # asegura existencia; si no existe, levanta excepción

    tipo_original = _normalizar_clave(existente.get("tipo"))
    tipologia_original = _normalizar_clave(existente.get("tipologia"))
    velocidad_original = _normalizar_clave(existente.get("velocidad"))

    tipo_post = _normalizar_clave(datos_actualizados.get("tipo"))
    tipologia_post = _normalizar_clave(datos_actualizados.get("tipologia"))
    velocidad_post = _normalizar_clave(datos_actualizados.get("velocidad"))

    if (tipo_post != tipo_original or
            tipologia_post != tipologia_original or
            velocidad_post != velocidad_original):
        raise ValueError("PRIMARY_KEY_IMMUTABLE")

    # Blindamos la clave usando los valores originales almacenados.
    datos_actualizados["tipo"] = existente.get("tipo")
    datos_actualizados["tipologia"] = existente.get("tipologia")
    datos_actualizados["velocidad"] = existente.get("velocidad")

    coll.upsert(doc_id, datos_actualizados)

def eliminar_umbral(cluster, bucket_name: str, scope_name: str, doc_id: str) -> None:
    """
    Elimina un umbral por doc_id. Lanza DocumentNotFoundException si no existe.
    """
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Umbrales")
    coll.remove(doc_id)
