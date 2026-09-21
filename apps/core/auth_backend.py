from __future__ import annotations

from typing import Any
from datetime import datetime, timezone

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

from functools import lru_cache

from apps.core.couchbase_client import connection


@lru_cache(maxsize=1)
def _cached_connection():
    """Cached Couchbase connection — connects once per process lifetime."""
    return connection("entorno")


def _normalize_role(role: str) -> str:
    r = (role or "").strip().lower()
    if r in {"admin", "administrador", "administrator"}:
        return "administrador"
    if r in {"licitador"}:
        return "licitador"
    if r in {"usuario", "user", "estandar", "estándar", "usuario estándar"}:
        return "usuario"
    return r or "usuario"


# Version original (silenciaba el motivo del fallo):
# def _load_couchbase_user(username: str) -> dict[str, Any] | None:
#     try:
#         cluster, bucket_name, scope_name = _cached_connection()
#         coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
#         doc = coll.get(username).content_as[dict]
#         return doc if isinstance(doc, dict) else None
#     except Exception:
#         return None


def _load_couchbase_user(username: str) -> tuple[dict[str, Any] | None, str | None]:
    """Devuelve (doc, motivo_error). doc es None si no se pudo cargar."""
    try:
        cluster, bucket_name, scope_name = _cached_connection()
        coll = cluster.bucket(bucket_name).scope(scope_name).collection("Maestro_Usuarios_Django")
        doc = coll.get(username).content_as[dict]
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    if not isinstance(doc, dict):
        return None, "El documento no tiene formato de diccionario."
    return doc, None


class _SimpleGroupManager:
    def __init__(self, role: str):
        self._role = role

    def values_list(self, field: str, flat: bool = False):
        if field == "name" and flat:
            return [self._role]
        return []


class _SimplePkField:
    @staticmethod
    def value_to_string(obj) -> str:
        return str(getattr(obj, "pk", ""))


class _SimpleMeta:
    pk = _SimplePkField()


class CouchbaseUser:
    """
    Usuario autenticado sin dependencia de auth_user.
    Compatible con login_required y con la lectura de grupos por nombre.
    """

    def __init__(self, username: str, role: str):
        self.pk = username
        self.id = username
        self.username = username
        self.email = username
        self.is_active = True
        self.is_staff = role == "administrador"
        self.is_superuser = role == "administrador"
        self._role = role
        self.groups = _SimpleGroupManager(role)
        self._meta = _SimpleMeta()

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_username(self) -> str:
        return self.username

    def get_session_auth_hash(self) -> str:
        # Session auth hash is optional for custom users; empty is enough.
        return ""

    def save(self, *args, **kwargs) -> None:
        # Django signal update_last_login calls user.save(update_fields=[...]).
        # In Couchbase-only auth we keep this as a harmless no-op.
        self.last_login = datetime.now(timezone.utc)

    def has_perm(self, perm, obj=None) -> bool:
        _ = perm, obj
        return self.is_superuser

    def has_module_perms(self, app_label) -> bool:
        _ = app_label
        return self.is_superuser


class AnonymousCouchbaseUser:
    is_authenticated = False
    is_anonymous = True
    is_active = False
    is_staff = False
    is_superuser = False
    username = ""
    email = ""

    class _EmptyGroups:
        @staticmethod
        def values_list(field: str, flat: bool = False):
            _ = field, flat
            return []

    groups = _EmptyGroups()

    def get_username(self) -> str:
        return ""

    def has_perm(self, perm, obj=None) -> bool:
        _ = perm, obj
        return False

    def has_module_perms(self, app_label) -> bool:
        _ = app_label
        return False


class CouchbaseUsersBackend(BaseBackend):
    # Version original (sin motivo de fallo, solo devolvía None):
    # def authenticate(self, request, username: str | None = None, password: str | None = None, **kwargs):
    #     if not username or password is None:
    #         return None
    #
    #     username = username.strip()
    #     if not username:
    #         return None
    #
    #     cb_user = _load_couchbase_user(username)
    #     if not cb_user:
    #         return None
    #
    #     stored_hash = str(cb_user.get("password_hash") or "")
    #     if stored_hash:
    #         if not check_password(password, stored_hash):
    #             return None
    #     else:
    #         # Legacy Couchbase docs may still store plain text password.
    #         stored_plain = str(cb_user.get("password") or "")
    #         if not stored_plain or stored_plain != password:
    #             return None
    #
    #     role = _normalize_role(str(cb_user.get("rol") or "usuario"))
    #     return CouchbaseUser(username=username, role=role)

    def authenticate(self, request, username: str | None = None, password: str | None = None, **kwargs):
        def _fail(reason: str):
            if request is not None:
                request.auth_error = reason
            return None

        if not username or password is None:
            return _fail("Falta usuario o contraseña en el formulario.")

        username = username.strip()
        if not username:
            return _fail("El usuario está vacío tras quitar espacios.")

        cb_user, error = _load_couchbase_user(username)
        if cb_user is None:
            return _fail(error or f"No se encontró el documento '{username}' en Maestro_Usuarios_Django.")

        stored_hash = str(cb_user.get("password_hash") or "")
        if stored_hash:
            if not check_password(password, stored_hash):
                return _fail("La contraseña no coincide con el password_hash almacenado.")
        else:
            # Legacy Couchbase docs may still store plain text password.
            stored_plain = str(cb_user.get("password") or "")
            if not stored_plain or stored_plain != password:
                return _fail("No hay password_hash y la contraseña en texto plano no coincide (o está vacía).")

        role = _normalize_role(str(cb_user.get("rol") or "usuario"))
        return CouchbaseUser(username=username, role=role)

    def get_user(self, user_id):
        if not user_id:
            return None
        cb_user, _error = _load_couchbase_user(str(user_id))
        if cb_user is None:
            return None
        role = _normalize_role(str(cb_user.get("rol") or "usuario"))
        return CouchbaseUser(username=str(user_id), role=role)

