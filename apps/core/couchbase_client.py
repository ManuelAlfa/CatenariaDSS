import os
from datetime import timedelta
from dotenv import load_dotenv
from couchbase.cluster import Cluster
from couchbase.auth import PasswordAuthenticator
from couchbase.exceptions import CouchbaseException
from couchbase.options import ClusterOptions
import time

def connection(nombre_entorno):
    max_retries = 3
    for attempt in range(max_retries):
        try:

            # Cargar el archivo .env correspondiente
            archivo_env = f"{nombre_entorno}.env"
            load_dotenv(dotenv_path=archivo_env)

            endpoint    = os.getenv("CB_ENDPOINT")
            username    = os.getenv("CB_USERNAME")
            password    = os.getenv("CB_PASSWORD")
            bucket_name = os.getenv("CB_BUCKET")
            scope_name  = os.getenv("CB_SCOPE") 

            auth = PasswordAuthenticator(username, password)
            cluster = Cluster.connect(endpoint, ClusterOptions(auth), timeout=timedelta(seconds=30))
            cluster.wait_until_ready(timedelta(seconds=15))
            bucket = cluster.bucket(bucket_name)
            bucket.scope(scope_name)
            return cluster, bucket_name, scope_name
        
        except CouchbaseException as e:
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                # Version original (solo str(e), a veces recorta el detalle real):
                # raise RuntimeError(
                #     f"No se pudo conectar a Couchbase tras {max_retries} intentos: {e}"
                # ) from e
                raise RuntimeError(
                    f"No se pudo conectar a Couchbase tras {max_retries} intentos: "
                    f"{type(e).__name__}: {e!r}"
                ) from e