import sys
from pathlib import Path
from couchbase.cluster import Cluster
from couchbase.options import ClusterOptions
from couchbase.auth import PasswordAuthenticator
from datetime import timedelta
import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Carga entorno.env (misma fuente que usan settings.py y couchbase_client.py)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "entorno.env")

""" # CONFIGURACIÓN DE COUCHBASE (hardcodeada, ya no se usa)
CB_ENDPOINT = "couchbases://cb.nlylijzw-dnmgmu.cloud.couchbase.com"
CB_USERNAME = "acceso_UAT"
CB_PASSWORD = "_S0lut1an0s:_"
CB_BUCKET = "BBDDPruebas"
CB_SCOPE = "catenarias"

CB_ENDPOINT = "couchbases://cb.rgnmbv9rungu93r.cloud.couchbase.com"
CB_USERNAME = "acceso_prueba"
CB_PASSWORD = "S0lut1an0s:"
CB_BUCKET = "CatenarIA-trial"
CB_SCOPE = "Desa"

# CONFIGURACIÓN DE POSTGRES (hardcodeada, ya no se usa)
PG_USER = "postgres"
PG_PASSWORD = "admin1234"
PG_HOST = "catenaria_postgres"
PG_PORT = "5432"
PG_DB = "catenaria"

PG_USER = "postgres"
PG_PASSWORD = "pepe"
PG_HOST = "localhost"
PG_PORT = "5432"
PG_DB = "catenaria"
"""

# CONFIGURACIÓN DE COUCHBASE Y POSTGRES: ahora se toman de entorno.env
CB_ENDPOINT = os.getenv("CB_ENDPOINT")
CB_USERNAME = os.getenv("CB_USERNAME")
CB_PASSWORD = os.getenv("CB_PASSWORD")
CB_BUCKET = os.getenv("CB_BUCKET")
CB_SCOPE = os.getenv("CB_SCOPE")

# Misma resolución que apps/tramos/services.py: prioriza PG_* (nombres que
# usa el código Django para conectarse) y cae a POSTGRES_* (nombres que usa
# la imagen oficial de Postgres para autoinicializarse) si PG_* no está.
PG_USER = os.getenv("PG_USER") or os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
PG_HOST = os.getenv("PG_HOST") or os.getenv("POSTGRES_HOST")
PG_PORT = os.getenv("PG_PORT") or os.getenv("POSTGRES_PORT")
PG_DB = os.getenv("PG_DB") or os.getenv("PG_DATABASE") or os.getenv("POSTGRES_DB")

_faltantes = [nombre for nombre, valor in [
    ("CB_ENDPOINT", CB_ENDPOINT), ("CB_USERNAME", CB_USERNAME), ("CB_PASSWORD", CB_PASSWORD),
    ("CB_BUCKET", CB_BUCKET), ("CB_SCOPE", CB_SCOPE),
    ("PG_HOST", PG_HOST), ("PG_PORT", PG_PORT), ("PG_USER", PG_USER),
    ("PG_PASSWORD", PG_PASSWORD), ("PG_DB", PG_DB),
] if not valor]
if _faltantes:
    print(f"CRÍTICO: faltan variables en entorno.env: {', '.join(_faltantes)}", file=sys.stderr)
    sys.exit(1)

COLECCIONES = [
    "Maestro_Tramos",
    "Maestro_Umbrales",
    "Medicion_Individual",
    "Incidencias",
]
NOMBRE_CARPETA = "db_datos"
os.makedirs(NOMBRE_CARPETA, exist_ok=True)

ESQUEMA = "mediciones"

# Cadena de conexión a la base de datos de mantenimiento "postgres", que
# siempre existe en cualquier instancia de PostgreSQL. La usamos solo para
# comprobar si nuestra base de datos de destino existe y, si no, crearla.
cadena_conexion_admin = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/postgres"

# Cadena de conexión a la base de datos real del proyecto.
cadena_conexion = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"


def asegurar_base_de_datos() -> None:
    """
    Crea la base de datos PG_DB si todavía no existe.

    CREATE DATABASE no puede ejecutarse dentro de una transacción, así que
    forzamos isolation_level="AUTOCOMMIT" en el engine de mantenimiento.
    """
    admin_engine = create_engine(cadena_conexion_admin, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :nombre"),
                {"nombre": PG_DB},
            ).first()
            if existe:
                print(f"La base de datos '{PG_DB}' ya existe.\n")
            else:
                print(f"La base de datos '{PG_DB}' no existe. Creándola...")
                # El nombre de la BD no se puede parametrizar con placeholders,
                # así que se valida antes de interpolarlo en el SQL.
                if not PG_DB.isidentifier():
                    raise ValueError(f"Nombre de base de datos no válido: {PG_DB!r}")
                conn.execute(text(f'CREATE DATABASE "{PG_DB}"'))
                print(f"Base de datos '{PG_DB}' creada correctamente.\n")
    except Exception as e:
        print(f"CRÍTICO: No se pudo comprobar/crear la base de datos '{PG_DB}'. Detalles: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        admin_engine.dispose()


def asegurar_esquema(pg_engine) -> None:
    """Crea el esquema ESQUEMA dentro de PG_DB si todavía no existe."""
    try:
        with pg_engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{ESQUEMA}"'))
        print(f"Esquema '{ESQUEMA}' listo.\n")
    except Exception as e:
        print(f"CRÍTICO: No se pudo crear el esquema '{ESQUEMA}'. Detalles: {e}", file=sys.stderr)
        sys.exit(1)


asegurar_base_de_datos()

pg_engine = create_engine(cadena_conexion)

try:
    print("Conectando a PostgreSQL...")
    with pg_engine.connect() as conn:

        conn.execute(text("SELECT 1"))
        print("Conexión a PostgreSQL exitosa\n")
except Exception as e:
    print(f"CRÍTICO: No se pudo conectar a PostgreSQL. Detalles: {e}", file=sys.stderr)
    sys.exit(1)

asegurar_esquema(pg_engine)


try:
    print("Conectando a Couchbase...")
    auth = PasswordAuthenticator(CB_USERNAME, CB_PASSWORD)
    cluster = Cluster(CB_ENDPOINT, ClusterOptions(auth))
    cluster.wait_until_ready(timedelta(seconds=60))
    print("Conexión a Couchbase exitosa\n")
except Exception as e:
    print(f"CRÍTICO: No se pudo conectar a Couchbase. Detalles: {e}", file=sys.stderr)
    sys.exit(1) 

for coleccion in COLECCIONES:
    print(f"Procesando la colección: {coleccion}...")
    
    query = f"SELECT * FROM `{CB_BUCKET}`.`{CB_SCOPE}`.`{coleccion}`"
    
    try:
        resultado = cluster.query(query)
        datos = [fila[coleccion] for fila in resultado]
        
        if datos:
            df = pd.DataFrame(datos)
            ruta_archivo = os.path.join(NOMBRE_CARPETA, f"{coleccion}.csv")

            df.to_csv(ruta_archivo, index=False, sep=",")
            print(f"Ha sido guardado en CSV: {ruta_archivo}")
            
            nombre_tabla = coleccion.lower() 
            df.to_sql(nombre_tabla, pg_engine, schema='mediciones', if_exists='replace', index=False)
            print(f"Datos guardados en la tabla PostgreSQL: {nombre_tabla}\n")
            
        else:
            print(f"La colección '{coleccion}' existe pero está vacía.\n")
            
    except Exception as e:
        print(f"Error crítico al exportar la colección '{coleccion}': {e}\n", file=sys.stderr)
        sys.exit(1)
