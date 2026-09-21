"""
Script que envía a Power Automate el catálogo de operaciones de
catenaria (estructura parte → grupos → subgrupos), descargado desde
Couchbase (colección Maestro_Operaciones).

Hace UNA SOLA llamada con todo el catálogo. El flujo de Power Automate
se encarga de hacer upsert en la tabla OPERACIONES2 (sin duplicar).

Uso:
    python m.py                              # Envío real a Power Automate
    python m.py --url http://localhost:5000  # Contra mock local
    python m.py --dry-run                    # Solo muestra el payload
    python m.py --id 5                       # idActuacion personalizado (por defecto "1")
"""

import os
import sys
import requests
import json
import argparse

from couchbase.exceptions import CouchbaseException

# Permite importar apps.core.couchbase_client sin depender del cwd desde
# el que se lance este script (p. ej. como subproceso de Django).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apps.core.couchbase_client import connection

# ── Configuración Couchbase ─────────────────────────────────────────────
# La conexión (endpoint/usuario/bucket/scope) se toma de entorno.env a
# través de connection("entorno"), igual que el resto de la aplicación,
# en vez de credenciales hardcodeadas contra otro clúster/bucket.

COLECCIONES = ["Maestro_Tramos", "Maestro_Umbrales", "Medicion_Individual","Incidencias"]



COL_OPERACIONES = "Maestro_Operaciones"

# ── URL del flujo de Power Automate ─────────────────────────────────────
POWER_AUTOMATE_URL = (
    "https://d92b6a428cf3e7f0bc99f33e606700.4c.environment.api.powerplatform.com:443"
    "/powerautomate/automations/direct/workflows"
    "/a563c722f1254f2691e815cae8401844/triggers/manual/paths/invoke"
    "?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&si"
    "g=J34KVmmPoNQ0mpj7dKXl_l01Td9c7qmJ-ozmHhUnLUs"
)

TIMEOUT = 60


def conectar_couchbase():
    return connection("entorno")


def obtener_operaciones(cluster, bucket_name, scope_name):
    """
    Lee Maestro_Operaciones y devuelve la lista en el formato:
    [ { "parte": "...", "grupos": [...] } ]
    """
    query = (
        f"SELECT ops.* "
        f"FROM `{bucket_name}`.`{scope_name}`.`{COL_OPERACIONES}` AS ops"
    )
    resultados = []
    for fila in cluster.query(query):
        doc = fila.get("Maestro_Operaciones", fila)
        resultados.append({
            "parte": doc["parte"],
            "grupos": doc["grupos"]
        })
    return resultados


def enviar(url, payload):
    """Envía el payload a Power Automate y muestra la respuesta."""
    try:
        r = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        print(f"\n📡 Respuesta del servidor:")
        print(f"   HTTP {r.status_code}")
        if r.text:
            print(f"   Body: {r.text[:300]}")

        if r.status_code in (200, 202):
            print("\n✅ Enviado correctamente")
            return True
        else:
            print("\n❌ Error en el envío")
            return False

    except requests.exceptions.Timeout:
        print("\n⏰ Timeout - el servidor tardó demasiado")
    except requests.exceptions.ConnectionError:
        print("\n🔌 Error de conexión - ¿el servidor está corriendo?")
    except requests.exceptions.RequestException as e:
        print(f"\n🚨 Error: {e}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Envía el catálogo de operaciones a Power Automate"
    )
    parser.add_argument("--url", help="URL del endpoint")
    parser.add_argument("--id", default="1", help="idActuacion (por defecto: '1')")
    parser.add_argument("--dry-run", action="store_true", help="No envía, solo muestra")
    args = parser.parse_args()

    url = args.url or POWER_AUTOMATE_URL

    # ── 1. Conectar ──
    print("🔗 Conectando a Couchbase...")
    try:
        cluster, bucket_name, scope_name = conectar_couchbase()
    except (CouchbaseException, RuntimeError) as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    print("✅ Conexión exitosa")

    # ── 2. Leer Maestro_Operaciones ──
    print(f"\n📥 Leyendo {COL_OPERACIONES}...")
    try:
        datos = obtener_operaciones(cluster, bucket_name, scope_name)
    except CouchbaseException as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    n_grupos = sum(len(p["grupos"]) for p in datos)
    n_subs = sum(len(g["subgrupos"]) for p in datos for g in p["grupos"])
    print(f"✅ {len(datos)} partes, {n_grupos} grupos, {n_subs} subgrupos")

    # ── 3. Construir payload ──
    payload = {
        "idActuacion": args.id,
        "datos": datos
    }

    destino = "mock local" if "localhost" in url or "127.0.0.1" in url else "Power Automate"
    print(f"\n{'=' * 60}")
    print(f"📦 Payload listo para enviar:")
    print(f"   idActuacion: {args.id}")
    print(f"   partes: {len(datos)}")
    for p in datos:
        ng = len(p["grupos"])
        ns = sum(len(g["subgrupos"]) for g in p["grupos"])
        print(f"     · {p['parte']}: {ng} grupos, {ns} subgrupos")
    print(f"   Destino: {destino}")
    print(f"{'=' * 60}")

    # ── 4. Enviar (o dry-run) ──
    if args.dry_run:
        print("\n📋 DRY RUN - Payload completo:\n")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("\n✅ Dry run completado. No se envió nada.\n")
    else:
        print(f"\n⏳ Enviando POST a {url[:60]}{'...' if len(url) > 60 else ''}")
        enviar(url, payload)


if __name__ == "__main__":
    main()
