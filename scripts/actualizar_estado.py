#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from datetime import datetime

# Permite ejecutar este script standalone (python scripts/actualizar_estado.py)
# añadiendo la raíz del proyecto al sys.path para resolver `apps.core.*`.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from apps.core.couchbase_client import connection
from couchbase.options import QueryOptions
from couchbase.exceptions import CouchbaseException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("actualizar_estado.log"), logging.StreamHandler()]
)


def procesar_actuaciones(usuario: str, entorno: str = "entorno"):

    logging.info("Conectando a Couchbase...")

    try:
        cluster, bucket_name, scope_name = connection(entorno)
        bucket = cluster.bucket(bucket_name)
        scope = bucket.scope(scope_name)
    except Exception as e:
        logging.error(f"❌ Error al conectar: {e}")
        return

    logging.info("Conexión correcta.")

    # Obtener actuaciones con estado R
    query_act = f"""
        SELECT META(a).id AS doc_id, a.*
        FROM `{bucket_name}`.`{scope_name}`.`Actuaciones` a
        WHERE a.estado = "R";
    """

    try:
        actuaciones = list(cluster.query(query_act).rows())
    except Exception as e:
        logging.error(f"❌ Error consultando Actuaciones: {e}")
        return

    if not actuaciones:
        logging.info("No hay actuaciones con estado R.")
        return

    logging.info(f"Encontradas {len(actuaciones)} actuaciones para procesar.")

    for act in actuaciones:
        try:
            doc_id = act["doc_id"]
            id_tramo = act.get("id_tramo")
            id_via = act.get("id_via")
            fecha = act.get("fecha")

            logging.info(f"Procesando {doc_id} ...")

            if not id_tramo or not id_via or not fecha:
                logging.warning("⚠ Falta id_tramo, id_via o fecha. Saltando...")
                continue

            # --- obtener mediciones ---
            query_med = f"""
                SELECT m.pto_km
                FROM `{bucket_name}`.`{scope_name}`.`Medicion_Individual` m
                WHERE m.id_tramo = $id_tramo
                AND   m.id_via   = $id_via
                AND   m.fecha    = $fecha;
            """

            mediciones = list(cluster.query(
                query_med,
                QueryOptions(named_parameters={
                    "id_tramo": id_tramo,
                    "id_via": id_via,
                    "fecha": fecha
                })
            ).rows())

            if not mediciones:
                logging.warning("Sin mediciones, no se actualiza.")
                continue

            pto_min = min(m["pto_km"] for m in mediciones)
            pto_max = max(m["pto_km"] for m in mediciones)
            num_km = float(pto_max - pto_min)

            logging.info(f"  pto_km_min={pto_min}, pto_km_max={pto_max}, num_km={num_km}")

            # --- Actualizar actuación via UPDATE N1QL ---
            query_update = """
                UPDATE `Actuaciones`
                SET num_km     = $num_km,
                    estado      = "P",
                    updated_at  = $updated_at,
                    updated_by  = $updated_by
                WHERE META().id = $doc_id
                RETURNING META().id AS actualizado;
            """

            result = list(cluster.query(
                query_update,
                QueryOptions(
                    named_parameters={
                        "num_km": num_km,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_by": usuario,
                        "doc_id": doc_id
                    },
                    query_context=f"{bucket_name}.{scope_name}"
                )
            ).rows())
            logging.info(" Actuación actualizada.")

        except Exception as e:
            logging.error(f"❌ Error en {doc_id}: {e}")

    logging.info("Proceso finalizado.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/actualizar_estado.py <usuario> [entorno]")
        sys.exit(1)

    usuario = sys.argv[1]
    entorno = sys.argv[2] if len(sys.argv) >= 3 else "entorno"

    procesar_actuaciones(usuario, entorno)
