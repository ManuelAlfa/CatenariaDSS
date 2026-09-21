from typing import List, Dict, Any

def obtener_personas(cluster, clausula_FROM):
    consulta = f'''
        SELECT 
            META(p).id AS doc_id,
            IFMISSINGORNULL(p.nombre, "") AS nombre,
            IFMISSINGORNULL(p.perfil, "") AS perfil,
            IFMISSINGORNULL(p.codigo, "") AS codigo
        {clausula_FROM}`Maestro_Usuarios` p
        ORDER BY p.nombre
    '''
    resultado = cluster.query(consulta)
    personas = []
    for fila in resultado:
        personas.append({
            "doc_id": fila.get("doc_id", ""),
            "codigo": fila.get("codigo", ""),
            "nombre": fila.get("nombre", ""),
            "perfil": fila.get("perfil", "")
        })
    return personas

def crear_usuario(cluster, bucket_name, scope_name, documento_id, documento):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios")
    coll.insert(documento_id, documento)

def actualizar_usuario(cluster, bucket_name, scope_name, doc_id, datos_actualizados):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios")
    coll.get(doc_id)  # asegúrate de que existe
    coll.upsert(doc_id, datos_actualizados)

def eliminar_usuario(cluster, bucket_name, scope_name, doc_id):
    coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios")
    coll.remove(doc_id)
