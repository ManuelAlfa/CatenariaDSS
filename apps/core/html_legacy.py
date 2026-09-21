from typing import Iterable, Optional, Sequence, Mapping
from typing import Optional, List, Dict, Any  

# ============================================================
#   NAV ÚNICO REUTILIZABLE
# ============================================================
# Definido aquí como constante para que TODAS las páginas usen el mismo nav.
# Si necesitas cambiar el nav de la app, edítalo SOLO aquí.
# Inyección:
#   - en f-strings:        usa {NAV_HTML}
#   - en strings normales: cierra el string, concatena NAV_HTML y reabre.
NAV_HTML = """
<nav class="navbar navbar-expand-lg navbar-light bg-primary py-2">
  <div class="container-fluid d-flex flex-wrap align-items-center gap-2">

    <a class="navbar-brand text-white d-flex align-items-center m-0 me-2" href="/entrada">
      <img src="/img/logo.png" alt="logo" width="80" height="40">
    </a>

    <button class="navbar-toggler order-1 ms-auto" type="button"
            data-bs-toggle="collapse" data-bs-target="#navMainPrincipal"
            aria-controls="navMainPrincipal" aria-expanded="false"
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>

    <div class="collapse navbar-collapse order-3 order-lg-2 flex-grow-1 justify-content-lg-center"
         id="navMainPrincipal">
      <ul class="navbar-nav gap-lg-3 my-2 my-lg-0">
        <li class="nav-item"><a class="nav-link text-white" href="/entrada?from=nav">Inicio</a></li>
        <li class="nav-item"><a class="nav-link text-white" href="/configuracion">Configuración</a></li>
        <li class="nav-item"><a class="nav-link text-white" href="/dss">DSS</a></li>
        <li class="nav-item"><a class="nav-link text-white" href="/kpi-kgi">Sistemas de KPI / KGI</a></li>
        <li class="nav-item"><a class="nav-link text-white" href="/alertas">Alertas</a></li>
      </ul>
    </div>

    <div class="d-flex align-items-center gap-2 order-2 order-lg-3 ms-lg-auto flex-shrink-0">
      <img src="/img/solutia.png" alt="solutia" style="height:36px;width:auto;">
      <a href="/logout" class="btn btn-outline-light btn-sm">Cerrar sesión</a>
    </div>

  </div>
</nav>
<style>
  /* Estilos específicos del nav unificado */
  .navbar .nav-link { transition: transform 0.2s linear; white-space: nowrap; }
  .navbar .nav-link:hover { transform: scale(1.06); }
  /* En pantallas <lg, el menú colapsado ocupa toda la fila para que no se monte
     con el logo derecho ni con la imagen de Solutia. */
  @media (max-width: 991.98px) {
    .navbar #navMainPrincipal { width: 100%; }
    .navbar #navMainPrincipal .navbar-nav { gap: .25rem; }
  }
</style>
"""


SCRIPT_GLOBAL_SYNC = """
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
<script>
let intervaloSync = null;

document.addEventListener("DOMContentLoaded", function() {
    if (sessionStorage.getItem("sincronizando") === "true") {
        restaurarEstadoVisualCargando();
        iniciarReloj();
    }
});

function iniciarSincronizacion() {
    sessionStorage.setItem("sincronizando", "true");
    restaurarEstadoVisualCargando();
    fetch('/ejecutar-script', { method: 'POST' }).catch(e => console.error("Error al arrancar:", e));
    iniciarReloj();
}

function restaurarEstadoVisualCargando() {
    let btn = document.getElementById("btn-sync");
    let texto = document.getElementById("texto-estado");
    if(btn && texto) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Trabajando...';
        texto.style.display = "block";
        texto.className = "text-info mt-2 small fw-bold";
        texto.innerText = "Sincronizando iniciada... Te avisaremos cuando haya terminado.";
    }
}

function iniciarReloj() {
    if (!intervaloSync) {
        preguntarComoVa();
        intervaloSync = setInterval(preguntarComoVa, 3000);
    }
}

function preguntarComoVa() {
    fetch('/estado-sync')
    .then(respuesta => respuesta.json())
    .then(datos => {
        if (datos.trabajando === false) {
            if (intervaloSync) {
                clearInterval(intervaloSync);
                intervaloSync = null;
            }
            sessionStorage.removeItem("sincronizando");
            
            let btn = document.getElementById("btn-sync");
            let texto = document.getElementById("texto-estado");
            
            if (btn && texto) {
                btn.disabled = false;
                btn.innerHTML = 'Ejecutar Sincronización';
                if (datos.mensaje !== "") {
                    texto.style.display = "block";
                    texto.innerText = datos.mensaje;
                    texto.className = datos.mensaje.includes("éxito") ? "text-success fw-bold mt-2" : "text-danger fw-bold mt-2";
                } else {
                    texto.style.display = "none";
                }
            }
            
            if (datos.mensaje !== "") {
                fetch('/limpiar-estado-sync', { method: 'POST' });
                mostrarNotificacionGlobal(datos.mensaje);
            }
        }
    })
    .catch(error => console.log("Esperando respuesta...", error));
}

function mostrarNotificacionGlobal(mensaje) {
    let esExito = mensaje.toLowerCase().includes("éxito");
    if (typeof Swal === 'undefined') {
        alert("Aviso:\\n" + mensaje);
        return;
    }
    Swal.fire({
        title: esExito ? '¡Sincronización Completada!' : 'Aviso',
        text: mensaje,
        icon: esExito ? 'success' : 'info',
        confirmButtonText: 'Genial',
        confirmButtonColor: '#0d6efd',
        timer: 5000,
        timerProgressBar: true
    });
}
</script>
"""



def page_login() -> str:
    
    html = ''' <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Login</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
                <link rel="shortcut icon" href="img/logo.png" type="image/x-icon">
            </head>
            <body class="bg-light">

                        <nav class="navbar navbar-expand-lg navbar-light bg-primary">
              <div class="container-fluid flex-wrap">
                <a class="navbar-brand text-white" href="/entrada">
                  <img src="/img/logo.png" alt="logo" width="80" height="40">
                </a>
                <div class="me-auto"></div>
                <div class="d-flex align-items-center gap-2 ms-lg-2">
                  <img src="/img/solutia.png" alt="solutia" style="height:40px;width:auto;">
                </div>
              </div>
            </nav>

                <div class="container d-flex justify-content-center align-items-center min-vh-100">
                    <div class="row justify-content-center w-100">
                        <div class="col-md-6 col-lg-4">
                            <div class="card border-0 rounded">
                                <div class="card-body">
                                    <h1 class="text-center text-primary mb-4">Identificación del usuario</h1>
                                    <div class="text-center mb-4">
                                        <img src="img/logo.png" alt="logo" class="img-fluid" style="max-width: 220px;">
                                    </div>
                                    <form method="post" action="/login">
                                        <div class="mb-3">
                                            <label for="usuario" class="form-label">Usuario</label>
                                            <input type="text" class="form-control" id="usuario" name="usuario" required>
                                        </div>
                                        <div class="mb-3">
                                            <label for="contraseña" class="form-label">Contraseña</label>
                                            <input type="password" class="form-control" id="contraseña" name="contraseña" required>
                                        </div>
                                        <button type="submit" class="btn btn-primary w-100">Validar</button>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
            </body>
            </html>'''
            
    return html.replace(b'</body>', SCRIPT_GLOBAL_SYNC.encode('utf-8') + b'\n</body>') if isinstance(html, bytes) else html.replace('</body>', SCRIPT_GLOBAL_SYNC + '\n</body>')


def page_configuracion(error_message: Optional[str] = None) -> str:

    alert = ""
    if error_message:
        alert = f'''<div class="alert alert-danger alert-dismissible fade show mt-3" role="alert">
            {error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>'''

    html = ''' 
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Configuracion</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
                
                <link rel="shortcut icon" href="img/logo.png" type="image/x-icon">
                <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
            </head>
            <style>
                .nav-link:hover {
                    transform: scale(1.1);
                    transition: transform 0.3s linear;
                }

                .btn-primary:hover {
                    background-color: #004494;
                    border-color: #004494;
                }

                .card:hover {
                    transform: scale(1.02);
                    transition: transform 0.3s linear;
                    box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
                }
                    .volver-btn {
                        transition: background-color 0.3s ease, transform 0.3s ease;
                    }

                    .volver-btn:hover {
                        background-color: #004c99; /* un azul más oscuro */
                        transform: scale(1.05);
                    }
            </style>

            <body class="bg-light">

                        ''' + NAV_HTML + '''

            <div class="container py-5">
            <div class="d-flex align-items-center gap-2 mb-4">
              <span style="width:120px"></span>
              <h1 class="h1 text-center mb-0 flex-grow-1"> Elige una opción </h1>
              <a href="/entrada" class="btn btn-primary btn-sm volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
            </div>
                <div class="row justify-content-center">
                    <!-- Tarjeta Operaciones -->
                    <div class="col-md-4 mb-4">
                       <div class="card h-100 text-center border-0 shadow">
                        <div class="card-body d-flex flex-column">
                            <i class="bi bi-clipboard-check display-4 text-primary mb-3"></i>
                            <h5 class="card-title">Operaciones</h5>
                            <p class="card-text">Gestiona el maestro de operaciones de la red de catenaria.</p>
                            <a href="/operaciones" class="btn btn-primary w-100 mt-auto">Ir a Operaciones</a>
                        </div>
                    </div>
                    </div>

                    <!-- Tarjeta Tramos -->
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 text-center border-0 shadow">
                            <div class="card-body d-flex flex-column">
                                <i class="bi bi-signpost-2-fill display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Tramos</h5>
                                <p class="card-text">Gestiona y visualiza los tramos de la red de catenaria.</p>
                                <a href="/tramos" class="btn btn-primary w-100 mt-auto">Ir a Tramos</a>
                            </div>
                        </div>
                    </div>

                    <!-- Tarjeta Umbrales -->
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 text-center border-0 shadow">
                            <div class="card-body d-flex flex-column">
                                <i class="bi bi-sliders2-vertical display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Umbrales</h5>
                                <p class="card-text">Gestiona y visualiza los umbrales de la red de catenaria.</p>
                                <a href="/umbrales" class="btn btn-primary w-100 mt-auto">Ir a Umbrales</a>
                            </div>
                        </div>
                    </div>

                    <!-- Tarjeta Usuarios -->
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 text-center border-0 shadow">
                            <div class="card-body d-flex flex-column">
                                <i class="bi bi-people-fill display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Usuarios</h5>
                                <p class="card-text">Administra los usuarios del sistema y sus permisos.</p>
                                <a href="/usuarios" class="btn btn-primary w-100 mt-auto">Ir a Usuarios</a>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4 mb-4">
                        <div class="card h-100 text-center border-0 shadow">
                            <div class="card-body d-flex flex-column">
                                <i class="bi bi-cloud-arrow-down display-4 text-primary mb-3"></i>
                                <h5 class="card-title">Sincronizar BBDD</h5>
                                <p class="card-text">Extrae los últimos datos de Couchbase en segundo plano.</p>
                                
                                <button id="btn-sync" class="btn btn-primary w-100 mt-auto" onclick="iniciarSincronizacion()">
                                    Ejecutar Sincronización
                                </button>
                                
                                <p id="texto-estado" class="mt-2 small" style="display: none;"></p>
                            </div>
                        </div>
                    </div>
                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
            </body>
            </html>'''

    return html.replace(b'</body>', SCRIPT_GLOBAL_SYNC.encode('utf-8') + b'\n</body>') if isinstance(html, bytes) else html.replace('</body>', SCRIPT_GLOBAL_SYNC + '\n</body>')


def page_usuarios(
    personas: Sequence[Mapping[str, str]],
    mensaje_html: str = "",
    query_params: Optional[Mapping[str, Sequence[str]]] = None,
    usuarios_acceso: Optional[Sequence[Mapping[str, str]]] = None,
) -> str:
    
    query_params = query_params or {}
    buscar_id = query_params.get('buscar_id', [''])[0].strip() if query_params else ""

    mensaje_busqueda = ""
    if buscar_id:
        personas_filtradas = [
            p for p in personas
            if buscar_id.lower() in str(p.get("doc_id", "")).lower()
        ]
        if personas_filtradas:
            personas = personas_filtradas
            mensaje_busqueda = f'''
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                Se encontraron {len(personas)} resultado(s) para <strong>{buscar_id}</strong>.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''
        else:
            mensaje_busqueda = f'''
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                No se encontraron usuarios con el código <strong>{buscar_id}</strong>.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''

    if 'success' in query_params:
        mensaje_html = f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            {query_params["success"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''
    elif 'error' in query_params:
        mensaje_html = f'''
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            {query_params["error"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    usuarios_acceso = usuarios_acceso or []

    filas_html = ""
    for persona in personas:
        doc_id = persona.get("doc_id", "")
        codigo = persona.get("codigo", "")
        nombre = persona.get("nombre", "")
        perfil = persona.get("perfil", "")

        filas_html += f'''
        <tr>
            <td>{codigo}</td>
            <td>{nombre}</td>
            <td>
                <!-- Botón Editar con Modal -->
                <button type="button" class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#editarModal{doc_id}">
                    <i class="bi bi-pencil-fill"></i>
                </button>

                <!-- Botón Eliminar con Modal -->
                <button type="button" class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#eliminarModal{doc_id}">
                    <i class="bi bi-trash-fill"></i>
                </button>

                <!-- Modal Editar -->
                <div class="modal fade" id="editarModal{doc_id}" tabindex="-1" aria-labelledby="editarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editarModalLabel{doc_id}">Editar Usuario no humano</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <form action="/usuarios/{doc_id}/editar" method="POST">
                                <div class="modal-body">
                                    <div class="mb-3">
                                        <label for="nombre{doc_id}" class="form-label">Nombre</label>
                                        <input type="text" class="form-control" id="nombre{doc_id}" name="nombre" value="{nombre}" required>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                    <button type="submit" class="btn btn-primary">Guardar Cambios</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>

                <!-- Modal Eliminar -->
                <div class="modal fade" id="eliminarModal{doc_id}" tabindex="-1" aria-labelledby="eliminarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="eliminarModalLabel{doc_id}">Confirmar Eliminación</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ¿Estás seguro de que deseas eliminar al usuario <span class="fw-bold">{nombre}</span>?
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <form action="/usuarios/{doc_id}/eliminar" method="POST" style="display: inline;">
                                    <button type="submit" class="btn btn-danger">Eliminar</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </td>
        </tr>
        '''

    # Si no hay filas (lista vacía), muestra fila "Sin resultados"
    if not filas_html.strip():
        filas_html = '<tr><td colspan="3" class="text-center text-muted">Sin resultados</td></tr>'

    filas_acceso_html = ""
    for ua in usuarios_acceso:
        doc_id = ua.get("doc_id", "")
        usuario = ua.get("usuario", "")
        rol = ua.get("rol", "")
        fecha_creacion = ua.get("fecha_creacion", "")
        filas_acceso_html += f"""
        <tr>
            <td>{usuario}</td>
            <td>{rol}</td>
            <td>{fecha_creacion}</td>
            <td>
                <button type="button" class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#editarAccesoModal{doc_id}">
                    <i class="bi bi-pencil-fill"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#eliminarAccesoModal{doc_id}">
                    <i class="bi bi-trash-fill"></i>
                </button>

                <div class="modal fade" id="editarAccesoModal{doc_id}" tabindex="-1" aria-labelledby="editarAccesoModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editarAccesoModalLabel{doc_id}">Editar acceso a la app</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <form action="/usuarios/acceso/{doc_id}/editar" method="POST">
                                <div class="modal-body">
                                    <div class="mb-3">
                                        <label for="accesoUsuarioEditar{doc_id}" class="form-label">Usuario</label>
                                        <input type="text" class="form-control" id="accesoUsuarioEditar{doc_id}" name="usuario" value="{usuario}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="accesoRolEditar{doc_id}" class="form-label">Rol</label>
                                        <select class="form-select" id="accesoRolEditar{doc_id}" name="rol" required>
                                            <option value="administrador" {'selected' if rol == 'administrador' else ''}>administrador</option>
                                            <option value="licitador" {'selected' if rol == 'licitador' else ''}>licitador</option>
                                            <option value="usuario" {'selected' if rol == 'usuario' else ''}>usuario</option>
                                        </select>
                                    </div>
                                    <div class="alert alert-secondary py-2 mb-0 small">
                                        La contraseña no se modifica desde este apartado.
                                    </div>
                                </div>
                                <div class="modal-footer d-flex justify-content-between">
                                    <button type="button" class="btn btn-warning btn-sm"
                                        onclick="resetPasswordAcceso('{doc_id}')">
                                        <i class="bi bi-key-fill me-1"></i>Restablecer contraseña
                                    </button>
                                    <div class="d-flex gap-2">
                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                        <button type="submit" class="btn btn-primary">Guardar cambios</button>
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>

                <div class="modal fade" id="eliminarAccesoModal{doc_id}" tabindex="-1" aria-labelledby="eliminarAccesoModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="eliminarAccesoModalLabel{doc_id}">Confirmar baja</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                ¿Dar de baja al usuario de acceso <span class="fw-bold">{usuario}</span>?
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <form action="/usuarios/acceso/{doc_id}/eliminar" method="POST" style="display: inline;">
                                    <button type="submit" class="btn btn-danger">Dar de baja</button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </td>
        </tr>
        """
    if not filas_acceso_html.strip():
        filas_acceso_html = '<tr><td colspan="4" class="text-center text-muted">Sin resultados</td></tr>'

    # Documento completo: devuelve **str** (sin .encode(...))
    html_response = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Usuarios</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
        <link rel="shortcut icon" href="img/logo.png" type="image/x-icon">
        <style>
            .nav-link {{ transition: transform 0.3s ease, color 0.3s ease; }}
            .nav-link:hover {{ transform: scale(1.1); }}
            .btn-primary:hover, .btn-success:hover {{
                transform: scale(1.05);
                transition: transform 0.3s ease, background-color 0.3s ease;
                box-shadow: 0 0.3rem 0.6rem rgba(0,0,0,0.2);
            }}
            .btn-outline-light:hover {{ background-color: white; color: #0d6efd; transform: scale(1.05); }}
            .card, .table {{ animation: fadeInUp 0.6s ease; }}
            .card:hover {{ transform: scale(1.02); transition: transform 0.3s ease, box-shadow 0.3s ease; box-shadow: 0 0.7rem 1.5rem rgba(0,0,0,0.15); }}
            .volver-btn {{ transition: all 0.3s ease; }}
            .volver-btn:hover {{ background-color: #004c99; transform: scale(1.08); box-shadow: 0 0.3rem 1rem rgba(0,0,0,0.3); }}
            .modal.fade .modal-dialog {{ transform: translateY(-50px); opacity: 0; transition: all 0.4s ease-in-out; }}
            .modal.fade.show .modal-dialog {{ transform: translateY(0); opacity: 1; }}
        </style>
        <script>
            if (window.history.replaceState) {{
                window.history.replaceState(null, null, window.location.pathname);
            }}
        </script>
    </head>
    <body class="bg-light">
                {NAV_HTML}

        <div class="container py-5">
            {mensaje_html}
            {mensaje_busqueda}
            <h1 class="h1 text-center mb-3"><i class="bi bi-people-fill"></i> Usuarios</h1>

            <ul class="nav nav-tabs mb-3" id="usuariosTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="tab-acceso-tab" data-bs-toggle="tab" data-bs-target="#tab-acceso" type="button" role="tab" aria-controls="tab-acceso" aria-selected="true">
                        Usuarios
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="tab-usuarios-tab" data-bs-toggle="tab" data-bs-target="#tab-usuarios" type="button" role="tab" aria-controls="tab-usuarios" aria-selected="false">
                        Usuarios no humanos: dresinas
                    </button>
                </li>
            </ul>

            <div class="tab-content" id="usuariosTabsContent">
                <div class="tab-pane fade" id="tab-usuarios" role="tabpanel" aria-labelledby="tab-usuarios-tab">
                    <div class="mb-4 d-flex justify-content-between">
                        <div class="ms-3">
                            <form class="row g-3 mb-1" method="GET" action="/usuarios">
                                <div class="col-auto">
                                    <input type="text" class="form-control border border-secondary" name="buscar_id" placeholder="Buscar por Código" value="{buscar_id}">
                                </div>
                                <div class="col-auto">
                                    <button type="submit" class="btn btn-outline-secondary mb-3">
                                        <i class="bi bi-search"></i> Buscar
                                    </button>
                                </div>
                            </form>
                        </div>
                        <div class="me-3">
                            <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#nuevoUsuarioModal">
                                <i class="bi bi-plus-lg"></i> Crear dresina
                            </button>
                        </div>
                    </div>

                    <div class="container">
                        <!-- Botón Volver encima de la tabla, a la derecha -->
                        <div class="d-flex justify-content-end mb-2">
                            <a href="/configuracion" class="btn btn-primary btn-sm volver-btn">
                                <i class="bi bi-arrow-left me-1"></i>Volver Atrás
                            </a>
                        </div>
                        <div class="table-responsive shadow-sm rounded">
                            <table class="table table-hover table-bordered align-middle text-center" id="tablaUsuarios">
                                <thead class="table-primary">
                                    <tr>
                                        <th>Código</th>
                                        <th>Nombre</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="tbodyUsuarios">
                                    {filas_html}
                                </tbody>
                            </table>
                        </div>
                        <!-- Paginación Usuarios -->
                        <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
                            <div class="d-flex align-items-center gap-2">
                                <label for="filasPorPaginaUs" class="form-label mb-0 text-muted small">Mostrar</label>
                                <select id="filasPorPaginaUs" class="form-select form-select-sm" style="width:auto;">
                                    <option value="10" selected>10</option>
                                    <option value="15">15</option>
                                    <option value="20">20</option>
                                    <option value="50">50</option>
                                    <option value="0">Todos</option>
                                </select>
                                <span class="text-muted small">filas por página</span>
                            </div>
                            <div class="d-flex align-items-center gap-3 flex-wrap">
                                <span id="infoPaginaUs" class="text-muted small"></span>
                                <nav><ul class="pagination pagination-sm mb-0" id="paginacionUsuarios"></ul></nav>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="tab-pane fade show active" id="tab-acceso" role="tabpanel" aria-labelledby="tab-acceso-tab">
                    <div class="mb-4 d-flex justify-content-between align-items-center">
                        <h4 class="m-0"><i class="bi bi-shield-lock-fill"></i> Acceso a la Aplicación</h4>
                        <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#nuevoAccesoModal">
                            <i class="bi bi-plus-lg"></i> Nuevo usuario
                        </button>
                    </div>

                    <div class="container mb-4">
                        <!-- Botón Volver encima de la tabla, a la derecha -->
                        <div class="d-flex justify-content-end mb-2">
                            <a href="/configuracion" class="btn btn-primary btn-sm volver-btn">
                                <i class="bi bi-arrow-left me-1"></i>Volver Atrás
                            </a>
                        </div>
                        <div class="table-responsive shadow-sm rounded">
                            <table class="table table-hover table-bordered align-middle text-center" id="tablaAcceso">
                                <thead class="table-primary">
                                    <tr>
                                        <th>Usuario</th>
                                        <th>Rol</th>
                                        <th>Fecha creación</th>
                                        <th>Acciones</th>
                                    </tr>
                                </thead>
                                <tbody id="tbodyAcceso">
                                    {filas_acceso_html}
                                </tbody>
                            </table>
                        </div>
                        <!-- Paginación Acceso -->
                        <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
                            <div class="d-flex align-items-center gap-2">
                                <label for="filasPorPaginaAc" class="form-label mb-0 text-muted small">Mostrar</label>
                                <select id="filasPorPaginaAc" class="form-select form-select-sm" style="width:auto;">
                                    <option value="10" selected>10</option>
                                    <option value="15">15</option>
                                    <option value="20">20</option>
                                    <option value="50">50</option>
                                    <option value="0">Todos</option>
                                </select>
                                <span class="text-muted small">filas por página</span>
                            </div>
                            <div class="d-flex align-items-center gap-3 flex-wrap">
                                <span id="infoPaginaAc" class="text-muted small"></span>
                                <nav><ul class="pagination pagination-sm mb-0" id="paginacionAcceso"></ul></nav>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Modal para nuevo usuario -->
            <div class="modal fade" id="nuevoUsuarioModal" tabindex="-1" aria-labelledby="nuevoUsuarioModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="nuevoUsuarioModalLabel">Nueva dresina</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <form action="/usuarios/nuevo" method="POST">
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="nuevoCodigo" class="form-label">Codigo</label>
                                    <input type="text" class="form-control" id="nuevoCodigo" name="codigo" required>
                                </div>
                                <div class="mb-3">
                                    <label for="nuevoNombre" class="form-label">Nombre</label>
                                    <input type="text" class="form-control" id="nuevoNombre" name="nombre" required>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Guardar</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <div class="modal fade" id="nuevoAccesoModal" tabindex="-1" aria-labelledby="nuevoAccesoModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="nuevoAccesoModalLabel">Nuevo acceso a la app</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <form action="/usuarios/acceso/nuevo" method="POST">
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="accesoUsuario" class="form-label">Usuario (email/login)</label>
                                    <input type="text" class="form-control" id="accesoUsuario" name="usuario" required>
                                </div>
                                <div class="mb-3">
                                    <label for="accesoPassword" class="form-label">Contraseña</label>
                                    <input type="password" class="form-control" id="accesoPassword" name="password" required>
                                </div>
                                <div class="mb-3">
                                    <label for="accesoRol" class="form-label">Rol</label>
                                    <select class="form-select" id="accesoRol" name="rol" required>
                                        <option value="administrador">administrador</option>
                                        <option value="licitador">licitador</option>
                                        <option value="usuario">usuario</option>
                                    </select>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Crear acceso</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        <script>
        function resetPasswordAcceso(docId) {{
            Swal.fire({{
                title: '¿Restablecer contraseña?',
                html: 'Se establecerá la contraseña por defecto: <strong>12345678</strong>',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Sí, restablecer',
                cancelButtonText: 'Cancelar',
                confirmButtonColor: '#ffc107',
                cancelButtonColor: '#6c757d',
            }}).then(function(result) {{
                if (result.isConfirmed) {{
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/usuarios/acceso/' + docId + '/resetear-password';
                    const csrf = document.querySelector('[name=csrfmiddlewaretoken]');
                    if (csrf) form.appendChild(csrf.cloneNode());
                    document.body.appendChild(form);
                    form.submit();
                }}
            }});
        }}
        </script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            function buildPaginator(tbodyId, selectorId, navUlId, infoId) {{
                const tbody = document.getElementById(tbodyId);
                const selector = document.getElementById(selectorId);
                const navUl = document.getElementById(navUlId);
                const info = document.getElementById(infoId);
                if (!tbody || !selector) return;
                let paginaActual = 1;

                function filas() {{ return Array.from(tbody.querySelectorAll('tr')); }}

                function renderPagina() {{
                    const todas = filas();
                    const porPagina = parseInt(selector.value);
                    const total = todas.length;

                    if (porPagina === 0) {{
                        todas.forEach(r => r.style.display = '');
                        navUl.innerHTML = '';
                        info.textContent = total + ' registros';
                        return;
                    }}

                    const totalPaginas = Math.ceil(total / porPagina);
                    if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;
                    const inicio = (paginaActual - 1) * porPagina;
                    const fin = inicio + porPagina;
                    todas.forEach((r, i) => r.style.display = (i >= inicio && i < fin) ? '' : 'none');

                    const desde = total === 0 ? 0 : inicio + 1;
                    const hasta = Math.min(fin, total);
                    info.textContent = `${{desde}}–${{hasta}} de ${{total}} registros`;

                    navUl.innerHTML = '';

                    function addPageBtn(p) {{
                        const li = document.createElement('li');
                        li.className = 'page-item' + (p === paginaActual ? ' active' : '');
                        li.innerHTML = `<a class="page-link" href="#">${{p}}</a>`;
                        li.addEventListener('click', e => {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
                        navUl.appendChild(li);
                    }}
                    function addEllipsis() {{
                        const li = document.createElement('li');
                        li.className = 'page-item disabled';
                        li.innerHTML = '<span class="page-link">…</span>';
                        navUl.appendChild(li);
                    }}

                    const liFirst = document.createElement('li');
                    liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
                    liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
                    liFirst.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
                    navUl.appendChild(liFirst);

                    const liPrev = document.createElement('li');
                    liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
                    liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
                    liPrev.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
                    navUl.appendChild(liPrev);

                    const rango = 2;
                    let desde_p = Math.max(1, paginaActual - rango);
                    let hasta_p = Math.min(totalPaginas, paginaActual + rango);
                    if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
                    if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));

                    if (desde_p > 1) {{ addPageBtn(1); if (desde_p > 2) addEllipsis(); }}
                    for (let p = desde_p; p <= hasta_p; p++) addPageBtn(p);
                    if (hasta_p < totalPaginas) {{ if (hasta_p < totalPaginas - 1) addEllipsis(); addPageBtn(totalPaginas); }}

                    const liNext = document.createElement('li');
                    liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
                    liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
                    liNext.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
                    navUl.appendChild(liNext);

                    const liLast = document.createElement('li');
                    liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
                    liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
                    liLast.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
                    navUl.appendChild(liLast);
                }}

                selector.addEventListener('change', () => {{ paginaActual = 1; renderPagina(); }});
                renderPagina();
            }}

            buildPaginator('tbodyUsuarios', 'filasPorPaginaUs', 'paginacionUsuarios', 'infoPaginaUs');
            buildPaginator('tbodyAcceso',   'filasPorPaginaAc', 'paginacionAcceso',   'infoPaginaAc');
        }});
        </script>
        <script>
            (function() {{
                function enableCrudAjax(actionPrefix) {{
                    document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(function(form) {{
                        var action = form.getAttribute('action') || '';
                        if (!action.startsWith(actionPrefix)) return;
                        form.addEventListener('submit', async function(e) {{
                            e.preventDefault();
                            try {{
                                const data = new FormData(form);
                                const res = await fetch(action, {{
                                    method: 'POST',
                                    body: data,
                                    credentials: 'same-origin',
                                    headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
                                }});
                                const html = await res.text();
                                document.open();
                                document.write(html);
                                document.close();
                            }} catch (err) {{
                                console.error('Error AJAX CRUD usuarios:', err);
                                form.submit();
                            }}
                        }});
                    }});
                }}
                enableCrudAjax('/usuarios/');
            }})();
        </script>
    </body>
    </html>
    '''
    return html_response


def page_tramos(
    tramos: Sequence[Mapping[str, str]],
    mensaje_html: str = "",
    query_params: Optional[Mapping[str, Sequence[str]]] = None
) -> str:
    
    query_params = query_params or {}
    buscar_id = query_params.get('buscar_id', [''])[0].strip() if query_params else ""

    # Guardamos la lista completa para poblar el SELECT (que necesita TODOS
    # los tramos disponibles, no solo los filtrados).
    tramos_originales = list(tramos)

    mensaje_busqueda = ""
    if buscar_id:
        tramos_filtrados = [
            t for t in tramos
            if buscar_id.lower() in str(t.get("id_tramo", "")).lower()
        ]
        if tramos_filtrados:
            tramos = tramos_filtrados
            mensaje_busqueda = f'''
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                Se encontraron {len(tramos)} resultado(s) para <strong>{buscar_id}</strong>.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''
        else:
            mensaje_busqueda = f'''
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                No se encontrarón tramos con el código <strong>{buscar_id}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''
    elif 'buscar_id' in query_params:
        mensaje_busqueda = f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            Se encontraron {len(tramos_originales)} resultado(s) en total.
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    # Mensajes flash (?success= / ?error=) priorizan sobre mensaje_html entrante
    if 'success' in query_params:
        mensaje_html = f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            {query_params["success"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''
    elif 'error' in query_params:
        mensaje_html = f'''
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            {query_params["error"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    # Construcción de filas SIEMPRE tras el posible filtrado
    filas_html = ""
    for t in tramos:
        doc_id        = t.get("doc_id", "")
        id_tramo      = t.get("id_tramo", "")
        id_via        = t.get("id_via", "")
        pto_km_ini    = t.get("pto_km_ini", "")
        pto_km_fin    = t.get("pto_km_fin", "")
        tipologia     = t.get("tipologia", "")
        velocidad_max = t.get("velocidad_max", "")
        descripcion   = t.get("descripcion", "")

        filas_html += f'''
        <tr>
            <td>{id_tramo}</td>
            <td>{id_via}</td>
            <td>{pto_km_ini}</td>
            <td>{pto_km_fin}</td>
            <td>{tipologia}</td>
            <td>{velocidad_max}</td>
            <td>{descripcion}</td>
            <td>
                <!-- Botón Editar -->
                <button type="button" class="btn btn-sm btn-outline-primary me-1"
                        data-bs-toggle="modal" data-bs-target="#editarModal{doc_id}">
                    <i class="bi bi-pencil-fill"></i>
                </button>
                <!-- Botón Eliminar -->
                <button type="button" class="btn btn-sm btn-outline-danger"
                        data-bs-toggle="modal" data-bs-target="#eliminarModal{doc_id}">
                    <i class="bi bi-trash-fill"></i>
                </button>

                <!-- Modal Editar -->
                <div class="modal fade" id="editarModal{doc_id}" tabindex="-1"
                     aria-labelledby="editarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog"><div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="editarModalLabel{doc_id}">Editar Tramo</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <form action="/tramos/{doc_id}/editar" method="POST">
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label for="id_tramo{doc_id}" class="form-label">Id tramo</label>
                                    <input type="text" class="form-control" id="id_tramo{doc_id}" name="id_tramo" value="{id_tramo}">
                                </div>
                                <div class="mb-3">
                                    <label for="id_via{doc_id}" class="form-label">Id vía</label>
                                    <input type="text" class="form-control" id="id_via{doc_id}" name="id_via" value="{id_via}">
                                </div>
                                <div class="mb-3">
                                    <label for="pto_km_ini{doc_id}" class="form-label">Pto km ini</label>
                                    <input type="text" class="form-control" id="pto_km_ini{doc_id}" name="pto_km_ini" value="{pto_km_ini}">
                                </div>
                                <div class="mb-3">
                                    <label for="pto_km_fin{doc_id}" class="form-label">Pto km fin</label>
                                    <input type="text" class="form-control" id="pto_km_fin{doc_id}" name="pto_km_fin" value="{pto_km_fin}">
                                </div>
                                <div class="mb-3">
                                    <label for="tipologia{doc_id}" class="form-label">Tipología</label>
                                    <input type="text" class="form-control" id="tipologia{doc_id}" name="tipologia" value="{tipologia}">
                                </div>
                                <div class="mb-3">
                                    <label for="velocidad_max{doc_id}" class="form-label">Velocidad Máxima</label>
                                    <input type="text" class="form-control" id="velocidad_max{doc_id}" name="velocidad_max" value="{velocidad_max}">
                                </div>
                                <div class="mb-3">
                                    <label for="descripcion{doc_id}" class="form-label">Descripción</label>
                                    <input type="text" class="form-control" id="descripcion{doc_id}" name="descripcion" value="{descripcion}">
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="submit" class="btn btn-primary">Guardar Cambios</button>
                            </div>
                        </form>
                    </div></div>
                </div>

                <!-- Modal Eliminar -->
                <div class="modal fade" id="eliminarModal{doc_id}" tabindex="-1"
                     aria-labelledby="eliminarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog"><div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="eliminarModalLabel{doc_id}">Confirmar Eliminación</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            ¿Estás seguro de que deseas eliminar el tramo
                            <span class="fw-bold">{id_tramo}</span>,
                            vía <span class="fw-bold">{id_via}</span>,
                            pto km inicial <span class="fw-bold">{pto_km_ini}</span> y
                            pto km final <span class="fw-bold">{pto_km_fin}</span>?
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                            <form action="/tramos/{doc_id}/eliminar" method="POST" style="display: inline;">
                                <button type="submit" class="btn btn-danger">Eliminar</button>
                            </form>
                        </div>
                    </div></div>
                </div>
            </td>
        </tr>
        '''
    # Si no hay filas
    if not filas_html.strip():
        filas_html = '<tr><td colspan="8" class="text-center text-muted">Sin resultados</td></tr>'

    # HTML completo (STR, sin encode)
    html_response = f'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tramos</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <link rel="shortcut icon" href="img/logo.png" type="image/x-icon">
    <style>
        .nav-link {{ transition: transform 0.3s ease, color 0.3s ease; }}
        .nav-link:hover {{ transform: scale(1.1); }}
        .btn-primary:hover, .btn-success:hover {{
            transform: scale(1.05);
            transition: transform 0.3s ease, background-color 0.3s ease;
            box-shadow: 0 0.3rem 0.6rem rgba(0, 0, 0, 0.2);
        }}
        .btn-outline-light:hover {{ background-color: white; color: #0d6efd; transform: scale(1.05); }}
        .card, .table {{ animation: fadeInUp 0.6s ease; }}
        .card:hover {{ transform: scale(1.02); transition: transform 0.3s ease, box-shadow 0.3s ease; box-shadow: 0 0.7rem 1.5rem rgba(0,0,0,0.15); }}
        .volver-btn {{ transition: all 0.3s ease; }}
        .volver-btn:hover {{ background-color: #004c99; transform: scale(1.08); box-shadow: 0 0.3rem 1rem rgba(0,0,0,0.3); }}
        .modal.fade .modal-dialog {{ transform: translateY(-50px); opacity: 0; transition: all 0.4s ease-in-out; }}
        .modal.fade.show .modal-dialog {{ transform: translateY(0); opacity: 1; }}
    </style>
    <script>
        if (window.history.replaceState) {{
            window.history.replaceState(null, null, window.location.pathname);
        }}
    </script>
</head>
<body class="bg-light">
        {NAV_HTML}

    <div class="container py-5">
        {mensaje_html}
        {mensaje_busqueda}
        <div class="d-flex align-items-center gap-2 mb-3">
          <span style="width:120px"></span>
          <h1 class="h1 text-center mb-0 flex-grow-1"><i class="bi bi-signpost-2-fill"></i> Tramos</h1>
          <a href="/configuracion" class="btn btn-primary btn-sm volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
        </div>

        <div class="mb-4 d-flex justify-content-between">
            <div class="ms-3">
                <form class="row g-3 mb-1" method="GET" action="/tramos">
                    <div class="col-auto">
                        <select class="form-select border border-secondary" name="buscar_id"
                                onchange="this.form.submit()" style="min-width: 260px;">
                            <option value="">📋 Todos los tramos</option>
                            <option value="" disabled>──────────</option>
                            {''.join(f'<option value="{tid}" {"selected" if tid == buscar_id else ""}>{tid}</option>' for tid in sorted({str(t.get("id_tramo", "")).strip() for t in tramos_originales if str(t.get("id_tramo", "")).strip()}))}
                        </select>
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-outline-secondary mb-3">
                            <i class="bi bi-search"></i> Buscar Tramo
                        </button>
                    </div>
                </form>
            </div>
            <div class="me-3">
                <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#nuevoTramoModal">
                    <i class="bi bi-plus-lg"></i> Agregar Nuevo Tramo
                </button>
            </div>
        </div>

        <!-- Modal para nuevo tramo -->
        <div class="modal fade" id="nuevoTramoModal" tabindex="-1" aria-labelledby="nuevoTramoModalLabel" aria-hidden="true">
            <div class="modal-dialog"><div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="nuevoTramoModalLabel">Nuevo Tramo</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form action="/tramos/nuevo" method="POST">
                    <div class="modal-body">
                        <div class="mb-3"><label class="form-label">Id Tramo</label><input name="id_tramo" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Vía</label><input name="id_via" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Pto km ini</label><input name="pto_km_ini" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Pto km fin</label><input name="pto_km_fin" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Tipología</label><input name="tipologia" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Velocidad máxima</label><input name="velocidad_max" class="form-control"></div>
                        <div class="mb-3"><label class="form-label">Descripción</label><textarea name="descripcion" class="form-control"></textarea></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-primary">Guardar</button>
                    </div>
                </form>
            </div></div>
        </div>

        <div class="table-responsive shadow-sm rounded">
            <table class="table table-hover table-bordered align-middle text-center" id="tablaTramos">
                <thead class="table-primary">
                    <tr>
                        <th>Id Tramo</th>
                        <th>Vía</th>
                        <th>Pto km ini</th>
                        <th>Pto km fin</th>
                        <th>Tipología</th>
                        <th>Velocidad</th>
                        <th>Descripción</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody id="tbodyTramos">
                    {filas_html}
                </tbody>
            </table>
        </div>

        <!-- Controles de paginación -->
        <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
            <!-- Selector filas por página -->
            <div class="d-flex align-items-center gap-2">
                <label for="filasPorPagina" class="form-label mb-0 text-muted small">Mostrar</label>
                <select id="filasPorPagina" class="form-select form-select-sm" style="width:auto;">
                    <option value="10" selected>10</option>
                    <option value="15">15</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="0">Todos</option>
                </select>
                <span class="text-muted small">filas por página</span>
            </div>

            <!-- Info + Navegación -->
            <div class="d-flex align-items-center gap-3 flex-wrap">
                <span id="infoPagina" class="text-muted small"></span>
                <nav>
                    <ul class="pagination pagination-sm mb-0" id="paginacionTramos"></ul>
                </nav>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
    <script>
      // ── Paginación ──────────────────────────────────────────────
      (function() {{
        const tbody = document.getElementById('tbodyTramos');
        const selector = document.getElementById('filasPorPagina');
        const navUl = document.getElementById('paginacionTramos');
        const info = document.getElementById('infoPagina');
        let paginaActual = 1;

        function filas() {{
          return Array.from(tbody.querySelectorAll('tr'));
        }}

        function renderPagina() {{
          const todas = filas();
          const porPagina = parseInt(selector.value);
          const total = todas.length;

          if (porPagina === 0) {{
            todas.forEach(r => r.style.display = '');
            navUl.innerHTML = '';
            info.textContent = total + ' registros';
            return;
          }}

          const totalPaginas = Math.ceil(total / porPagina);
          if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;

          const inicio = (paginaActual - 1) * porPagina;
          const fin = inicio + porPagina;
          todas.forEach((r, i) => r.style.display = (i >= inicio && i < fin) ? '' : 'none');

          const desde = total === 0 ? 0 : inicio + 1;
          const hasta = Math.min(fin, total);
          info.textContent = `${{desde}}–${{hasta}} de ${{total}} registros`;

          // Botones de página
          navUl.innerHTML = '';

          function addPageBtn(p) {{
            const liP = document.createElement('li');
            liP.className = 'page-item' + (p === paginaActual ? ' active' : '');
            liP.innerHTML = `<a class="page-link" href="#">${{p}}</a>`;
            liP.addEventListener('click', e => {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
            navUl.appendChild(liP);
          }}
          function addEllipsis() {{
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<span class="page-link">…</span>';
            navUl.appendChild(li);
          }}

          // Primera
          const liFirst = document.createElement('li');
          liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
          liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
          liFirst.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
          navUl.appendChild(liFirst);

          // Anterior
          const liPrev = document.createElement('li');
          liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
          liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
          liPrev.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
          navUl.appendChild(liPrev);

          // Páginas numeradas con primera, última y rango central
          const rango = 2;
          let desde_p = Math.max(1, paginaActual - rango);
          let hasta_p = Math.min(totalPaginas, paginaActual + rango);
          if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
          if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));

          // Página 1 siempre visible
          if (desde_p > 1) {{
            addPageBtn(1);
            if (desde_p > 2) addEllipsis();
          }}

          for (let p = desde_p; p <= hasta_p; p++) addPageBtn(p);

          // Última página siempre visible
          if (hasta_p < totalPaginas) {{
            if (hasta_p < totalPaginas - 1) addEllipsis();
            addPageBtn(totalPaginas);
          }}

          // Siguiente
          const liNext = document.createElement('li');
          liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
          liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
          liNext.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
          navUl.appendChild(liNext);

          // Última
          const liLast = document.createElement('li');
          liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
          liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
          liLast.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
          navUl.appendChild(liLast);
        }}

        selector.addEventListener('change', () => {{ paginaActual = 1; renderPagina(); }});
        renderPagina();
      }})();

      // ── AJAX CRUD ───────────────────────────────────────────────
      (function() {{
        document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(function(form) {{
          var action = form.getAttribute('action') || '';
          if (!action.startsWith('/tramos/')) return;
          form.addEventListener('submit', async function(e) {{
            e.preventDefault();
            try {{
              const data = new FormData(form);
              const res = await fetch(action, {{
                method: 'POST',
                body: data,
                credentials: 'same-origin',
                headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
              }});
              const html = await res.text();
              document.open();
              document.write(html);
              document.close();
            }} catch (err) {{
              console.error('Error AJAX CRUD tramos:', err);
              form.submit();
            }}
          }});
        }});
      }})();
    </script>
</body>
</html>
'''
    return html_response  


def page_filtros(opciones_html: str, error_message: Optional[str] = None) -> str:

    error_html = ''
    if error_message:
        error_html = f'''
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            {error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    # KPIs/KGIs disponibles
    indicadores_disponibles = [
        "Ind_KG1", "Ind_KPIG1", "Ind_KPIG2", "Ind_KPIG3", "Ind_KPIG4",
        "Ind_KPIG5", "Ind_KPIG6", "Ind_KPIG7", "Ind_KPIG8", "Ind_KPIG9",
        "Ind_KPIG10", "Ind_KPIG11", "Ind_KPIG13", "Ind_KPIG14"
    ]

    # HTML de checkboxes para KPIs/KGIs
    opciones_kpigs = ''.join(
        f'''
        <div class="form-check">
            <input class="form-check-input kpi" type="checkbox" name="kpigs" value="{indicador}" id="{indicador}"
                   onclick="handleCheckboxClick(this, 'kpi')">
            <label class="form-check-label" for="{indicador}">{indicador}</label>
        </div>
        '''
        for indicador in indicadores_disponibles
    )

    # HTML de checkboxes para Incidencias
    incidencias_lista = [
        "Por defecto de altura",
        "Por defecto de descentramiento",
        "Por defecto de pendiente",
        "Por defecto de la variación de la pendiente",
        "Por defecto de flecha",
        "Por defecto de contraflecha",
        "Por defecto de tijera",
        "Por contacto fuera de la zona de trabajo del pantógrafo",
        "Número global de incidencias",
        "Índice global de evaluación de la tasa de fallos de la catenaria",
        "Otras causas"
    ]

    incidencias_html = ''.join(
        f'''
        <div class="form-check ms-2">
            <input class="form-check-input incidencia" type="checkbox" name="incidencias"
                   value="{nombre}" id="incidencia{i}"
                   onclick="handleCheckboxClick(this, 'incidencia')">
            <label class="form-check-label" for="incidencia{i}">{nombre}</label>
        </div>
        '''
        for i, nombre in enumerate(incidencias_lista)
    )

    # Documento completo (devolvemos STR, sin .encode)
    html_response = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Filtros Avanzados</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
    
        function cargarVias() {{
            const tramoSeleccionado = document.getElementById('tramo').value;
            if (!tramoSeleccionado) return;

            fetch(`/obtener_vias?tramo=${{encodeURIComponent(tramoSeleccionado)}}`)
                .then(response => response.json())
                .then(data => {{                         // <-- aquí el cambio correcto
                            const listaVias = data.vias || [];  // <-- data.vias, no vias ni data.data
                            const selectVia = document.getElementById('via');

                            selectVia.innerHTML = '<option selected disabled>Selecciona una vía</option>';

                            listaVias.forEach(via => {{
                                const option = document.createElement('option');
                                option.value = via;
                                option.textContent = via;
                                selectVia.appendChild(option);
                            }});
                        }})
                                .catch(error => console.error('Error al cargar vías:', error));
                        }}

        function toggleSelectAll(groupClass, sourceCheckbox) {{
            const checkboxes = document.querySelectorAll('input.form-check-input.' + groupClass);
            checkboxes.forEach(cb => cb.checked = sourceCheckbox.checked);
            handleExclusiveSelection(groupClass);
        }}

        function handleCheckboxClick(checkbox, groupClass) {{
            handleExclusiveSelection(groupClass);
        }}

        function handleExclusiveSelection(activeGroup) {{
            const kpiCheckboxes = document.querySelectorAll('input.form-check-input.kpi');
            const incidenciaCheckboxes = document.querySelectorAll('input.form-check-input.incidencia');
            const indicadoresCheckboxes = document.querySelectorAll('input.form-check-input.indicadores');

            const anyKpiChecked = Array.from(kpiCheckboxes).some(cb => cb.checked);
            const anyIncidenciaChecked = Array.from(incidenciaCheckboxes).some(cb => cb.checked);
            const anyIndicadoresChecked = Array.from(indicadoresCheckboxes).some(cb => cb.checked);

            if (activeGroup === 'kpi' && anyKpiChecked) {{
                incidenciaCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
                indicadoresCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
            }} else if (activeGroup === 'incidencia' && anyIncidenciaChecked) {{
                kpiCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
                indicadoresCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
            }} else if (activeGroup === 'indicadores' && anyIndicadoresChecked) {{
                kpiCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
                incidenciaCheckboxes.forEach(cb => {{ cb.checked = false; cb.disabled = true; }});
            }}

            if (!anyKpiChecked && !anyIncidenciaChecked && !anyIndicadoresChecked) {{
                kpiCheckboxes.forEach(cb => cb.disabled = false);
                incidenciaCheckboxes.forEach(cb => cb.disabled = false);
                indicadoresCheckboxes.forEach(cb => cb.disabled = false);
            }}
        }}
    </script>
</head>
<body>
''' + NAV_HTML + '''

<div class="container my-5 p-4 bg-white rounded shadow-sm" style="max-width: 900px;">
    <div class="d-flex align-items-center gap-2 mb-4">
      <span style="width:120px"></span>
      <h1 class="text-center text-primary mb-0 flex-grow-1">Filtros de Búsqueda</h1>
      <a href="/kpi-kgi" class="btn btn-primary btn-sm volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
    </div>
    __ERROR_HTML_PH__
    <form id="form-filtros-avanzados" method="post" action="/tabla">

        <!-- Sección de Localización -->
        <div class="d-flex flex-row border border-primary rounded-3 p-3 mb-4" id="accordionLocalizacion">
            <!-- Por tramos -->
            <div class="w-50 p-3 border-end border-primary text-center">
                <button class="btn btn-primary w-75" type="button" data-bs-toggle="collapse"
                        data-bs-target="#formulario" aria-expanded="false" aria-controls="formulario">
                    Localización por tramos
                </button>
                <div class="collapse" id="formulario" data-bs-parent="#accordionLocalizacion">
                    <div class="card card-body mt-3">
                        <div class="mb-3">
                            <label for="tramo" class="form-label">Tramo <span class="text-danger">*</span></label>
                            <select class="form-select border border-primary" id="tramo" name="tramo" onchange="cargarVias()">
                                <option selected disabled>Selecciona el tramo</option>
                                __OPCIONES_HTML_PH__
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="via" class="form-label">Vía</label>
                            <select class="form-select border border-primary" id="via" name="via">
                                <option selected disabled>Selecciona una vía</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label for="metro_inicio" class="form-label">Punto Kilométrico Inicio</label>
                            <input type="number" class="form-control border border-primary" id="metro_inicio" name="pto_km_ini">
                        </div>
                        <div class="mb-3">
                            <label for="metro_fin" class="form-label">Punto Kilométrico Fin</label>
                            <input type="number" class="form-control border border-primary" id="metro_fin" name="pto_km_fin">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Por ámbito geográfico -->
            <div class="w-50 p-3 text-center">
                <button class="btn btn-primary w-75" type="button" data-bs-toggle="collapse"
                        data-bs-target="#formulario2" aria-expanded="false" aria-controls="formulario2">
                    Localización por ámbito geográfico
                </button>
                <div class="collapse" id="formulario2" data-bs-parent="#accordionLocalizacion">
                    <div class="card card-body mt-3">
                        <div class="mb-3">
                            <label for="radio" class="form-label">Radio (KM)<span class="text-danger">*</span></label>
                            <input type="number" class="form-control border border-primary" id="radio" name="radio" step="1" min="1" inputmode="numeric">
                        </div>
                        <div class="mb-3">
                            <label for="coordenada_gps" class="form-label">Coordenada GPS (Decimales)<span class="text-danger">*</span></label>
                            <input type="text" class="form-control border border-primary" id="coordenada_gps" name="coordenada_gps" placeholder="EJ: 40.7128, -74.0060">
                        </div>
                        <input type="hidden" id="cuadrantes_seleccionados" name="cuadrantes_seleccionados" value="">
                        <!-- compatibilidad con backend legado -->
                        <input type="hidden" id="cuadrante_seleccionado" name="cuadrante_seleccionado" value="">

                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-outline-primary btn-sm" onclick="actualizarMapaCuadrantes()">
                                Actualizar mapa
                            </button>
                            <button type="button" class="btn btn-outline-secondary btn-sm" onclick="usarEjemploMapa()">
                                Ejemplo
                            </button>
                        </div>

                        <div id="geo-map-filtros" style="height:320px; margin-top:12px; border-radius:10px; overflow:hidden; border:1px solid #d0d7de;"></div>
                        <div class="d-flex flex-wrap gap-2 align-items-center mt-2">
                            <span class="badge text-bg-primary">Tramos visibles</span>
                            <span class="badge text-bg-warning text-dark">Cuadrantes marcados</span>
                            <span class="badge text-bg-secondary">Click para marcar/desmarcar</span>
                        </div>
                        <div class="small mt-1" id="geo-map-selected"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sección de Fechas -->
        <div class="d-flex flex-row justify-content-center gap-3 border border-primary rounded-3 p-3 my-4">
            <div class="w-48">
                <div class="mb-3">
                    <label for="fecha_inicio" class="form-label">Fecha de Inicio</label>
                    <input type="date" class="form-control border border-primary" name="fecha_inicio" id="fecha_inicio">
                </div>
            </div>
            <div class="w-48">
                <div class="mb-3">
                    <label for="fecha_fin" class="form-label">Fecha de Fin</label>
                    <input type="date" class="form-control border border-primary" name="fecha_fin" id="fecha_fin">
                </div>
            </div>
        </div>

        <!-- Sección de Indicadores -->
        <h3 class="text-center mb-5">Elija Indicadores KGIs/KPIs o Incidencias</h3>
        
        <div class="d-flex flex-row align-items-start mb-3">
            <div class="me-4">
                <strong><p>KGIs/KPIs<span class="text-danger">*</span></p></strong>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="selectAllKpis" onclick="toggleSelectAll('kpi', this)">
                    <label class="form-check-label" for="selectAllKpis">Seleccionar / Deseleccionar Todo</label>
                </div>
                __OPCIONES_KPIGS_PH__
            </div>
            <div style="margin-left: 60px;">
                <strong><p>Incidencias <span class="text-danger">*</span></p></strong>
                <div class="mb-3">
                    <div class="form-check mb-3">
                        <input class="form-check-input incidencia" type="checkbox" id="selectAllIncidencias" onclick="toggleSelectAll('incidencia', this)">
                        <label class="form-check-label" for="selectAllIncidencias">Seleccionar / Deseleccionar Todo</label>
                    </div>
                </div>
                <div>
                    __INCIDENCIAS_HTML_PH__
                </div>
            </div>
        </div> 

        <!-- Métricas adicionales -->
        <div class="d-flex flex-column mb-4">
            <strong><p>Indicadores de operativa<span class="text-danger">*</span></p></strong>

            <div id="alerta_km" class="alert alert-warning mt-2" style="display:none;">
                <strong>Atención:</strong> Los puntos km ini y km fin no se tomarán en cuenta para la búsqueda de Indicadores de Operativa
            </div>
            

            <div class="form-check mb-3">
                <input class="form-check-input indicadores" type="checkbox" id="selectAllIndicadores" onclick="toggleSelectAll('indicadores', this); mostrarAvisoKM();">
                <label class="form-check-label" for="selectAllIndicadores">Seleccionar / Deseleccionar Todo</label>
            </div>

            <div class="form-check">
                    <input class="form-check-input indicadores" type="checkbox" id="check1" name="indicadores" value="inspecciones"
                        onclick="handleCheckboxClick(this, 'indicadores'); mostrarAvisoKM();">
                    <label class="form-check-label" for="check1">Número de inspecciones realizadas</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input indicadores" type="checkbox" id="check2" name="indicadores" value="km"
                        onclick="handleCheckboxClick(this, 'indicadores'); mostrarAvisoKM();">
                    <label class="form-check-label" for="check2">Número de kilómetros inspeccionados</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input indicadores" type="checkbox" id="check3" name="indicadores" value="formularios"
                        onclick="handleCheckboxClick(this, 'indicadores'); mostrarAvisoKM();">
                    <label class="form-check-label" for="check3">Número de informes registrados</label>
                </div>
                <div class="form-check">
                    <input class="form-check-input indicadores" type="checkbox" id="check4" name="indicadores" value="errores"
                        onclick="handleCheckboxClick(this, 'indicadores'); mostrarAvisoKM();">
                    <label class="form-check-label" for="check4">Número de errores detectados en la documentación</label>
                </div>
        </div>

        <div class="d-flex justify-content-between">
            <button type="submit" class="btn btn-primary mt-3">Ver Resultados</button>
        </div>
    </form>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
<script>
    if (window.history.replaceState) {{
        window.history.replaceState(null, null, window.location.pathname);
    }}
</script>
<script>
function mostrarAvisoKM() {{
    var alerta = document.getElementById("alerta_km");
    var checks = document.querySelectorAll("input.form-check-input.indicadores");
    var algunoMarcado = Array.from(checks).some(cb => cb.checked);

    if (algunoMarcado) {{
        alerta.style.display = "block";
    }} else {{
        alerta.style.display = "none";
    }}
}}
</script>
<script>
(function () {{
    let geoMap = null;
    let rectLayers = [];
    let segLayers = [];
    let selectedCuadId = null;
    let payloadCache = null;
    let overviewLayers = [];
    let overviewTimer = null;
    let lastOverviewKey = null;
    let radioCircle = null;
    let selectionMarker = null;
    let mapInteractionsBound = false;
    let globalBboxCache = {{
        minLat: 40.641366,
        maxLat: 41.085923,
        minLon: -4.730047,
        maxLon: -3.841580,
    }}; // Bounding box global precalculado
    let lastClickedPoint = null;

    function setStatus(msg) {{
        const el = document.getElementById('geo-map-status');
        if (el) el.textContent = msg || '';
    }}

    function setSelectedInfo() {{
        const el = document.getElementById('geo-map-selected');
        if (!el) return;
        if (selectedCuadId === null || selectedCuadId === undefined) {{
            el.innerHTML = '';
            return;
        }}
        el.innerHTML = `<span class="badge rounded-pill text-bg-warning text-dark me-1 mb-1">Cuadrante ${selectedCuadId}</span>`;
    }}

    function clearLayers() {{
        rectLayers.forEach(r => {{ try {{ geoMap.removeLayer(r.layer); }} catch(e) {{}} }});
        segLayers.forEach(s => {{ try {{ geoMap.removeLayer(s.layer); }} catch(e) {{}} }});
        rectLayers = [];
        segLayers = [];
    }}

    function clearOverview() {{
        overviewLayers.forEach(l => {{ try {{ geoMap.removeLayer(l); }} catch(e) {{}} }});
        overviewLayers = [];
    }}

    function applyQuadrantSelectionStyles() {{
        rectLayers.forEach(r => {{
            const isSelected = selectedCuadId !== null && selectedCuadId !== undefined && r.id === selectedCuadId;
            r.layer.setStyle({{
                color: isSelected ? '#ff9800' : '#6c757d',
                weight: isSelected ? 3 : 1,
                fillOpacity: isSelected ? 0.28 : 0.05,
                fillColor: isSelected ? '#ffd54f' : '#6c757d',
            }});
        }});

        overviewLayers.forEach(l => {{
            const isSelected = selectedCuadId !== null && selectedCuadId !== undefined && l._cuadId === selectedCuadId;
            const baseColor = l._baseColor || '#66bb6a';
            const baseFill = l._baseFill || 0.10;
            l.setStyle({{
                color: isSelected ? '#ff9800' : baseColor,
                weight: isSelected ? 2 : 1,
                fillOpacity: isSelected ? 0.28 : baseFill,
                fillColor: isSelected ? '#ffd54f' : baseColor,
            }});
        }});
    }}

    function makeSelectionIcon() {{
        return L.divIcon({{
            className: 'selection-marker-icon',
            html: '<i class="bi bi-geo-alt-fill" style="font-size:28px;color:#e11d48;text-shadow:0 1px 2px rgba(0,0,0,0.35);"></i>',
            iconSize: [28, 28],
            iconAnchor: [14, 28],
        }});
    }}

    function setSelectedPoint(lat, lon) {{
        const coordEl = document.getElementById('coordenada_gps');
        if (coordEl) coordEl.value = `${{lat.toFixed(6)}}, ${{lon.toFixed(6)}}`;
        lastClickedPoint = {{ lat, lon }};
        if (!geoMap) return;

        if (selectionMarker) {{
            try {{ geoMap.removeLayer(selectionMarker); }} catch (e) {{}}
            selectionMarker = null;
        }}

        selectionMarker = L.marker([lat, lon], {{
            icon: makeSelectionIcon(),
            interactive: false,
            keyboard: false,
            zIndexOffset: 1000,
        }}).addTo(geoMap);

        if (getRadioMeters()) {{
            drawRadioAt(lat, lon);
        }}
    }}

    function bindMapInteractions() {{
        if (!geoMap || mapInteractionsBound) return;
        mapInteractionsBound = true;
        geoMap.on('click', function (e) {{
            setSelectedPoint(e.latlng.lat, e.latlng.lng);
        }});
    }}

    function getColorForKey(key) {{
        const palette = [
            '#e11d48', '#0f766e', '#2563eb', '#f97316', '#7c3aed',
            '#15803d', '#db2777', '#c2410c', '#0891b2', '#9333ea'
        ];
        let hash = 0;
        const text = String(key || 'segmento');
        for (let i = 0; i < text.length; i++) {{
            hash = ((hash << 5) - hash) + text.charCodeAt(i);
            hash |= 0;
        }}
        return palette[Math.abs(hash) % palette.length];
    }}

    function updateHiddenSelected() {{
        const hiddenMulti = document.getElementById('cuadrantes_seleccionados');
        const hiddenSingle = document.getElementById('cuadrante_seleccionado');
        const v = (selectedCuadId === null || selectedCuadId === undefined) ? '' : String(selectedCuadId);
        if (hiddenMulti) hiddenMulti.value = v;
        if (hiddenSingle) hiddenSingle.value = v;
        setSelectedInfo();
    }}

    function applySelection() {{
        rectLayers.forEach(r => {{
            const isSel = (selectedCuadId !== null && r.id === selectedCuadId);
            r.layer.setStyle({{
                color: isSel ? '#ff9800' : '#6c757d',
                weight: isSel ? 3 : 1,
                fillOpacity: isSel ? 0.28 : 0.05,
                fillColor: isSel ? '#ffd54f' : '#6c757d',
            }});
        }});
    }}

    function getRadioMeters() {{
        const radioEl = document.getElementById('radio');
        const raw = (radioEl?.value || '').trim();
        if (!raw) return 0;
        const n = Number(raw);
        if (!Number.isFinite(n) || n <= 0) return 0;
        return Math.round(n * 1000);
    }}

    function drawRadioAt(lat, lon) {{
        if (!geoMap) return;
        if (radioCircle) {{
            try {{ geoMap.removeLayer(radioCircle); }} catch (e) {{}}
            radioCircle = null;
        }}
        const meters = getRadioMeters();
        if (!meters) return;
        radioCircle = L.circle([lat, lon], {{
            radius: meters,
            color: '#ef6c00',
            weight: 2,
            fillColor: '#ffb74d',
            fillOpacity: 0.15,
            interactive: false,
        }}).addTo(geoMap);
    }}

    function updateCoordsFromMapCenter() {{
        if (!geoMap) return;
        const coordEl = document.getElementById('coordenada_gps');
        if (!coordEl) return;
        const c = geoMap.getCenter();
        coordEl.value = `${{c.lat.toFixed(6)}}, ${{c.lng.toFixed(6)}}`;
    }}

    function loadGlobalBoundingBox() {{
        return globalBboxCache;
    }}

    function renderPayload(payload) {{
        payloadCache = payload;
        clearLayers();

        const startLat = payload.punto_busqueda.lat;
        const startLon = payload.punto_busqueda.lon;

        if (!geoMap) {{
            geoMap = L.map('geo-map-filtros').setView([40.4168, -3.7038], 6); // España por defecto
            // Evita bloqueos de OpenStreetMap volunteer servers usando Carto (tiles públicos).
            L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                attribution: '© OpenStreetMap contributors, © CARTO'
            }}).addTo(geoMap);
            bindMapInteractions();
            loadOverview();
        }} else {{
            geoMap.setView([startLat, startLon]);
        }}

        selectedCuadId = null;
        if (payload.cuadrante_defecto !== undefined && payload.cuadrante_defecto !== null) {{
            selectedCuadId = payload.cuadrante_defecto;
        }}
        updateHiddenSelected();
        applyQuadrantSelectionStyles();

        // Cuadrantes
        (payload.cuadrantes || []).forEach(cuad => {{
            const latNo = cuad.esquina_NO[0];
            const lonNo = cuad.esquina_NO[1];
            const latSe = cuad.esquina_SE[0];
            const lonSe = cuad.esquina_SE[1];
            const bounds = [
                [latSe, lonNo],
                [latNo, lonSe],
            ];

            const rect = L.rectangle(bounds, {{
                color: '#6c757d',
                weight: 1,
                fillOpacity: 0.05,
                fillColor: '#6c757d',
            }}).addTo(geoMap);

            rect.bindTooltip(`Cuadrante ${{cuad.id_cuadrante}}`, {{ sticky: true }});
            rect.on('click', function () {{
                const id = cuad.id_cuadrante;
                selectedCuadId = id;
                const latCenter = (latNo + latSe) / 2;
                const lonCenter = (lonNo + lonSe) / 2;
                setSelectedPoint(latCenter, lonCenter);
                updateHiddenSelected();
                applyQuadrantSelectionStyles();
                applySelection();
            }});

            rectLayers.push({{ id: cuad.id_cuadrante, layer: rect }});
        }});

        // Segs deshabilitados - solo mostrar cuadrantes y bounding box

        // Bounding box global: se pinta al instante con coordenadas precalculadas.
        const globalBbox = loadGlobalBoundingBox();
        if (globalBbox && geoMap) {{
            const {{ minLat, maxLat, minLon, maxLon }} = globalBbox;
            L.rectangle([[minLat, minLon], [maxLat, maxLon]], {{
                color: '#2563eb',
                weight: 3,
                fillOpacity: 0,
                dashArray: '5, 5',
                interactive: false,
            }}).addTo(geoMap);
        }}

        applySelection();

        if (selectedCuadId !== null && payload.cuadrantes) {{
            const c = (payload.cuadrantes || []).find(x => x.id_cuadrante === selectedCuadId);
            if (c) {{
                const latC = (c.esquina_NO[0] + c.esquina_SE[0]) / 2;
                const lonC = (c.esquina_NO[1] + c.esquina_SE[1]) / 2;
                drawRadioAt(latC, lonC);
            }}
        }}
    }}

    async function actualizarMapaCuadrantes() {{
        const radioEl = document.getElementById('radio');
        const coordEl = document.getElementById('coordenada_gps');
        const radioVal = radioEl ? (radioEl.value || '').trim() : '';
        const coordVal = coordEl ? (coordEl.value || '').trim() : '';

        // Radio sin decimales
        if (radioVal && radioVal.includes('.')) {{
            setStatus('El radio no admite decimales. Usa un número entero (por ejemplo 2).');
            return;
        }}
        if (!radioVal || !coordVal) {{
            setStatus('Para dibujar tramos detallados, introduce radio y coordenada GPS. Puedes marcar cuadrantes en el mapa sin estos campos.');
            scheduleOverview();
            if (geoMap) {{
                const c = geoMap.getCenter();
                drawRadioAt(c.lat, c.lng);
            }}
            return;
        }}

        setStatus('Cargando mapa…');

        try {{
            const url = `/mapa-cuadrantes?coordenada_gps=${{encodeURIComponent(coordVal)}}&radio=${{encodeURIComponent(radioVal)}}&max_segmentos=800`;
            const resp = await fetch(url, {{ credentials: 'same-origin' }});
            if (!resp.ok) throw new Error(await resp.text());
            const payload = await resp.json();
            await renderPayload(payload);
        }} catch (err) {{
            console.error(err);
            setStatus('No se pudo cargar el mapa: ' + (err?.message || err));
        }}
    }}

    window.actualizarMapaCuadrantes = actualizarMapaCuadrantes;

    window.usarEjemploMapa = function () {{
        const coordEl = document.getElementById('coordenada_gps');
        const radioEl = document.getElementById('radio');
        if (coordEl) coordEl.value = '41.060057, -4.706851';
        if (radioEl) radioEl.value = '2';
        actualizarMapaCuadrantes();
    }}

    // Carga automática del mapa al escribir coordenada + radio (tramos detallados).
    let autoTimer = null;
    const radioEl = document.getElementById('radio');
    const coordEl = document.getElementById('coordenada_gps');
    if (radioEl && coordEl) {{
        const handler = function () {{
            if (autoTimer) clearTimeout(autoTimer);
            autoTimer = setTimeout(() => {{
                // Solo si ya hay valores razonables.
                const r = (radioEl.value || '').trim();
                const c = (coordEl.value || '').trim();
                if (r && c) actualizarMapaCuadrantes();
            }}, 600);
        }};
        radioEl.addEventListener('input', handler);
        coordEl.addEventListener('input', handler);
        radioEl.addEventListener('input', function () {{
            if (!geoMap) return;
            if (lastClickedPoint) {{
                if (coordEl) coordEl.value = `${{lastClickedPoint.lat.toFixed(6)}}, ${{lastClickedPoint.lon.toFixed(6)}}`;
                drawRadioAt(lastClickedPoint.lat, lastClickedPoint.lon);
                return;
            }}
            const c = geoMap.getCenter();
            drawRadioAt(c.lat, c.lng);
        }});
    }}

    async function loadOverview() {{
        if (!geoMap) return;
        const b = geoMap.getBounds();
        const south = b.getSouth();
        const west = b.getWest();
        const north = b.getNorth();
        const east = b.getEast();
        // Si el mapa está sin tamaño (ej: dentro de collapse oculto), bounds degenerado.
        if (!Number.isFinite(south) || !Number.isFinite(west) || !Number.isFinite(north) || !Number.isFinite(east)) return;
        if (Math.abs(north - south) < 0.00001 || Math.abs(east - west) < 0.00001) return;

        // Evita consultas repetidas por micro-movimientos.
        const key = [south, west, north, east].map(v => Number(v).toFixed(3)).join(',');
        if (key === lastOverviewKey) return;
        lastOverviewKey = key;

        clearOverview();
        try {{
            const zoom = geoMap.getZoom ? geoMap.getZoom() : 6;
            const limit = zoom <= 6 ? 200 : (zoom <= 8 ? 400 : 700);
            const url = `/mapa-cuadrantes-overview?bbox=${{south}},${{west}},${{north}},${{east}}&limit=${{limit}}`;
            const resp = await fetch(url, {{ credentials: 'same-origin' }});
            if (!resp.ok) throw new Error(await resp.text());
            const data = await resp.json();
            const cuads = data.cuadrantes || [];
            
            // Colorea según cantidad de tramos aproximada.
            cuads.forEach(cuad => {{
                const latNo = cuad.esquina_NO[0];
                const lonNo = cuad.esquina_NO[1];
                const latSe = cuad.esquina_SE[0];
                const lonSe = cuad.esquina_SE[1];
                if (latNo === undefined || lonNo === undefined || latSe === undefined || lonSe === undefined) return;
                
                const bounds = [
                    [latSe, lonNo],
                    [latNo, lonSe],
                ];
                const n = Number(cuad.n_tramos || 1);
                const color = n >= 5 ? '#1b5e20' : (n >= 2 ? '#2e7d32' : '#66bb6a');
                const fill = n >= 5 ? 0.28 : (n >= 2 ? 0.18 : 0.10);
                const rect = L.rectangle(bounds, {{
                    color: color,
                    weight: 1,
                    fillOpacity: fill,
                    fillColor: color,
                }});
                rect.on('click', function () {{
                    // Permite marcar cuadrantes desde vista general.
                    const id = cuad.id_cuadrante;
                    selectedCuadId = id;
                    updateHiddenSelected();
                    // Visibilidad de tramos detallados (si existen)
                    applyQuadrantSelectionStyles();
                    applySelection();
                    // Remarca estilo del rectángulo seleccionado
                    rect.setStyle({{
                        weight: (selectedCuadId === id) ? 2 : 1,
                        color: (selectedCuadId === id) ? '#ff9800' : color,
                        fillColor: (selectedCuadId === id) ? '#ffd54f' : color,
                    }});
                    const latCenter = (latNo + latSe) / 2;
                    const lonCenter = (lonNo + lonSe) / 2;
                    setSelectedPoint(latCenter, lonCenter);
                }});
                rect._cuadId = cuad.id_cuadrante;
                rect._baseColor = color;
                rect._baseFill = fill;
                rect.bindTooltip(`Cuadrante ${{cuad.id_cuadrante}} · Tramos: ${{n}}`, {{ sticky: true }});
                rect.addTo(geoMap);
                overviewLayers.push(rect);
            }});
            applyQuadrantSelectionStyles();
            
            setStatus(`Cuadrantes con tramos en vista: ${{cuads.length}}`);
        }} catch (e) {{
            // Silencioso si falla overview
            console.error(e);
        }}
    }}

    function scheduleOverview() {{
        if (!geoMap) return;
        if (overviewTimer) clearTimeout(overviewTimer);
        overviewTimer = setTimeout(loadOverview, 500);
    }}

    // Inicializa mapa general al entrar, aunque no haya coordenadas/radio.
    function initMapOnLoad() {{
        if (geoMap) return;
        const mapEl = document.getElementById('geo-map-filtros');
        if (!mapEl) return;
        geoMap = L.map('geo-map-filtros').setView([40.4168, -3.7038], 6); // España
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '© OpenStreetMap contributors, © CARTO'
        }}).addTo(geoMap);
        bindMapInteractions();
        setStatus('Cargando cuadrantes con tramos...');
        loadOverview();

        // Si el mapa está dentro de un collapse oculto, recalcular tamaño al abrir.
        const panel = document.getElementById('formulario2');
        if (panel) {{
            panel.addEventListener('shown.bs.collapse', function () {{
                try {{
                    geoMap.invalidateSize(true);
                }} catch (e) {{}}
                setTimeout(() => {{
                    try {{
                        geoMap.invalidateSize(true);
                    }} catch (e) {{}}
                    lastOverviewKey = null;
                    scheduleOverview();
                }}, 120);
            }});
        }}
    }}

    initMapOnLoad();

}})();
</script>
<script>
(function() {{
    const form = document.getElementById('form-filtros-avanzados');
    if (!form) return;

    form.addEventListener('submit', async function(e) {{
        const radioEl = document.getElementById('radio');
        const coordEl = document.getElementById('coordenada_gps');
        const hiddenCuads = document.getElementById('cuadrantes_seleccionados');
        const tramoEl = document.getElementById('tramo');
        const viaEl = document.getElementById('via');
        const usingGeo = Boolean((coordEl?.value || '').trim() || (radioEl?.value || '').trim());
        const usingTramo = Boolean((tramoEl?.value || '').trim() && (viaEl?.value || '').trim());
        const hasCuads = Boolean((hiddenCuads?.value || '').trim());
        const anyMetric = Array.from(document.querySelectorAll('input.form-check-input.kpi, input.form-check-input.incidencia, input.form-check-input.indicadores')).some(cb => cb.checked);

        if (!anyMetric) {{
            e.preventDefault();
            alert('Selecciona al menos un KPI, incidencia o indicador de operativa.');
            return;
        }}

        const hasCoordAndRadio = Boolean((coordEl?.value || '').trim() && (radioEl?.value || '').trim());
        if (usingGeo && !usingTramo && !hasCuads && !hasCoordAndRadio) {{
            e.preventDefault();
            alert('Marca un cuadrante o completa coordenada y radio antes de calcular.');
            return;
        }}

        e.preventDefault();
        const submitBtn = form.querySelector('button[type="submit"]');
        const oldText = submitBtn ? submitBtn.innerHTML : '';
        if (submitBtn) {{
            submitBtn.disabled = true;
            submitBtn.innerHTML = 'Procesando...';
        }}
        try {{
            const formData = new FormData(form);
            const response = await fetch(form.action, {{
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
            }});
            const html = await response.text();
            document.open();
            document.write(html);
            document.close();
        }} catch (err) {{
            console.error('Error AJAX en /tabla:', err);
            form.submit();
        }} finally {{
            if (submitBtn) {{
                submitBtn.disabled = false;
                submitBtn.innerHTML = oldText;
            }}
        }}
    }});
}})();
</script>

</body>
</html>
'''
    html_response = html_response.replace('__ERROR_HTML_PH__', error_html)
    html_response = html_response.replace('__OPCIONES_HTML_PH__', opciones_html)
    html_response = html_response.replace('__OPCIONES_KPIGS_PH__', opciones_kpigs)
    html_response = html_response.replace('__INCIDENCIAS_HTML_PH__', incidencias_html)
    html_response = html_response.replace('{{', '{').replace('}}', '}')
    return html_response


def page_consultar_datos_filtros(opciones_tramos_html: str, error_message: Optional[str] = None) -> str:
    """
    Interfaz de filtros para el módulo 'Consultar Datos'.
    """
    error_html = ""
    if error_message:
        error_html = f"""
        <div class="alert alert-danger alert-dismissible fade show mt-3" role="alert">
            {error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Consultar Datos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet"
        crossorigin="anonymous"
    >
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {{
            background-color: #f5f7fb;
        }}
        .form-wrap {{
            max-width: 1180px;
        }}
        .card-filtros {{
            border-radius: 18px;
            const msg = String(err?.message || err || '');
            if (msg.includes('no está cubierta por ningún cuadrante')) {{
                setStatus('');
                return;
            }}
            setStatus('No se pudo cargar el mapa: ' + msg);
            border: none;
        }}
        .btn-buscar {{
            background-color: #0d6efd;
            border-color: #0d6efd;
            border-radius: 999px;
            padding-inline: 2.5rem;
        }}
        .pill-group .form-check {{
            margin-right: .5rem;
        }}
        .pill-group .form-check-input {{
            position: absolute;
            opacity: 0;
        }}
        .pill-group .form-check-label {{
            border-radius: 999px;
            border: 1px solid #ced4da;
            padding: .35rem .9rem;
            cursor: pointer;
            transition: all .15s ease-in-out;
            display: inline-flex;
            align-items: center;
            font-size: .9rem;
        }}
        .pill-group .form-check-input:checked + .form-check-label {{
            background-color: #0d6efd;
            color: #fff;
            border-color: #0d6efd;
        }}
        .tipos-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(140px, 1fr));
            gap: 0.85rem;
        }}
        .tipo-card {{
            cursor: pointer;
            display: block;
            text-decoration: none;
        }}
        .tipo-box {{
            width: 100%;
            min-height: 128px;
            border-radius: 15px;
            background: #fff;
            border: 2px solid #e3e3e3;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 10px;
            transition: .2s ease-in-out;
            box-shadow: 0 3px 10px rgba(0,0,0,0.07);
            text-align: center;
            padding: .5rem;
        }}
        .tipo-box:hover {{
            transform: scale(1.03);
            border-color: #0d6efd;
            box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
        }}
        .tipo-card input {{
            display: none;
        }}
        .tipo-card input:checked + .tipo-box {{
            border-color: #0d6efd;
            background: #e9f2ff;
            transform: scale(1.03);
        }}
        .tipo-icon {{
            width: 44px;
            height: 44px;
        }}
        @media (max-width: 991.98px) {{
            .tipos-grid {{
                grid-template-columns: repeat(2, minmax(140px, 1fr));
            }}
        }}
        @media (max-width: 575.98px) {{
            .tipos-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
{NAV_HTML}

<div class="container py-4 form-wrap">
    <h1 class="h3 text-center mb-3">Filtros de Búsqueda</h1>
    {error_html}
    <div class="row justify-content-center">
        <div class="col-12">
            <div class="card card-filtros p-4 bg-white">
                <form id="form-consultar-datos" method="POST" action="/consultar-datos">
                    <!-- Localización -->
                    <h2 class="mb-3">Localización por tramos</h2>

                    <div class="mb-3">
                        <label for="tramo" class="form-label">Tramo <span class="text-danger">*</span></label>
                        <select class="form-select" id="tramo" name="tramo" onchange="cargarVias()" required>
                            <option value="">Selecciona el tramo</option>
                            {opciones_tramos_html}
                        </select>
                    </div>

                    <div class="mb-3">
                        <label for="via" class="form-label">Vía <span class="text-danger">*</span></label>
                        <select class="form-select" id="via" name="via" required>
                            <option value="">Selecciona una vía</option>
                        </select>
                    </div>

                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="pto_km_ini" class="form-label">Punto Kilométrico Inicio</label>
                            <input type="number" step="0.001" class="form-control" id="pto_km_ini"
                                   name="pto_km_ini" placeholder="PK inicio">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="pto_km_fin" class="form-label">Punto Kilométrico Fin</label>
                            <input type="number" step="0.001" class="form-control" id="pto_km_fin"
                                   name="pto_km_fin" placeholder="PK fin">
                        </div>
                    </div>

                    <!-- Fechas -->
                    <h2 class="mt-3 mb-2">Fechas</h2>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="fecha_inicio" class="form-label">Fecha Inicio</label>
                            <input type="date" class="form-control" id="fecha_inicio" name="fecha_inicio">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="fecha_fin" class="form-label">Fecha Fin</label>
                            <input type="date" class="form-control" id="fecha_fin" name="fecha_fin">
                        </div>
                    </div>

                    <!-- Tipo de búsqueda -->
                    <h2 class="mt-3 mb-3 text-center">Tipo de Búsqueda</h2>

                    <div class="tipos-grid mb-4">

                        <!-- Inspecciones -->
                        <label class="tipo-card">
                            <input type="radio" name="tipo_busqueda" value="inspecciones">
                            <div class="tipo-box">
                                <img src="img/inspeccion.png" class="tipo-icon">
                                <span><strong>Inspecciones</strong></span>
                            </div>
                        </label>

                        <!-- Formularios -->
                        <label class="tipo-card">
                            <input type="radio" name="tipo_busqueda" value="formularios">
                            <div class="tipo-box">
                                <img src="img/formulario.png" class="tipo-icon">
                                <span><strong>Formularios</strong></span>
                            </div>
                        </label>

                        <!-- Incidencias -->
                        <label class="tipo-card">
                            <input type="radio" name="tipo_busqueda" value="incidencias">
                            <div class="tipo-box">
                                <img src="img/error.png" class="tipo-icon">
                                <span><strong>Incidencias</strong></span>
                            </div>
                        </label>

                        <!-- Mediciones -->
                        <label class="tipo-card">
                            <input type="radio" name="tipo_busqueda" value="mediciones" checked>
                            <div class="tipo-box">
                                <img src="img/medicion.png" class="tipo-icon">
                                <span><strong>Mediciones</strong></span>
                            </div>
                        </label>

                    </div>


                    <div class="d-flex justify-content-between mt-3">
                        <a href="/dss" class="btn btn-primary volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
                        <button type="submit" class="btn btn-primary"><i class="bi bi-search me-1"></i> Buscar
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<script
    src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
    crossorigin="anonymous"></script>
<script>
    function cargarVias() {{
        const tramo = document.getElementById('tramo').value;
        const viaSelect = document.getElementById('via');

        if (!tramo) {{
            viaSelect.innerHTML = '<option value="">Selecciona una vía</option>';
            return;
        }}

        fetch('/obtener_vias?tramo=' + encodeURIComponent(tramo))
            .then(res => res.json())
            .then(data => {{
                viaSelect.innerHTML = '<option value="">Selecciona una vía</option>';
                (data.vias || []).forEach(v => {{
                    const opt = document.createElement('option');
                    opt.value = v;
                    opt.textContent = v;
                    viaSelect.appendChild(opt);
                }});
            }})
            .catch(err => {{
                console.error('Error obteniendo vías', err);
                viaSelect.innerHTML = '<option value="">Error cargando vías</option>';
            }});
    }}
</script>
<script>
    (function() {{
        const form = document.getElementById('form-consultar-datos');
        if (!form) return;

        form.addEventListener('submit', async function(e) {{
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const oldText = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {{
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Buscando...';
            }}
            try {{
                const formData = new FormData(form);
                const response = await fetch(form.action, {{
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin',
                    headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
                }});
                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
            }} catch (err) {{
                console.error('Error AJAX en /consultar-datos:', err);
                form.submit();
            }} finally {{
                if (submitBtn) {{
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = oldText;
                }}
            }}
        }});
    }})();
</script>
</body>
</html>
"""


def page_consultar_datos_mediciones_resultados(
    tramo: str,
    via: str,
    pto_km_ini: Optional[float],
    pto_km_fin: Optional[float],
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    resultados: List[Dict[str, Any]],
) -> str:

    # =============================
    #   TEXTO DE FILTROS
    # =============================
    filtros = []
    if tramo:
        filtros.append(f"Tramo: {tramo}")
    if via:
        filtros.append(f"Vía: {via}")
    if pto_km_ini is not None or pto_km_fin is not None:
        if pto_km_ini is not None and pto_km_fin is not None:
            filtros.append(f"PK: {pto_km_ini} - {pto_km_fin}")
        elif pto_km_ini is not None:
            filtros.append(f"PK desde {pto_km_ini}")
        elif pto_km_fin is not None:
            filtros.append(f"PK hasta {pto_km_fin}")
    if fecha_inicio:
        filtros.append(f"Fecha desde: {fecha_inicio}")
    if fecha_fin:
        filtros.append(f"Fecha hasta: {fecha_fin}")

    filtros_html = "<br>".join(filtros) if filtros else "Sin filtros adicionales"

    # =============================
    #   FILAS
    # =============================
    filas_html = ""

    if resultados:
        for r in resultados:

            # ---- Coordenadas ----
            coords = r.get("coordenadas_GPS") or []
            lat, lon = (coords[0], coords[1]) if len(coords) >= 2 else ("-", "-")
            enlace_mapa = f"https://www.google.com/maps?q={lat},{lon}" if lat != "-" else "#"

            # ---- Fecha / Hora ISO ----
            f = r.get("fecha", "")
            h = r.get("hora", "")
            fecha_fmt = f"{f[:4]}-{f[4:6]}-{f[6:]}" if isinstance(f, str) and len(f) == 8 else (f or "")
            hora_fmt = (h or "").replace(":", ".", 3)
            fecha_hora_iso = f"{fecha_fmt}T{hora_fmt}" if fecha_fmt and hora_fmt else f"{fecha_fmt}{hora_fmt}"
            fecha_txt = fecha_fmt or "—"
            hora_txt = hora_fmt or "—"

            # ---- Incidencias (solo icono/botón) ----
            inc_ids = r.get("incidencias_ids", []) or []
            num_inc = len(inc_ids)

            if num_inc > 0:
                # SOLO comillas simples + llamada directa. Nada de template literals.
                inc_html = (
                    "<button type='button' class='btn btn-warning btn-sm' "
                    "title='Ver incidencias relacionadas' "
                    "onclick=\"abrirModalIncidenciasMedicion("
                    f"'{r.get('id_tramo','')}',"
                    f"'{r.get('id_via','')}',"
                    f"'{r.get('pto_km','')}',"
                    f"'{r.get('fecha','')}',"
                    f"'{r.get('hora','')}'"
                    "); return false;\">"
                    "<i class='bi bi-exclamation-triangle-fill me-1'></i>"
                    "Ver incidencias "
                    f"<span class='badge bg-dark ms-1'>{num_inc}</span>"
                    "</button>"
                )
            else:
                inc_html = "<span class='badge bg-success'>Sin incidencias</span>"

            filas_html += f"""
            
<tr class="fila-medicion" style="cursor:pointer;">
    <td>{r.get('id_tramo','')}</td>
    <td>{r.get('id_via','')}</td>
    <td>{r.get('pto_km','')}</td>
    <td>{fecha_txt}</td>
    <td>{hora_txt}</td>
</tr>

<tr class="detalle-medicion d-none">
<td colspan="5">
<div class="p-3 border rounded bg-light text-center">

    <p>
        <i class="bi bi-geo-alt-fill"></i>
        Coordenadas: <strong>{lat}</strong>, <strong>{lon}</strong>
        · <a href="{enlace_mapa}" target="_blank">Ver en mapa</a>
    </p>

    <hr>

    <h5><i class="bi bi-rulers"></i> Altura y posición LAC</h5>
    <div class="d-flex justify-content-center flex-wrap gap-2 mb-3">
        <span class="badge bg-primary">Altura LAC: {r.get('altura_LAC')}</span>
        <span class="badge bg-info">Flecha: {r.get('flecha')}</span>
        <span class="badge bg-success">Contraflecha: {r.get('contraflecha')}</span>
        <span class="badge bg-danger">Descentramiento: {r.get('descentramiento')}</span>
    </div>

    <h5><i class="bi bi-bezier2"></i> Geometría y vía</h5>
    <div class="mb-3">
        Pendiente: <strong>{r.get('pendiente')}</strong> ·
        Variación: <strong>{r.get('variacion_pendiente')}</strong> ·
        Radio: <strong>{r.get('radio_curvatura')}</strong>
    </div>

    <h5><i class="bi bi-exclamation-triangle-fill"></i> Incidencias relacionadas</h5>
    <div class="mb-3">{inc_html}</div>

    <h5><i class="bi bi-gear-fill"></i> Otros parámetros técnicos</h5>
    <div class="mb-2">
        <a href="{r.get('video_url', '#')}" target="_blank" class="btn btn-dark btn-sm">
            <i class="bi bi-camera-video-fill"></i> Ver vídeo
        </a>
    </div>

    <div class="small text-muted">
        Presión hidráulica: {r.get('presion_hidraulica')} ·
        Tensión batería: {r.get('tension_bateria')} mV
    </div>

</div>
</td>
</tr>
"""

    else:
        filas_html = """
<tr>
<td colspan="5" class="text-center text-muted">
No se encontraron resultados.
</td>
</tr>
"""

    # =============================
    #   JS “BLINDADO” (NO f-string)
    # =============================
    js = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  var filas = document.querySelectorAll(".fila-medicion");
  filas.forEach(function (fila) {
    fila.addEventListener("click", function () {
      var detalle = fila.nextElementSibling;
      if (detalle) detalle.classList.toggle("d-none");
    });
  });
  buildPaginatorPairs(".fila-medicion", "filasPorPaginaMed", "paginacionMediciones", "infoPaginaMed");
});

function buildPaginatorPairs(mainSelector, selectorId, navUlId, infoId) {
  const selector = document.getElementById(selectorId);
  const navUl = document.getElementById(navUlId);
  const info = document.getElementById(infoId);
  if (!selector) return;
  let paginaActual = 1;
  function mainRows() { return Array.from(document.querySelectorAll(mainSelector)); }
  function renderPagina() {
    const todas = mainRows();
    const porPagina = parseInt(selector.value);
    const total = todas.length;
    if (porPagina === 0) {
      todas.forEach(r => { r.style.display = ''; });
      navUl.innerHTML = '';
      info.textContent = total + ' registros';
      return;
    }
    const totalPaginas = Math.ceil(total / porPagina);
    if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;
    const inicio = (paginaActual - 1) * porPagina;
    const fin = inicio + porPagina;
    todas.forEach((r, i) => {
      const visible = i >= inicio && i < fin;
      r.style.display = visible ? '' : 'none';
      const det = r.nextElementSibling;
      if (det && !visible) det.style.display = 'none';
      else if (det && visible) det.style.display = '';
    });
    const desde = total === 0 ? 0 : inicio + 1;
    const hasta = Math.min(fin, total);
    info.textContent = desde + '–' + hasta + ' de ' + total + ' registros';
    navUl.innerHTML = '';
    function addBtn(p) {
      const li = document.createElement('li');
      li.className = 'page-item' + (p === paginaActual ? ' active' : '');
      li.innerHTML = '<a class="page-link" href="#">' + p + '</a>';
      li.addEventListener('click', function(e) { e.preventDefault(); paginaActual = p; renderPagina(); });
      navUl.appendChild(li);
    }
    function addEllipsis() {
      const li = document.createElement('li');
      li.className = 'page-item disabled';
      li.innerHTML = '<span class="page-link">…</span>';
      navUl.appendChild(li);
    }
    const liFirst = document.createElement('li');
    liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
    liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
    liFirst.addEventListener('click', function(e) { e.preventDefault(); if (paginaActual !== 1) { paginaActual = 1; renderPagina(); } });
    navUl.appendChild(liFirst);
    const liPrev = document.createElement('li');
    liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
    liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
    liPrev.addEventListener('click', function(e) { e.preventDefault(); if (paginaActual > 1) { paginaActual--; renderPagina(); } });
    navUl.appendChild(liPrev);
    const rango = 2;
    let desde_p = Math.max(1, paginaActual - rango);
    let hasta_p = Math.min(totalPaginas, paginaActual + rango);
    if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
    if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));
    if (desde_p > 1) { addBtn(1); if (desde_p > 2) addEllipsis(); }
    for (let p = desde_p; p <= hasta_p; p++) addBtn(p);
    if (hasta_p < totalPaginas) { if (hasta_p < totalPaginas - 1) addEllipsis(); addBtn(totalPaginas); }
    const liNext = document.createElement('li');
    liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
    liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
    liNext.addEventListener('click', function(e) { e.preventDefault(); if (paginaActual < totalPaginas) { paginaActual++; renderPagina(); } });
    navUl.appendChild(liNext);
    const liLast = document.createElement('li');
    liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
    liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
    liLast.addEventListener('click', function(e) { e.preventDefault(); if (paginaActual !== totalPaginas) { paginaActual = totalPaginas; renderPagina(); } });
    navUl.appendChild(liLast);
  }
  selector.addEventListener('change', function() { paginaActual = 1; renderPagina(); });
  renderPagina();
}

function abrirIncidencia(docId) {
  fetch("/incidencia-detalle?doc_id=" + encodeURIComponent(docId))
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    })
    .then(function (html) {
      var cont = document.getElementById("modal-incidencia-container");
      if (cont) cont.innerHTML = html;

      var el = document.getElementById("modal-incidencia");
      if (!el) {
        console.error("El servidor no devolvió #modal-incidencia");
        return;
      }
      new bootstrap.Modal(el).show();
    })
    .catch(function (err) {
      console.error(err);
      alert("No se pudo cargar la incidencia.");
    });
}

function abrirModalIncidenciasMedicion(id_tramo, id_via, pto_km, fecha, hora) {
  var url = "/incidencias-medicion?"
    + "id_tramo=" + encodeURIComponent(id_tramo)
    + "&id_via=" + encodeURIComponent(id_via)
    + "&pto_km=" + encodeURIComponent(pto_km)
    + "&fecha=" + encodeURIComponent(fecha)
    + "&hora=" + encodeURIComponent(hora);

  fetch(url)
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.text();
    })
    .then(function (html) {
      // elimina modal anterior si existe
      var existente = document.getElementById("modal-incidencias");
      if (existente) existente.remove();

      // inserta el nuevo modal
      var cont = document.getElementById("modal-incidencias-container");
      if (cont) cont.innerHTML = html;

      var modalEl = document.getElementById("modal-incidencias");
      if (!modalEl) {
        console.error("El servidor no devolvió #modal-incidencias");
        return;
      }
      new bootstrap.Modal(modalEl).show();
    })
    .catch(function (err) {
      console.error("Error cargando incidencias:", err);
      alert("No se pudieron cargar las incidencias.");
    });
}
</script>
"""

    # =============================
    #   HTML FINAL
    # =============================
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Resultados de Mediciones</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
</head>

<body class="bg-light">

<div class="container py-4">
  <h1 class="h3 mb-3">Resultados de Mediciones</h1>

  <div class="card mb-4">
    <div class="card-body">
      <strong>Filtros:</strong><br>{filtros_html}
    </div>
  </div>

  <!-- Botón Volver encima de la tabla, a la derecha -->
  <div class="d-flex justify-content-end mb-2">
    <a href="/consultar-datos" class="btn btn-primary btn-sm">
      <i class="bi bi-arrow-left me-1"></i>Volver Atrás
    </a>
  </div>

  <table class="table table-hover align-middle text-center" id="tablaMediciones">
   <thead class="table-primary">
    <tr>
        <th>Tramo</th>
        <th>Vía</th>
        <th>PK</th>
        <th>Fecha</th>
        <th>Hora</th>
    </tr>
    </thead>
    <tbody id="tbodyMediciones">
      {filas_html}
    </tbody>
  </table>

  <!-- Controles de paginación -->
  <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
    <div class="d-flex align-items-center gap-2">
      <label for="filasPorPaginaMed" class="form-label mb-0 text-muted small">Mostrar</label>
      <select id="filasPorPaginaMed" class="form-select form-select-sm" style="width:auto;">
        <option value="10" selected>10</option>
        <option value="15">15</option>
        <option value="20">20</option>
        <option value="50">50</option>
        <option value="0">Todos</option>
      </select>
      <span class="text-muted small">filas por página</span>
    </div>
    <div class="d-flex align-items-center gap-3 flex-wrap">
      <span id="infoPaginaMed" class="text-muted small"></span>
      <nav><ul class="pagination pagination-sm mb-0" id="paginacionMediciones"></ul></nav>
    </div>
  </div>
</div>

<!-- Contenedores de modales inyectados por fetch() -->
<div id="modal-incidencia-container"></div>
<div id="modal-incidencias-container"></div>

<!-- Bootstrap primero -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>

{js}

</body>
</html>
"""



def page_consultar_datos_inspecciones_resultados(
    tramo: str,
    via: str,
    pto_km_ini: Optional[float],
    pto_km_fin: Optional[float],
    fecha_inicio: Optional[str],
    fecha_fin: Optional[str],
    resultados: List[Dict[str, Any]],
) -> str:

    # Formatear PK y Fechas
    pk_text = f"PK inicio: {pto_km_ini or '—'} · PK fin: {pto_km_fin or '—'}"
    fechas_text = f"Fecha inicio: {fecha_inicio or '—'} · Fecha fin: {fecha_fin or '—'}"

    # =======================
    #  Construcción de filas
    # =======================
    filas_html = ""

    if resultados:
        for r in resultados:
            errores_raw = r.get("num_errores", 0)
            try:
                errores = int(errores_raw) if errores_raw not in (None, "") else 0
            except (TypeError, ValueError):
                errores = 0
            badge_color = "bg-danger" if errores > 0 else "bg-success"

            filas_html += f"""
            <tr class="fila-inspeccion" style="cursor:pointer;">
                <td class="text-center"><i class="bi bi-signpost-2"></i> {r.get('id_tramo','')}</td>
                <td class="text-center"><i class="bi bi-diagram-3"></i> {r.get('id_via','')}</td>
                <td class="text-center"><i class="bi bi-rulers"></i> {r.get('num_km','')}</td>
                <td class="text-center">
                    <span class="badge {badge_color} px-3 py-2">
                        <i class="bi bi-exclamation-triangle-fill"></i> {errores}
                    </span>
                </td>
                <td class="text-center"><i class="bi bi-calendar-event"></i> {r.get('fecha','')}</td>
            </tr>

            <tr class="detalle-inspeccion d-none">
                <td colspan="5">
                    <div class="p-4 card shadow-sm text-center">

                        <h5 class="text-primary mb-4">
                            <i class="bi bi-search"></i> Detalle de inspección
                        </h5>

                        <div class="row justify-content-center">

                            <!-- Creación -->
                            <div class="col-md-5 mb-3">
                                <div class="border rounded bg-light p-3 h-100">
                                    <h6 class="text-info">
                                        <i class="bi bi-clock-history me-2"></i> Creado
                                    </h6>
                                    <p class="mb-1"><strong>{r.get('created_at','—')}</strong></p>
                                    <p class="mb-0 text-muted"><i class="bi bi-person-fill"></i> {r.get('created_by','—')}</p>
                                </div>
                            </div>

                            <!-- Actualización -->
                            <div class="col-md-5 mb-3">
                                <div class="border rounded bg-light p-3 h-100">
                                    <h6 class="text-warning">
                                        <i class="bi bi-arrow-repeat me-2"></i> Actualizado
                                    </h6>
                                    <p class="mb-1"><strong>{r.get('updated_at','—')}</strong></p>
                                    <p class="mb-0 text-muted"><i class="bi bi-person-fill"></i> {r.get('updated_by','—')}</p>
                                </div>
                            </div>

                        </div>

                    </div>
                </td>
            </tr>
            """
    else:
        filas_html = """
        <tr>
            <td colspan="5" class="text-center py-4 text-muted">
                No se han encontrado inspecciones para los filtros seleccionados.
            </td>
        </tr>
        """

    # =======================
    #  HTML COMPLETO
    # =======================
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Resultados de Inspecciones</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">

    <style>
        body {{
            background-color: #f5f7fb;
        }}
        .card-resumen {{
            border-radius: 18px;
            border: none;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.05);
        }}
        .fila-inspeccion:hover {{
            background-color: #eef4ff !important;
        }}
        .detalle-inspeccion td {{
            background-color: #f9fcff;
        }}
        .card {{
            border-radius: 14px;
        }}
    </style>
</head>

<body>

<!-- NAVBAR -->
{NAV_HTML}

<div class="container py-4">

    <h1 class="h3 mb-3">Resultados de Inspecciones</h1>

    <!-- RESUMEN -->
    <div class="card card-resumen mb-4">
        <div class="card-body">
            <h5 class="card-title mb-1">Tramo {tramo} · Vía {via}</h5>
            <p class="mb-0 small text-muted">
                {fechas_text}<br>{pk_text}
            </p>
        </div>
    </div>

    <!-- TABLA PRINCIPAL -->
    <!-- Botón Volver encima de la tabla, a la derecha -->
    <div class="d-flex justify-content-end mb-2">
        <a href="/consultar-datos" class="btn btn-primary btn-sm">
            <i class="bi bi-arrow-left me-1"></i>Volver Atrás
        </a>
    </div>
    <div class="card shadow-sm">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0 text-center" id="tablaInspecciones">
                    <thead class="table-primary">
                        <tr>
                            <th>Tramo</th>
                            <th>Vía</th>
                            <th>Nº kilómetros</th>
                            <th>Errores</th>
                            <th>Fecha</th>
                        </tr>
                    </thead>
                    <tbody id="tbodyInspecciones">
                        {filas_html}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Controles de paginación -->
    <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
        <div class="d-flex align-items-center gap-2">
            <label for="filasPorPaginaInsp" class="form-label mb-0 text-muted small">Mostrar</label>
            <select id="filasPorPaginaInsp" class="form-select form-select-sm" style="width:auto;">
                <option value="10" selected>10</option>
                <option value="15">15</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="0">Todos</option>
            </select>
            <span class="text-muted small">filas por página</span>
        </div>
        <div class="d-flex align-items-center gap-3 flex-wrap">
            <span id="infoPaginaInsp" class="text-muted small"></span>
            <nav><ul class="pagination pagination-sm mb-0" id="paginacionInspecciones"></ul></nav>
        </div>
    </div>

</div>

<script>
document.addEventListener("DOMContentLoaded", function () {{
    // Toggle detalle
    document.querySelectorAll(".fila-inspeccion").forEach(function (fila) {{
        fila.addEventListener("click", function () {{
            const detalle = fila.nextElementSibling;
            if (detalle && detalle.classList.contains("detalle-inspeccion")) {{
                detalle.classList.toggle("d-none");
            }}
        }});
    }});

    // Paginación
    buildPaginatorPairs(".fila-inspeccion", "filasPorPaginaInsp", "paginacionInspecciones", "infoPaginaInsp");
}});

function buildPaginatorPairs(mainSelector, selectorId, navUlId, infoId) {{
    const selector = document.getElementById(selectorId);
    const navUl = document.getElementById(navUlId);
    const info = document.getElementById(infoId);
    if (!selector) return;
    let paginaActual = 1;

    function mainRows() {{ return Array.from(document.querySelectorAll(mainSelector)); }}

    function renderPagina() {{
        const todas = mainRows();
        const porPagina = parseInt(selector.value);
        const total = todas.length;

        if (porPagina === 0) {{
            todas.forEach(r => {{ r.style.display = ''; }});
            navUl.innerHTML = '';
            info.textContent = total + ' registros';
            return;
        }}

        const totalPaginas = Math.ceil(total / porPagina);
        if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;
        const inicio = (paginaActual - 1) * porPagina;
        const fin = inicio + porPagina;
        todas.forEach((r, i) => {{
            const visible = i >= inicio && i < fin;
            r.style.display = visible ? '' : 'none';
            const detalle = r.nextElementSibling;
            if (detalle && !visible) detalle.style.display = 'none';
            else if (detalle && visible) detalle.style.display = '';
        }});

        const desde = total === 0 ? 0 : inicio + 1;
        const hasta = Math.min(fin, total);
        info.textContent = desde + '–' + hasta + ' de ' + total + ' registros';

        navUl.innerHTML = '';
        function addBtn(p) {{
            const li = document.createElement('li');
            li.className = 'page-item' + (p === paginaActual ? ' active' : '');
            li.innerHTML = '<a class="page-link" href="#">' + p + '</a>';
            li.addEventListener('click', function(e) {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
            navUl.appendChild(li);
        }}
        function addEllipsis() {{
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<span class="page-link">…</span>';
            navUl.appendChild(li);
        }}
        const liFirst = document.createElement('li');
        liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
        liFirst.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
        navUl.appendChild(liFirst);
        const liPrev = document.createElement('li');
        liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
        liPrev.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
        navUl.appendChild(liPrev);

        const rango = 2;
        let desde_p = Math.max(1, paginaActual - rango);
        let hasta_p = Math.min(totalPaginas, paginaActual + rango);
        if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
        if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));

        if (desde_p > 1) {{ addBtn(1); if (desde_p > 2) addEllipsis(); }}
        for (let p = desde_p; p <= hasta_p; p++) addBtn(p);
        if (hasta_p < totalPaginas) {{ if (hasta_p < totalPaginas - 1) addEllipsis(); addBtn(totalPaginas); }}

        const liNext = document.createElement('li');
        liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
        liNext.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
        navUl.appendChild(liNext);

        const liLast = document.createElement('li');
        liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
        liLast.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
        navUl.appendChild(liLast);
    }}

    selector.addEventListener('change', function() {{ paginaActual = 1; renderPagina(); }});
    renderPagina();
}}
</script>

</body>
</html>
"""

def page_consultar_datos_incidencias_resultados(
    tramo,
    via,
    pto_km_ini,
    pto_km_fin,
    fecha_inicio,
    fecha_fin,
    resultados,
) -> str:

    # -----------------------------------------------------
    # Construcción de filas (tbody) + detalle desplegable
    # -----------------------------------------------------
    filas_html = ""

    def _fmt(v):
        return "{:.2f}".format(v) if isinstance(v, (int, float)) else (v or "—")

    def _nivel_badge(nivel):
        try:
            n = int(nivel)
        except Exception:
            n = None
        if n == 1:
            return '<span class="badge badge-nivel badge-nivel-1">Nivel 1</span>'
        if n == 2:
            return '<span class="badge badge-nivel badge-nivel-2">Nivel 2</span>'
        if n == 3:
            return '<span class="badge badge-nivel badge-nivel-3">Nivel 3</span>'
        if n == 4:
            return '<span class="badge badge-nivel badge-nivel-4">Nivel 4</span>'
        return f'<span class="badge badge-nivel badge-nivel-0">{nivel if nivel is not None else "—"}</span>'

    for grupo in resultados:
        id_tramo = grupo.get("id_tramo", "—")
        id_via = grupo.get("id_via", "—")
        pto_km = grupo.get("pto_km", "—")
        fecha = grupo.get("fecha", "—")
        hora = grupo.get("hora", "—")
        num_inc = grupo.get("num_incidencias", 0)
        tiene_medicion = bool(grupo.get("tiene_medicion", False))

        coords = grupo.get("coordenadas_GPS") or []
        lat, lon = (coords[0], coords[1]) if isinstance(coords, (list, tuple)) and len(coords) >= 2 else ("—", "—")

        enlace_mapa = (
            "https://www.google.com/maps?q={lat},{lon}".format(lat=lat, lon=lon)
            if lat != "—" else "#"
        )

        TIPO_DESC = {
            "KPIT1": "Incidencia de altura (m)",
            "KPIT2": "Incidencia de descentramiento (cm)",
            "KPIT3": "Incidencia de pendiente (‰)",
            "KPIT4": "Incidencia de variación de pendiente (‰)",
            "KPIT5": "Incidencia de flecha (%)",
            "KPIT6": "Incidencia de contraflecha (mm)",
            "KPIT7": "Incidencia de tijera (mm)",
            "KPIT8": "Zona de contacto con el pantógrafo (mm)",
            "KPIT9": "Incidencia por otras causas",
        }
        SUBTIPO_DESC = {
            "rec": "Descentramiento en recta",
            "cpo": "Descentramiento en curva — poste",
            "cva": "Descentramiento en curva — vano",
            "com": "Defecto de compensación",
            "gal": "Gálibo reducido",
            "mon": "Montaje",
        }

        incidencias_rows = ""
        for inc in grupo.get("incidencias", []) or []:
            try:
                nivel_num = int(inc.get("nivel"))
            except Exception:
                nivel_num = None
            es_critica = nivel_num in (3, 4)

            if es_critica:
                revisada = inc.get("revision") is True
                revision_fecha = inc.get("revision_fecha") or ""
                if revisada:
                    revision_html = (
                        '<span class="badge bg-success">Sí</span>'
                        + (f'<br><small class="text-muted">{revision_fecha}</small>' if revision_fecha else "")
                    )
                else:
                    revision_html = '<span class="badge bg-secondary">Pendiente</span>'
            else:
                revision_html = ""

            tipo = inc.get("tipo", "—")
            subtipo = inc.get("subtipo", "—")
            tipo_desc = TIPO_DESC.get(tipo, "")
            subtipo_desc = SUBTIPO_DESC.get(subtipo, "")
            tipo_td = (
                f'<span class="badge bg-info text-dark" data-bs-toggle="tooltip" '
                f'data-bs-placement="top" title="{tipo_desc}">{tipo}</span>'
                if tipo_desc else
                f'<span class="badge bg-info text-dark">{tipo}</span>'
            )
            subtipo_td = (
                f'<span data-bs-toggle="tooltip" data-bs-placement="top" '
                f'title="{subtipo_desc}">{subtipo}</span>'
                if subtipo_desc else subtipo
            )

            incidencias_rows += """
<tr>
  <td>{nivel_badge}</td>
  <td>{poste}</td>
  <td>{tipo_td}</td>
  <td>{subtipo_td}</td>
  <td>{valor_medido}</td>
  <td>{valor_ref}</td>
  <td>{revision}</td>
</tr>
""".format(
                nivel_badge=_nivel_badge(inc.get("nivel")),
                poste=inc.get("poste", "—"),
                tipo_td=tipo_td,
                subtipo_td=subtipo_td,
                valor_medido=_fmt(inc.get("valor_medido")),
                valor_ref=_fmt(inc.get("valor_referencia")),
                revision=revision_html,
            )

        link_medicion = ""
        if tiene_medicion:
            link_medicion = """
<p class="mb-2">
  <strong>Medición relacionada:</strong>
  <a href="#" class="link-medicion"
     onclick="event.preventDefault(); event.stopPropagation();
              abrirModalMedicion('{id_tramo}','{id_via}','{pto_km}','{fecha}','{hora}')">
     Ver detalle de la medición
  </a>
</p>
""".format(
                id_tramo=id_tramo,
                id_via=id_via,
                pto_km=pto_km,
                fecha=fecha,
                hora=hora,
            )

        filas_html += """
<tr class="fila-incidencia" style="cursor:pointer;">
  <td>{id_tramo}</td>
  <td>{id_via}</td>
  <td>{pto_km}</td>
  <td>{fecha}</td>
  <td>{hora}</td>
  <td><span class="badge bg-danger">{num_inc}</span></td>
</tr>

<tr class="detalle-incidencia d-none">
  <td colspan="6">
    <div class="p-3 border rounded bg-light detalle-box">
      <p class="mb-1"><strong>Coordenadas:</strong> {lat}, {lon}</p>
      {link_medicion}

      <a href="{mapa}" target="_blank" class="btn btn-outline-primary btn-sm mb-3">
        Ver en mapa
      </a>

      <div class="detalle-title"><span class="detalle-title-icon">⚠</span> Detalle de incidencias</div>

      <div class="table-responsive">
        <table class="table table-sm table-bordered table-incidencias-detalle">
          <thead>
            <tr>
              <th>Nivel</th>
              <th>Poste</th>
              <th>Tipo</th>
              <th>Subtipo</th>
              <th>Valor medido</th>
              <th>Valor referencia</th>
              <th>Revisada</th>
            </tr>
          </thead>
          <tbody>
            {incidencias_rows}
          </tbody>
        </table>
      </div>
    </div>
  </td>
</tr>
""".format(
            id_tramo=id_tramo,
            id_via=id_via,
            pto_km=pto_km,
            fecha=fecha,
            hora=hora,
            num_inc=num_inc,
            lat=lat,
            lon=lon,
            mapa=enlace_mapa,
            incidencias_rows=incidencias_rows,
            link_medicion=link_medicion,
        )

    # -----------------------------------------------------
    # Página completa (mantiene Bootstrap + estilos + modal)
    # -----------------------------------------------------
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Resultados de Incidencias</title>

  <!-- Bootstrap (igual que el resto de páginas) -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">

  <style>
    body {{ background: #f6f7fb; }}

    .nav-link:hover {{
      transform: scale(1.1);
      transition: transform 0.3s linear;
    }}

    .card-resumen {{ border: 1px solid #e5e7eb; }}

    .badge-nivel {{ padding: .35rem .55rem; border-radius: .5rem; font-weight: 700; font-size: .75rem; }}
    .badge-nivel-1 {{ background: #0f766e; color: #fff; }}
    .badge-nivel-2 {{ background: #f59e0b; color: #111827; }}
    .badge-nivel-3 {{ background: #dc2626; color: #fff; }}
    .badge-nivel-4 {{ background: #7f1d1d; color: #fff; }}
    .badge-nivel-0 {{ background: #6b7280; color: #fff; }}

    .detalle-box {{ background: #ffffff !important; }}
    .detalle-title {{
      display: flex; align-items: center; gap: .5rem;
      font-weight: 800; color: #b91c1c;
      border-top: 1px solid #e5e7eb;
      padding-top: .75rem; margin-top: .75rem;
    }}
    .detalle-title-icon {{ font-size: 1rem; }}

    .table-incidencias-detalle thead th {{ background: #eef2ff; }}

    /* Evita que el modal “baile” al abrir/cerrar */
    .modal-open {{ padding-right: 0 !important; }}
  </style>
</head>
<body>

    {NAV_HTML}

  <div class="container my-4">

    <div class="d-flex justify-content-between align-items-center mb-3">
      <h1 class="h3 m-0">Resultados de Incidencias</h1>
    </div>

    <div class="card card-resumen mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-3"><strong>Tramo:</strong> {tramo or '—'}</div>
          <div class="col-md-2"><strong>Vía:</strong> {via or '—'}</div>
          <div class="col-md-3"><strong>PK inicio/fin:</strong> {pto_km_ini or '—'} / {pto_km_fin or '—'}</div>
          <div class="col-md-4"><strong>Fecha inicio/fin:</strong> {fecha_inicio or '—'} / {fecha_fin or '—'}</div>
        </div>
      </div>
    </div>

    <!-- Botón Volver encima de la tabla, a la derecha -->
    <div class="d-flex justify-content-end mb-2">
      <a href="/consultar-datos" class="btn btn-primary btn-sm">
        <i class="bi bi-arrow-left me-1"></i>Volver Atrás
      </a>
    </div>

    <div class="table-responsive">
      <table class="table table-bordered table-hover align-middle" id="tablaIncidencias">
        <thead class="table-primary">
          <tr>
            <th>Id Tramo</th>
            <th>Vía</th>
            <th>Pto Km</th>
            <th>Fecha</th>
            <th>Hora</th>
            <th>N° Incidencias</th>
          </tr>
        </thead>
        <tbody id="tbodyIncidencias">
          {filas_html}
        </tbody>
      </table>
    </div>

    <!-- Controles de paginación -->
    <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
      <div class="d-flex align-items-center gap-2">
        <label for="filasPorPaginaInc" class="form-label mb-0 text-muted small">Mostrar</label>
        <select id="filasPorPaginaInc" class="form-select form-select-sm" style="width:auto;">
          <option value="10" selected>10</option>
          <option value="15">15</option>
          <option value="20">20</option>
          <option value="50">50</option>
          <option value="0">Todos</option>
        </select>
        <span class="text-muted small">filas por página</span>
      </div>
      <div class="d-flex align-items-center gap-3 flex-wrap">
        <span id="infoPaginaInc" class="text-muted small"></span>
        <nav><ul class="pagination pagination-sm mb-0" id="paginacionIncidencias"></ul></nav>
      </div>
    </div>

  </div>

  <!-- Contenedor para inyectar el HTML del modal de medición -->
  <div id="modal-medicion-container"></div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

  <script>
    // Toggle de detalle (fila + fila siguiente)
    document.addEventListener('DOMContentLoaded', function() {{
      document.querySelectorAll('.fila-incidencia').forEach(function(fila) {{
        fila.addEventListener('click', function() {{
          const detalle = fila.nextElementSibling;
          if (!detalle || !detalle.classList.contains('detalle-incidencia')) return;
          detalle.classList.toggle('d-none');
        }});
      }});
      buildPaginatorPairs('.fila-incidencia', 'filasPorPaginaInc', 'paginacionIncidencias', 'infoPaginaInc');
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el) {{
        new bootstrap.Tooltip(el);
      }});
    }});

    function buildPaginatorPairs(mainSelector, selectorId, navUlId, infoId) {{
      const selector = document.getElementById(selectorId);
      const navUl = document.getElementById(navUlId);
      const info = document.getElementById(infoId);
      if (!selector) return;
      let paginaActual = 1;
      function mainRows() {{ return Array.from(document.querySelectorAll(mainSelector)); }}
      function renderPagina() {{
        const todas = mainRows();
        const porPagina = parseInt(selector.value);
        const total = todas.length;
        if (porPagina === 0) {{
          todas.forEach(r => {{ r.style.display = ''; }});
          navUl.innerHTML = '';
          info.textContent = total + ' registros';
          return;
        }}
        const totalPaginas = Math.ceil(total / porPagina);
        if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;
        const inicio = (paginaActual - 1) * porPagina;
        const fin = inicio + porPagina;
        todas.forEach((r, i) => {{
          const visible = i >= inicio && i < fin;
          r.style.display = visible ? '' : 'none';
          const det = r.nextElementSibling;
          if (det && !visible) det.style.display = 'none';
          else if (det && visible) det.style.display = '';
        }});
        const desde = total === 0 ? 0 : inicio + 1;
        const hasta = Math.min(fin, total);
        info.textContent = desde + '–' + hasta + ' de ' + total + ' registros';
        navUl.innerHTML = '';
        function addBtn(p) {{
          const li = document.createElement('li');
          li.className = 'page-item' + (p === paginaActual ? ' active' : '');
          li.innerHTML = '<a class="page-link" href="#">' + p + '</a>';
          li.addEventListener('click', function(e) {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
          navUl.appendChild(li);
        }}
        function addEllipsis() {{
          const li = document.createElement('li');
          li.className = 'page-item disabled';
          li.innerHTML = '<span class="page-link">…</span>';
          navUl.appendChild(li);
        }}
        const liFirst = document.createElement('li');
        liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
        liFirst.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
        navUl.appendChild(liFirst);
        const liPrev = document.createElement('li');
        liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
        liPrev.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
        navUl.appendChild(liPrev);
        const rango = 2;
        let desde_p = Math.max(1, paginaActual - rango);
        let hasta_p = Math.min(totalPaginas, paginaActual + rango);
        if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
        if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));
        if (desde_p > 1) {{ addBtn(1); if (desde_p > 2) addEllipsis(); }}
        for (let p = desde_p; p <= hasta_p; p++) addBtn(p);
        if (hasta_p < totalPaginas) {{ if (hasta_p < totalPaginas - 1) addEllipsis(); addBtn(totalPaginas); }}
        const liNext = document.createElement('li');
        liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
        liNext.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
        navUl.appendChild(liNext);
        const liLast = document.createElement('li');
        liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
        liLast.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
        navUl.appendChild(liLast);
      }}
      selector.addEventListener('change', function() {{ paginaActual = 1; renderPagina(); }});
      renderPagina();
    }}

    // Abre modal con el detalle de la medición relacionada (misma clave)
    async function abrirModalMedicion(id_tramo, id_via, pto_km, fecha, hora) {{
      try {{
        const params = new URLSearchParams({{ id_tramo, id_via, pto_km, fecha, hora }});
        const resp = await fetch('/medicion-detalle?' + params.toString(), {{ headers: {{ 'X-Requested-With': 'fetch' }} }});
        const html = await resp.text();

        const container = document.getElementById('modal-medicion-container');
        container.innerHTML = html;

        const modalEl = document.getElementById('modal-medicion');
        if (!modalEl) {{
          console.error('No se encontró #modal-medicion en la respuesta de /medicion-detalle');
          return;
        }}

        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      }} catch (e) {{
        console.error('Error abriendo modal de medición:', e);
        alert('No se pudo cargar el detalle de la medición.');
      }}
    }}
  </script>

</body>
</html>
"""



def page_consultar_datos_formularios_resultados(
    tramo,
    via,
    pto_km_ini,
    pto_km_fin,
    fecha_inicio,
    fecha_fin,
    resultados
):
    # Normalizar textos
    fecha_ini_txt = fecha_inicio or "—"
    fecha_fin_txt = fecha_fin or "—"
    pk_ini_txt = str(pto_km_ini) if pto_km_ini is not None else "—"
    pk_fin_txt = str(pto_km_fin) if pto_km_fin is not None else "—"

    filas_html = ""

    for form in resultados:
        tipo = form.get("tipo", "—")
        id_tramo = form.get("id_tramo", "—")
        id_via = form.get("id_via", "—")
        pki = form.get("pto_km_ini", "—")
        pkf = form.get("pto_km_fin", "—")
        fecha = form.get("fecha", "—")
        fid = form.get("id", "")

        # 1. Personas 
        personas = form.get("Personal-cargo") or []
        
        personas_table_rows = ""
        for p in personas:
            personal_name = p.get('Personal', 'Sin nombre')
            cargo_name = p.get('Cargo', 'Sin cargo')
            personas_table_rows += f"""
                <tr>
                    <td><i class="bi bi-person me-2 text-muted"></i>{personal_name}</td>
                    <td>{cargo_name}</td>
                </tr>
            """
        
        if personas_table_rows:
            # Diseño HTML basado en tabla con flex para centrar
            personas_html = f"""
                <div class="d-flex justify-content-center mt-3">
                    <table class="table table-sm table-striped table-bordered w-auto mb-0 text-start">
                        <thead class="table-success">
                            <tr><th>Nombre</th><th>Cargo</th></tr>
                        </thead>
                        <tbody>
                            {personas_table_rows}
                        </tbody>
                    </table>
                </div>
            """
        else:
            personas_html = '<p class="mb-0 text-muted fs-6 mt-3">—</p>'

        vehiculos = form.get("Vehiculos") or []
        vehiculos_html = "".join(
            f"<span class='badge bg-info text-dark me-2 mb-2 fs-6'><i class='bi bi-truck me-2'></i>{v.get('Vehiculo', '')}</span>"
            for v in vehiculos
        ) or "—"

        subtr_html = ""
        subtr = form.get("subtramnos") or []
        for s in subtr:
            for clave, valores in s.items():
                subtr_html += f"""
                <tr>
                    <td>{clave}</td>
                    <td>{valores[0]}</td>
                    <td>{valores[1]}</td>
                </tr>
                """
        if not subtr_html:
            subtr_html = "<tr><td colspan='3'>—</td></tr>"

        # 4. Operaciones 
        ops_html = ""
        ops = form.get("operaciones") or []
        for op in ops:
            op_id = op.get("Id", "—")
            ops_html += f"<tr><td><strong>{op_id}</strong></td><td>"
            ops_html += "".join(
                f"<span class='badge bg-success me-1'>{k}: {v}</span>"
                for k, v in op.items() if k.startswith("R")
            )
            ops_html += "</td></tr>"

        if not ops_html:
            ops_html = "<tr><td colspan='2'>—</td></tr>"

        # Fila principal
        filas_html += f"""
        <tr class="fila-formulario" style="cursor:pointer;">
            <td>{id_tramo}</td>
            <td>{id_via}</td>
            <td>{tipo}</td>
            <td>{pki}</td>
            <td>{pkf}</td>
            <td>{fecha}</td>
        </tr>

          <tr class="detalle-formulario d-none">
            <td colspan="6">
    <div class="p-4 border rounded bg-light">

        <div class="text-center mb-4">
            <i class="bi bi-fingerprint text-primary" style="font-size: 1.4rem;"></i>
            <p class="mt-2 mb-0 small text-muted">
                <strong>ID formulario:</strong> {fid}
            </p>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-clock-history text-info me-2" style="font-size: 1.5rem;"></i>
                    Horarios
                </h5>
                <p class="mb-1">🕒 Hora corte tensión: <strong>{form.get('hora_corte_tension','—')}</strong></p>
                <p class="mb-1">🔌 Hora restablecimiento: <strong>{form.get('hora_restb_tension','—')}</strong></p>
                <p class="mb-1">🚧 Hora inicio trabajos: <strong>{form.get('hora_ini_trabajos','—')}</strong></p>
                <p class="mb-0">🏁 Hora fin trabajos: <strong>{form.get('hora_fin_trabajos','—')}</strong></p>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-person-badge text-warning me-2" style="font-size: 1.5rem;"></i>
                    Responsable
                </h5>
                <p class="fw-bold fs-5">{form.get('responsable_corte','—')}</p>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-repeat text-secondary me-2" style="font-size: 1.5rem;"></i>
                    Periodicidad
                </h5>
                <span class="badge bg-secondary fs-6 px-3 py-2">
                    {form.get('periodicidad', '—')}
                </span>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-stopwatch text-danger me-2" style="font-size: 1.5rem;"></i>
                    Horas
                </h5>
                <p class="fs-5 mb-0">⏱ Desplazamiento: <strong>{form.get('horas_desplazamiento','—')}</strong></p>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-people-fill text-success me-2" style="font-size: 1.5rem;"></i>
                    Personal y Cargo
                </h5>
                {personas_html}
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-car-front-fill text-info me-2" style="font-size: 1.5rem;"></i>
                    Vehículos
                </h5>
                <div class="d-flex flex-wrap justify-content-center mt-3">
                    {vehiculos_html}
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title mb-3">
                    <i class="bi bi-diagram-3-fill text-primary me-2" style="font-size: 1.5rem;"></i>
                    Subtramos
                </h5>
                <div class="d-flex justify-content-center">
                    <table class="table table-sm table-bordered w-auto mb-0">
                        <thead class="table-secondary">
                            <tr><th>Cod</th><th>Ini</th><th>Fin</th></tr>
                        </thead>
                        <tbody>{subtr_html}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-tools text-dark me-2" style="font-size: 1.5rem;"></i>
                    Operaciones
                </h5>
                <div class="d-flex justify-content-center">
                    <table class="table table-sm table-bordered w-auto mb-0">
                        <thead class="table-secondary">
                            <tr><th>ID</th><th>Resultados</th></tr>
                        </thead>
                        <tbody>{ops_html}</tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-body text-center">
                <h5 class="card-title">
                    <i class="bi bi-journal-text text-purple me-2" style="font-size: 1.5rem;"></i>
                    Metadatos
                </h5>
                <p class="small mb-0">
                    ✍️ Creado por <strong>{form.get('created_by','—')}</strong> ({form.get('created_at','—')})<br>
                    🔄 Actualizado por <strong>{form.get('updated_by','—')}</strong> ({form.get('updated_at','—')})
                </p>
            </div>
        </div>

    </div>
</td>

        """

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Resultados de Formularios</title>

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">

    <style>
        body {{ background-color: #f5f7fb; }}
        .fila-formulario:hover {{ background: #eef4ff; }}
        .detalle-formulario td {{ background: #f9fcff; }}
        /* Aseguramos que la cabecera de la tabla de personas sea verde suave */
        .table-success {{ background-color: #d1e7dd; border-color: #bcd0c7; }}
    </style>
</head>
<body>

{NAV_HTML}

<div class="container py-4">

    <h1 class="h3 mb-3">Resultados de Formularios</h1>

    <div class="card card-resumen mb-4">
        <div class="card-body">
            <h5 class="card-title mb-2">
                Tramo {tramo or "—"} · Vía {via or "—"}
            </h5>
            <p class="mb-1 small text-muted">
                <strong>Fecha inicio:</strong> {fecha_ini_txt}
                &nbsp;·&nbsp;
                <strong>Fecha fin:</strong> {fecha_fin_txt}
            </p>
            <p class="mb-0 small text-muted">
                <strong>PK inicio:</strong> {pk_ini_txt}
                &nbsp;·&nbsp;
                <strong>PK fin:</strong> {pk_fin_txt}
            </p>
        </div>
    </div>

    <!-- Botón Volver encima de la tabla, a la derecha -->
    <div class="d-flex justify-content-end mb-2">
        <a href="/consultar-datos" class="btn btn-primary btn-sm">
            <i class="bi bi-arrow-left me-1"></i>Volver Atrás
        </a>
    </div>

    <div class="table-responsive">
        <table class="table table-hover align-middle text-center" id="tablaFormularios">
            <thead class="table-primary">
                <tr>
                    <th>Id Tramo</th>
                    <th>Vía</th>
                    <th>Tipo</th>
                    <th>PK Inicio</th>
                    <th>PK Fin</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody id="tbodyFormularios">
                {filas_html}
            </tbody>
        </table>
    </div>

    <!-- Controles de paginación -->
    <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
        <div class="d-flex align-items-center gap-2">
            <label for="filasPorPaginaForm" class="form-label mb-0 text-muted small">Mostrar</label>
            <select id="filasPorPaginaForm" class="form-select form-select-sm" style="width:auto;">
                <option value="10" selected>10</option>
                <option value="15">15</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="0">Todos</option>
            </select>
            <span class="text-muted small">filas por página</span>
        </div>
        <div class="d-flex align-items-center gap-3 flex-wrap">
            <span id="infoPaginaForm" class="text-muted small"></span>
            <nav><ul class="pagination pagination-sm mb-0" id="paginacionFormularios"></ul></nav>
        </div>
    </div>

</div>

<script>
document.addEventListener("DOMContentLoaded", function() {{
    document.querySelectorAll(".fila-formulario").forEach(function(fila) {{
        fila.addEventListener("click", function() {{
            let det = fila.nextElementSibling;
            if (det && det.classList.contains("detalle-formulario")) {{
                det.classList.toggle("d-none");
            }}
        }});
    }});
    buildPaginatorPairs(".fila-formulario", "filasPorPaginaForm", "paginacionFormularios", "infoPaginaForm");
}});

function buildPaginatorPairs(mainSelector, selectorId, navUlId, infoId) {{
    const selector = document.getElementById(selectorId);
    const navUl = document.getElementById(navUlId);
    const info = document.getElementById(infoId);
    if (!selector) return;
    let paginaActual = 1;
    function mainRows() {{ return Array.from(document.querySelectorAll(mainSelector)); }}
    function renderPagina() {{
        const todas = mainRows();
        const porPagina = parseInt(selector.value);
        const total = todas.length;
        if (porPagina === 0) {{
            todas.forEach(r => {{ r.style.display = ''; }});
            navUl.innerHTML = '';
            info.textContent = total + ' registros';
            return;
        }}
        const totalPaginas = Math.ceil(total / porPagina);
        if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;
        const inicio = (paginaActual - 1) * porPagina;
        const fin = inicio + porPagina;
        todas.forEach((r, i) => {{
            const visible = i >= inicio && i < fin;
            r.style.display = visible ? '' : 'none';
            const det = r.nextElementSibling;
            if (det && !visible) det.style.display = 'none';
            else if (det && visible) det.style.display = '';
        }});
        const desde = total === 0 ? 0 : inicio + 1;
        const hasta = Math.min(fin, total);
        info.textContent = desde + '–' + hasta + ' de ' + total + ' registros';
        navUl.innerHTML = '';
        function addBtn(p) {{
            const li = document.createElement('li');
            li.className = 'page-item' + (p === paginaActual ? ' active' : '');
            li.innerHTML = '<a class="page-link" href="#">' + p + '</a>';
            li.addEventListener('click', function(e) {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
            navUl.appendChild(li);
        }}
        function addEllipsis() {{
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<span class="page-link">…</span>';
            navUl.appendChild(li);
        }}
        const liFirst = document.createElement('li');
        liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
        liFirst.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
        navUl.appendChild(liFirst);
        const liPrev = document.createElement('li');
        liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
        liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
        liPrev.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
        navUl.appendChild(liPrev);
        const rango = 2;
        let desde_p = Math.max(1, paginaActual - rango);
        let hasta_p = Math.min(totalPaginas, paginaActual + rango);
        if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
        if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));
        if (desde_p > 1) {{ addBtn(1); if (desde_p > 2) addEllipsis(); }}
        for (let p = desde_p; p <= hasta_p; p++) addBtn(p);
        if (hasta_p < totalPaginas) {{ if (hasta_p < totalPaginas - 1) addEllipsis(); addBtn(totalPaginas); }}
        const liNext = document.createElement('li');
        liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
        liNext.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
        navUl.appendChild(liNext);
        const liLast = document.createElement('li');
        liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
        liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
        liLast.addEventListener('click', function(e) {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
        navUl.appendChild(liLast);
    }}
    selector.addEventListener('change', function() {{ paginaActual = 1; renderPagina(); }});
    renderPagina();
}}
</script>


</body>
</html>
"""

def page_umbrales(
    umbrales: Sequence[Mapping[str, str]],
    mensaje_html: str = "",
    query_params: Optional[Mapping[str, Sequence[str]]] = None
) -> str:
    
    query_params = query_params or {}
    buscar_tipo = query_params.get('buscar_tipo', [''])[0].strip() if query_params else ""

    # Guardamos la lista completa para poblar el SELECT (necesita todos los
    # tipos disponibles, no solo los del filtro actual).
    umbrales_originales = list(umbrales)
    tipos_disponibles = sorted({
        str(u.get("tipo", "")).strip()
        for u in umbrales_originales
        if str(u.get("tipo", "")).strip()
    })

    # Filtro por tipo si viene query (mensajito como en Tramos)
    mensaje_busqueda = ""
    if buscar_tipo:
        umbrales = [
            u for u in umbrales
            if buscar_tipo.lower() in str(u.get("tipo", "")).lower()
        ]
        total = len(umbrales)
        if total:
            mensaje_busqueda = f'''
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                Se encontraron {total} resultado(s) para <strong>{buscar_tipo}</strong>.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''
        else:
            mensaje_busqueda = f'''
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                No se encontraron umbrales con el tipo <strong>{buscar_tipo}</strong>.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            '''

    # Mensajes de éxito/error (mismo patrón que Tramos)
    if 'success' in query_params:
        mensaje_html = f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            {query_params["success"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''
    elif 'error' in query_params:
        mensaje_html = f'''
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            {query_params["error"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    # Filas de tabla
    filas_html = ""
    for u in umbrales:
        doc_id           = u.get("doc_id", "")
        tipo             = u.get("tipo", "")
        tipologia        = u.get("tipologia", "")
        velocidad        = u.get("velocidad", "")
        valor_referencia = u.get("valor_referencia", "")
        n1 = " - ".join(u.get("valores_N1", []) or [])
        n2 = " - ".join(u.get("valores_N2", []) or [])
        n3 = " - ".join(u.get("valores_N3", []) or [])
        n4_raw = u.get("valores_N4", [])
        n4 = " - ".join(n4_raw) if n4_raw else ""

        filas_html += f'''
        <tr>
            <td>{tipo}</td>
            <td>{tipologia}</td>
            <td>{'' if velocidad is None else velocidad}</td>
            <td>{valor_referencia}</td>
            <td>{n1}</td>
            <td>{n2}</td>
            <td>{n3}</td>
            <td>{n4}</td>
            <td>
                <!-- Botón Editar -->
                <button type="button" class="btn btn-sm btn-outline-primary"
                        data-bs-toggle="modal" data-bs-target="#editarModal{doc_id}">
                    <i class="bi bi-pencil-fill"></i>
                </button>
                <!-- Botón Eliminar -->
                <button type="button" class="btn btn-sm btn-outline-danger"
                        data-bs-toggle="modal" data-bs-target="#eliminarModal{doc_id}">
                    <i class="bi bi-trash-fill"></i>
                </button>
                <!-- Modal Editar Umbral -->
                <div class="modal fade" id="editarModal{doc_id}" tabindex="-1"
                    aria-labelledby="editarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="editarModalLabel{doc_id}">Editar Umbral</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <form id="formEditarUmbral{doc_id}" class="formEditarUmbral" action="/umbrales/{doc_id}/editar" method="POST">
                                <input type="hidden" name="doc_id" value="{doc_id}">
                                <div class="modal-body">
                                    <div class="alert alert-danger d-none editarErrorBox" role="alert"></div>
                                    <div class="row g-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Tipo</label>
                                            <input type="text" class="form-control" name="tipo" value="{tipo}" required readonly>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Tipología</label>
                                            <input type="text" class="form-control" name="tipologia" value="{tipologia}" readonly>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Velocidad</label>
                                            <input type="number" class="form-control" name="velocidad" min="0" step="1" value="{'' if velocidad is None else velocidad}" readonly>
                                            <div class="form-text">Sólo para pendiente / var_pendiente</div>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Valor referencia</label>
                                            <input type="text" class="form-control" name="valor_referencia" value="{valor_referencia}" required>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">N1 (min,max)</label>
                                            <input type="text" class="form-control" name="valores_N1" value="{n1.replace(' - ' , '-')}" required>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">N2 (min,max)</label>
                                            <input type="text" class="form-control" name="valores_N2" value="{n2.replace(' - ', '-')}" required>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">N3 (min,max)</label>
                                            <input type="text" class="form-control" name="valores_N3" value="{n3.replace(' - ', '-')}" required>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">N4 (min,max)</label>
                                            <input type="text" class="form-control" name="valores_N4" value="{n4.replace(' - ', '-') if n4 else ''}">
                                        </div>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                    <button type="submit" class="btn btn-primary">Guardar Cambios</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
                <!-- Modal Eliminar Umbral -->
                <div class="modal fade" id="eliminarModal{doc_id}" tabindex="-1"
                    aria-labelledby="eliminarModalLabel{doc_id}" aria-hidden="true">
                    <div class="modal-dialog"><div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="eliminarModalLabel{doc_id}">Confirmar Eliminación</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        ¿Estás seguro de que deseas eliminar el umbral
                        <span class="fw-bold">{tipo}</span> - <span class="fw-bold">{tipologia}</span>?
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <form action="/umbrales/{doc_id}/eliminar" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-danger">Eliminar</button>
                        </form>
                    </div>
                    </div></div>
                </div>
            </td>
        </tr>
        '''

    if not filas_html.strip():
        filas_html = '<tr><td colspan="9" class="text-center text-muted">Sin resultados</td></tr>'

    html_response = f'''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Umbrales</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        .navbar-brand img {{ height: 40px; }}
        .volver-btn {{ margin-top: 10px; }}
    </style>
</head>
<body>
    <!-- Encabezado/Nav igual que Tramos -->
        {NAV_HTML}

    <div class="container py-5">
        {mensaje_html}
        {mensaje_busqueda}
        <div class="d-flex align-items-center gap-2 mb-3">
          <span style="width:120px"></span>
          <h1 class="h1 text-center mb-0 flex-grow-1"><i class="bi bi-signpost-2-fill"></i> Umbrales</h1>
          <a href="/configuracion" class="btn btn-primary btn-sm volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
        </div>

        <div class="mb-4 d-flex justify-content-between">
            <div class="ms-3">
                <form class="row g-3 mb-1" method="GET" action="/umbrales">
                    <div class="col-auto">
                        <select class="form-select border border-secondary" name="buscar_tipo"
                                onchange="this.form.submit()" style="min-width: 260px;">
                            <option value="">📋 Todos los tipos</option>
                            <option value="" disabled>──────────</option>
                            {''.join(f'<option value="{t}" {"selected" if t == buscar_tipo else ""}>{t}</option>' for t in tipos_disponibles)}
                        </select>
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-outline-secondary mb-3">
                            <i class="bi bi-search"></i> Buscar Tipo
                        </button>
                    </div>
                </form>
            </div>
            <div class="me-3">
                <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#nuevoUmbralModal">
                    <i class="bi bi-plus-lg"></i> Agregar Nuevo Umbral
                </button>
            </div>
        </div>

        <div class="table-responsive">
            <table class="table table-hover table-bordered align-middle text-center" id="tablaUmbrales">
                <thead class="table-primary">
                    <tr>
                        <th>Tipo</th>
                        <th>Tipología</th>
                        <th>Velocidad</th>
                        <th>Valor referencia</th>
                        <th>N1</th>
                        <th>N2</th>
                        <th>N3</th>
                        <th>N4</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody id="tbodyUmbrales">
                    {filas_html}
                </tbody>
            </table>
        </div>

        <!-- Controles de paginación -->
        <div class="d-flex justify-content-between align-items-center mt-2 flex-wrap gap-2">
            <div class="d-flex align-items-center gap-2">
                <label for="filasPorPaginaU" class="form-label mb-0 text-muted small">Mostrar</label>
                <select id="filasPorPaginaU" class="form-select form-select-sm" style="width:auto;">
                    <option value="10" selected>10</option>
                    <option value="15">15</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="0">Todos</option>
                </select>
                <span class="text-muted small">filas por página</span>
            </div>
            <div class="d-flex align-items-center gap-3 flex-wrap">
                <span id="infoPaginaU" class="text-muted small"></span>
                <nav>
                    <ul class="pagination pagination-sm mb-0" id="paginacionUmbrales"></ul>
                </nav>
            </div>
        </div>
    </div>

    <!-- Modal Nuevo Umbral (estilo igual al de Nuevo Tramo) -->
    <div class="modal fade" id="nuevoUmbralModal" tabindex="-1" aria-labelledby="nuevoUmbralLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="nuevoUmbralLabel">Nuevo Umbral</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form id="formNuevoUmbral" action="/umbrales/nuevo" method="POST">
                    <div class="modal-body">
                        <div id="altaError" class="alert alert-danger d-none" role="alert"></div>
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label">Tipo</label>
                                <select class="form-select" name="tipo" required>
                                    <option value="" disabled selected>Selecciona un tipo</option>
                                    {''.join(f'<option value="{t}">{t}</option>' for t in tipos_disponibles)}
                                </select>
                                <div class="form-text">Tipos existentes en el catálogo de umbrales.</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Tipología</label>
                                <input type="text" class="form-control" name="tipologia">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Velocidad</label>
                                <input type="number" class="form-control" name="velocidad" min="0" step="1">
                                <div class="form-text">Sólo para pendiente / var_pendiente</div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Valor referencia</label>
                                <input type="text" class="form-control" name="valor_referencia">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">N1 (min,max)</label>
                                <input type="text" class="form-control" name="valores_N1" placeholder="ej. 4.55 - 4.59">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">N2 (min,max)</label>
                                <input type="text" class="form-control" name="valores_N2" placeholder="ej. 4.50 - 4.55">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">N3 (min,max)</label>
                                <input type="text" class="form-control" name="valores_N3" placeholder="ej. 4.45 - 4.50">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">N4 (min,max)</label>
                                <input type="text" class="form-control" name="valores_N4" placeholder="opcional, ej. 0 - 4.45">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-primary">Guardar</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    <script>
    // ── Paginación Umbrales ─────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {{
        const tbody = document.getElementById('tbodyUmbrales');
        const selector = document.getElementById('filasPorPaginaU');
        const navUl = document.getElementById('paginacionUmbrales');
        const info = document.getElementById('infoPaginaU');
        let paginaActual = 1;

        function filas() {{ return Array.from(tbody.querySelectorAll('tr')); }}

        function renderPagina() {{
            const todas = filas();
            const porPagina = parseInt(selector.value);
            const total = todas.length;

            if (porPagina === 0) {{
                todas.forEach(r => r.style.display = '');
                navUl.innerHTML = '';
                info.textContent = total + ' registros';
                return;
            }}

            const totalPaginas = Math.ceil(total / porPagina);
            if (paginaActual > totalPaginas) paginaActual = totalPaginas || 1;

            const inicio = (paginaActual - 1) * porPagina;
            const fin = inicio + porPagina;
            todas.forEach((r, i) => r.style.display = (i >= inicio && i < fin) ? '' : 'none');

            const desde = total === 0 ? 0 : inicio + 1;
            const hasta = Math.min(fin, total);
            info.textContent = `${{desde}}–${{hasta}} de ${{total}} registros`;

            navUl.innerHTML = '';

            function addPageBtn(p) {{
                const li = document.createElement('li');
                li.className = 'page-item' + (p === paginaActual ? ' active' : '');
                li.innerHTML = `<a class="page-link" href="#">${{p}}</a>`;
                li.addEventListener('click', e => {{ e.preventDefault(); paginaActual = p; renderPagina(); }});
                navUl.appendChild(li);
            }}
            function addEllipsis() {{
                const li = document.createElement('li');
                li.className = 'page-item disabled';
                li.innerHTML = '<span class="page-link">…</span>';
                navUl.appendChild(li);
            }}

            // Primera
            const liFirst = document.createElement('li');
            liFirst.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
            liFirst.innerHTML = '<a class="page-link" href="#" title="Primera página">|&laquo;</a>';
            liFirst.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== 1) {{ paginaActual = 1; renderPagina(); }} }});
            navUl.appendChild(liFirst);

            // Anterior
            const liPrev = document.createElement('li');
            liPrev.className = 'page-item' + (paginaActual === 1 ? ' disabled' : '');
            liPrev.innerHTML = '<a class="page-link" href="#">&laquo;</a>';
            liPrev.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual > 1) {{ paginaActual--; renderPagina(); }} }});
            navUl.appendChild(liPrev);

            const rango = 2;
            let desde_p = Math.max(1, paginaActual - rango);
            let hasta_p = Math.min(totalPaginas, paginaActual + rango);
            if (paginaActual - rango < 1) hasta_p = Math.min(totalPaginas, hasta_p + (rango - paginaActual + 1));
            if (paginaActual + rango > totalPaginas) desde_p = Math.max(1, desde_p - (paginaActual + rango - totalPaginas));

            if (desde_p > 1) {{ addPageBtn(1); if (desde_p > 2) addEllipsis(); }}
            for (let p = desde_p; p <= hasta_p; p++) addPageBtn(p);
            if (hasta_p < totalPaginas) {{ if (hasta_p < totalPaginas - 1) addEllipsis(); addPageBtn(totalPaginas); }}

            // Siguiente
            const liNext = document.createElement('li');
            liNext.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
            liNext.innerHTML = '<a class="page-link" href="#">&raquo;</a>';
            liNext.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual < totalPaginas) {{ paginaActual++; renderPagina(); }} }});
            navUl.appendChild(liNext);

            // Última
            const liLast = document.createElement('li');
            liLast.className = 'page-item' + (paginaActual === totalPaginas || totalPaginas === 0 ? ' disabled' : '');
            liLast.innerHTML = '<a class="page-link" href="#" title="Última página">&raquo;|</a>';
            liLast.addEventListener('click', e => {{ e.preventDefault(); if (paginaActual !== totalPaginas) {{ paginaActual = totalPaginas; renderPagina(); }} }});
            navUl.appendChild(liLast);
        }}

        selector.addEventListener('change', () => {{ paginaActual = 1; renderPagina(); }});
        renderPagina();
    }});
    </script>

    <script>
    document.addEventListener('DOMContentLoaded', function () {{
        async function submitCrudAjax(form, logLabel) {{
            const action = form.getAttribute('action') || '';
            const data = new FormData(form);
            const response = await fetch(action, {{
                method: 'POST',
                body: data,
                credentials: 'same-origin',
                headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
            }});
            const html = await response.text();
            document.open();
            document.write(html);
            document.close();
        }}

        // ====== ALTA ======
        var formNuevo = document.getElementById('formNuevoUmbral');   // <form id="formNuevoUmbral"...>
        var errorNuevo = document.getElementById('altaError');         // <div id="altaError"...>
        var bypassNuevo = false;

        if (formNuevo) {{
            formNuevo.addEventListener('submit', async function (e) {{
            if (bypassNuevo) return;     // segundo submit: ya validado
            e.preventDefault();

            if (errorNuevo) {{
                errorNuevo.classList.add('d-none');
                errorNuevo.textContent = '';
            }}

            try {{
                // x-www-form-urlencoded (el backend parsea con parse_qs)
                var fd = new FormData(formNuevo);
                var params = new URLSearchParams();
                fd.forEach(function (v, k) {{ params.append(k, v); }});

                var res = await fetch('/umbrales/validar', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' }},
                body: params.toString()
                }});
                if (!res.ok) throw new Error('HTTP ' + res.status);
                var data = await res.json();

                if (data.ok) {{
                bypassNuevo = true;
                await submitCrudAjax(formNuevo, 'nuevo');
                return;
                }}

                if (errorNuevo) {{
                errorNuevo.textContent = data.message || 'Datos de umbral inválidos';
                errorNuevo.classList.remove('d-none');
                }}
                if (data.field) {{
                var inputEl = formNuevo.querySelector('[name="' + data.field + '"]');
                if (inputEl) {{
                    inputEl.focus();
                    if (inputEl.select) inputEl.select();
                }}
                }}
            }} catch (err) {{
                if (errorNuevo) {{
                errorNuevo.textContent = 'No se pudo validar. Inténtelo de nuevo.';
                errorNuevo.classList.remove('d-none');
                }}
            }}
            }});
        }}

        // ====== EDICIÓN (múltiples formularios) ======
        var editForms = document.querySelectorAll('.formEditarUmbral'); // cada fila tiene uno
        var bypassMap = new WeakMap();                                   // marca por formulario

        editForms.forEach(function (form) {{
            form.addEventListener('submit', async function (e) {{
            if (bypassMap.get(form)) return;   // segundo submit: ya validado
            e.preventDefault();

            var errorBox = form.querySelector('.editarErrorBox'); // el div que añadimos en el modal
            if (errorBox) {{
                errorBox.classList.add('d-none');
                errorBox.textContent = '';
            }}

            try {{
                var fd = new FormData(form);
                var params = new URLSearchParams();
                fd.forEach(function (v, k) {{ params.append(k, v); }});

                var res = await fetch('/umbrales/validar', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' }},
                body: params.toString()
                }});
                if (!res.ok) throw new Error('HTTP ' + res.status);
                var data = await res.json();

                if (data.ok) {{
                bypassMap.set(form, true);
                await submitCrudAjax(form, 'editar');
                return;
                }}

                if (errorBox) {{
                errorBox.textContent = data.message || 'Datos de umbral inválidos';
                errorBox.classList.remove('d-none');
                }}
                if (data.field) {{
                var inputEl = form.querySelector('[name="' + data.field + '"]');
                if (inputEl) {{
                    inputEl.focus();
                    if (inputEl.select) inputEl.select();
                }}
                }}
            }} catch (err) {{
                if (errorBox) {{
                errorBox.textContent = 'No se pudo validar. Inténtelo de nuevo.';
                errorBox.classList.remove('d-none');
                }}
            }}
            }});
        }});

        var deleteForms = document.querySelectorAll('form[action^="/umbrales/"][action$="/eliminar"]');
        deleteForms.forEach(function(form) {{
            form.addEventListener('submit', async function(e) {{
                e.preventDefault();
                try {{
                    await submitCrudAjax(form, 'eliminar');
                }} catch (err) {{
                    console.error('Error AJAX CRUD umbrales:', err);
                    form.submit();
                }}
            }});
        }});
        }});
    </script>



    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
</body>
</html>
'''
    
    return html_response

def page_operaciones( partes, grupos, subgrupos, seleccion_parte: str = "", seleccion_grupo: str = "", mensaje_html: str = "", filtro_codigo: str = "", query_params: dict = None, ver_todas: bool = False, todas_operaciones: list = None) -> str:
    
    query_params = query_params or {}

    if 'success' in query_params:
        mensaje_html = f'''
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            {query_params["success"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''
    elif 'error' in query_params:
        mensaje_html = f'''
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            {query_params["error"][0]}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    # Opciones combos
    # Opción especial al principio del desplegable de Parte: "Ver todas las operaciones".
    opcion_todas = (
        '<option value="__todas__" {sel}>📋 Ver todo</option>'
        '<option value="" disabled>──────────</option>'
    ).format(sel="selected" if ver_todas else "")

    opciones_partes = opcion_todas + ''.join(
        f'<option value="{p}" {"selected" if (not ver_todas and p == seleccion_parte) else ""}>{p}</option>'
        for p in partes
    )
    opciones_grupos = ''.join(
        f'<option value="{g["id"]}" {"selected" if g["id"] == seleccion_grupo else ""}>{g["id"]} - {g["nombre"]}</option>'
        for g in grupos
    )

    # Modo "ver todas": cada fila lleva su propia parte/id_grupo (no hay seleccion global)
    # Modo "por filtros": parte e id_grupo vienen de seleccion_parte / seleccion_grupo
    items_render = []
    if ver_todas:
        for op in (todas_operaciones or []):
            items_render.append({
                "parte": op.get("parte", "") or "",
                "id_grupo": op.get("id_grupo", "") or "",
                "nombre_grupo": op.get("nombre_grupo", "") or "",
                "codigo": op.get("codigo", "") or "",
                "descripcion": op.get("descripcion", "") or "",
            })
    else:
        for sg in subgrupos:
            items_render.append({
                "parte": seleccion_parte,
                "id_grupo": seleccion_grupo,
                "nombre_grupo": "",
                "codigo": sg.get("codigo", "") or "",
                "descripcion": sg.get("descripcion", "") or "",
            })

    filas_html = ''
    for idx, it in enumerate(items_render):
        codigo = it["codigo"]
        desc   = it["descripcion"]
        row_parte = it["parte"]
        row_grupo = it["id_grupo"]
        # ID único por fila: en ver_todas el mismo código puede repetirse en distintas
        # parte/grupo, así que mezclamos parte + grupo + código + índice.
        modal_uid = f"{row_parte}_{row_grupo}_{codigo}_{idx}".replace('.', '_').replace(' ', '_').replace('/', '_').replace('\\', '_').replace('"', '').replace("'", '')

        cols_extra = ''
        if ver_todas:
            cols_extra = f"""
          <td>{row_parte}</td>
          <td class="text-start">{row_grupo} - {it["nombre_grupo"]}</td>"""

        filas_html += f"""
        <tr>{cols_extra}
          <td>{codigo}</td>
          <td class="text-start">{desc}</td>
          <td>
            <button type="button" class="btn btn-sm btn-outline-primary me-1" data-bs-toggle="modal" data-bs-target="#editar{modal_uid}">
              <i class="bi bi-pencil-fill"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#eliminar{modal_uid}">
              <i class="bi bi-trash-fill"></i>
            </button>

            <!-- Modal Editar -->
            <div class="modal fade" id="editar{modal_uid}" tabindex="-1">
              <div class="modal-dialog"><div class="modal-content">
                <div class="modal-header"><h5 class="modal-title">Editar subgrupo</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form action="/operaciones/editar" method="POST">
                  <div class="modal-body">
                    <input type="hidden" name="parte" value="{row_parte}">
                    <input type="hidden" name="id_grupo" value="{row_grupo}">
                    <input type="hidden" name="codigo_original" value="{codigo}">
                    <div class="mb-3"><label class="form-label">Parte</label>
                      <input class="form-control" value="{row_parte}" disabled>
                    </div>
                    <div class="mb-3"><label class="form-label">Grupo</label>
                      <input class="form-control" value="{row_grupo} - {it['nombre_grupo']}" disabled>
                    </div>
                    <div class="mb-3"><label class="form-label">Código</label>
                      <input class="form-control" value="{codigo}" disabled>
                      <input type="hidden" name="codigo" value="{codigo}">
                    </div>
                    <div class="mb-3"><label class="form-label">Descripción</label>
                      <textarea class="form-control" name="descripcion" rows="3" required>{desc}</textarea></div>
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Guardar cambios</button>
                  </div>
                </form>
              </div></div>
            </div>

            <!-- Modal Eliminar -->
            <div class="modal fade" id="eliminar{modal_uid}" tabindex="-1">
              <div class="modal-dialog"><div class="modal-content">
                <div class="modal-header"><h5 class="modal-title">Confirmar eliminación</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                  ¿Eliminar el subgrupo <strong>{codigo}</strong> de <strong>{row_parte}</strong> / grupo <strong>{row_grupo}</strong>?
                </div>
                <div class="modal-footer">
                  <form action="/operaciones/eliminar" method="POST">
                    <input type="hidden" name="parte" value="{row_parte}">
                    <input type="hidden" name="id_grupo" value="{row_grupo}">
                    <input type="hidden" name="codigo" value="{codigo}">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-danger">Eliminar</button>
                  </form>
                </div>
              </div></div>
            </div>

          </td>
        </tr>
        """

    colspan_vacio = 5 if ver_todas else 3
    if not filas_html.strip():
        filas_html = f'<tr><td colspan="{colspan_vacio}" class="text-center text-muted">Sin subgrupos para mostrar</td></tr>'

    # Cabecera de la tabla según el modo
    if ver_todas:
        thead_html = """
        <tr>
          <th style="width:160px">Parte</th>
          <th style="width:200px">Grupo</th>
          <th style="width:170px">Código</th>
          <th>Descripción</th>
          <th style="width:140px">Acciones</th>
        </tr>
        """
    else:
        thead_html = """
        <tr>
          <th style="width:170px">Código</th>
          <th>Descripción</th>
          <th style="width:140px">Acciones</th>
        </tr>
        """

    # Variables auxiliares para el modo "ver todas"
    # Importante: el select de Parte queda SIEMPRE habilitado (incluso en
    # modo "ver todas") porque la opción "Ver todas las operaciones" forma
    # parte del propio desplegable y queremos poder volver a una parte concreta.
    grupo_disabled = "disabled" if (ver_todas or not seleccion_parte) else ""
    nuevo_disabled = "disabled" if (ver_todas or not (seleccion_parte and seleccion_grupo)) else ""
    ver_todas_hidden = '<input type="hidden" name="ver_todas" value="1" id="hidden_ver_todas">' if ver_todas else ""

    info_modo_html = ""
    if ver_todas:
        total_n = len(items_render)
        info_modo_html = (
            f'<div class="alert alert-info py-2 mb-3"><i class="bi bi-info-circle"></i> '
            f'Mostrando el catálogo completo de operaciones ({total_n} '
            f'{"registro" if total_n == 1 else "registros"}). '
            f'Para filtrar por parte y grupo, vuelve a seleccionar uno en el desplegable.</div>'
        )

    # Página
    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Operaciones</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
  <link rel="shortcut icon" href="img/logo.png" type="image/x-icon">
</head>
<body class="bg-light">
{NAV_HTML}

<div class="container py-5">
  {mensaje_html}
  <!-- Cabecera con botón Volver arriba a la derecha (siempre visible, útil con paginación) -->
  <div class="d-flex align-items-center gap-2 mb-2">
    <span style="width:120px"></span>
    <h1 class="h1 text-center mb-0 flex-grow-1"><i class="bi bi-clipboard-check"></i> Operaciones</h1>
    <a href="/configuracion" class="btn btn-primary btn-sm volver-btn">
      <i class="bi bi-arrow-left me-1"></i>Volver Atrás
    </a>
  </div>

  {info_modo_html}

  <!-- Filtros -->
  <form class="row g-3 align-items-end mb-3" method="GET" action="/operaciones">
    {ver_todas_hidden}
    <div class="col-md-4">
      <label class="form-label">Parte</label>
      <select class="form-select" name="parte" id="select_parte_operaciones" onchange="onChangeParteOperaciones(this)">
        <option value="" disabled {"selected" if (not seleccion_parte and not ver_todas) else ""}>Selecciona un parte</option>
        {opciones_partes}
      </select>
    </div>
    <div class="col-md-4">
      <label class="form-label">Grupo</label>
      <select class="form-select" name="grupo" {grupo_disabled} onchange="this.form.submit()">
        <option value="" disabled {"selected" if not seleccion_grupo else ""}>Selecciona un grupo</option>
        {opciones_grupos}
      </select>
    </div>
    <div class="col-md-3">
      <label class="form-label">Buscar por código</label>
      <input class="form-control" name="buscar_codigo" value="{filtro_codigo}">
    </div>
    <div class="col-md-1">
      <button type="submit" class="btn btn-outline-secondary w-100"><i class="bi bi-search"></i></button>
    </div>
  </form>

  <!-- Barra de acciones -->
  <div class="d-flex justify-content-end gap-2 mb-2 flex-wrap">
    <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#confirmarActualizarTablas">
      <i class="bi bi-arrow-repeat"></i> Sincronizar tablet
    </button>
    <button class="btn btn-warning" data-bs-toggle="modal" data-bs-target="#nuevoGrupo">
      <i class="bi bi-folder-plus"></i> Nuevo grupo
    </button>
    <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#nuevoSubgrupo" {nuevo_disabled}>
      <i class="bi bi-plus-lg"></i> Nuevo subgrupo
    </button>
  </div>

  <!-- Modal Confirmar Actualización Tablet -->
  <div class="modal fade" id="confirmarActualizarTablas" tabindex="-1">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title"><i class="bi bi-arrow-repeat text-primary"></i> Sincronizar tablet</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form action="/operaciones/actualizar-tablas-tablet" method="POST">
        <div class="modal-body">
          <p class="mb-2">Se va a sincronizar el catálogo de operaciones (Maestro_Operaciones) con la tablet.</p>
          <p class="text-muted small mb-0">El proceso puede tardar unos segundos. No cierres esta ventana hasta recibir la confirmación.</p>
          <input type="hidden" name="parte" value="{seleccion_parte}">
          <input type="hidden" name="id_grupo" value="{seleccion_grupo}">
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-primary" id="btn-confirmar-actualizar">
            <i class="bi bi-arrow-repeat"></i> Sí, actualizar
          </button>
        </div>
      </form>
    </div></div>
  </div>
  <script>
    (function() {{
      var form = document.querySelector('#confirmarActualizarTablas form');
      if (!form) return;
      form.addEventListener('submit', function() {{
        var btn = document.getElementById('btn-confirmar-actualizar');
        if (btn) {{
          btn.disabled = true;
          btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Actualizando...';
        }}
      }});
    }})();
  </script>

  <!-- Modal Alta de Grupo -->
  <div class="modal fade" id="nuevoGrupo" tabindex="-1">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header bg-warning">
        <h5 class="modal-title"><i class="bi bi-folder-plus"></i> Nuevo grupo</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form action="/operaciones/grupo/nuevo" method="POST">
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label">Parte <span class="text-danger">*</span></label>
            <select class="form-select" name="parte" required>
              <option value="" disabled selected>Selecciona un parte</option>
              {''.join(f'<option value="{p}">{p}</option>' for p in partes)}
            </select>
            <div class="form-text">Selecciona un parte donde se creará el grupo.</div>
          </div>
          <div class="mb-3">
            <label class="form-label">ID del grupo <span class="text-danger">*</span></label>
            <input class="form-control" name="id_grupo" required maxlength="50"
                   placeholder="Ej. 7">
            <div class="form-text">Identificador numérico o textual único dentro de la parte.</div>
          </div>
          <div class="mb-3">
            <label class="form-label">Nombre <span class="text-danger">*</span></label>
            <input class="form-control" name="nombre" required maxlength="200"
                   placeholder="Nombre descriptivo del grupo">
          </div>
          <div class="alert alert-info py-2 small mb-0">
            <i class="bi bi-info-circle"></i> El grupo se creará vacío. Tras crearlo
            podrás añadir subgrupos directamente desde el botón <strong>Nuevo subgrupo</strong>.
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-warning"><i class="bi bi-check-lg"></i> Crear grupo</button>
        </div>
      </form>
    </div></div>
  </div>

  <!-- Modal Alta -->
  <div class="modal fade" id="nuevoSubgrupo" tabindex="-1">
    <div class="modal-dialog"><div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Nuevo subgrupo</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form action="/operaciones/nuevo" method="POST">
        <div class="modal-body">
          <input type="hidden" name="parte" value="{seleccion_parte}">
          <input type="hidden" name="id_grupo" value="{seleccion_grupo}">
          <div class="mb-3"><label class="form-label">Código</label><input class="form-control" name="codigo" required></div>
          <div class="mb-3"><label class="form-label">Descripción</label><textarea class="form-control" rows="3" name="descripcion" required></textarea></div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
          <button type="submit" class="btn btn-primary">Guardar</button>
        </div>
      </form>
    </div></div>
  </div>

  <!-- Tabla -->
  <div class="table-responsive shadow-sm rounded">
    <table class="table table-hover table-bordered align-middle" id="tablaOperaciones">
      <thead class="table-primary">
        {thead_html}
      </thead>
      <tbody id="tbodyOperaciones">
        {filas_html}
      </tbody>
    </table>
  </div>

  <!-- Controles de paginación (client-side) -->
  <nav aria-label="Paginación de operaciones" class="mt-3">
    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
      <div class="d-flex align-items-center gap-2">
        <label for="page_size_ops" class="form-label mb-0 small text-muted">Filas por página:</label>
        <select id="page_size_ops" class="form-select form-select-sm" style="width:auto;">
          <option value="10">10</option>
          <option value="25" selected>25</option>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="0">Todas</option>
        </select>
        <span class="small text-muted ms-2" id="info_pag_ops"></span>
      </div>
      <ul class="pagination pagination-sm mb-0" id="pag_ops"></ul>
    </div>
  </nav>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
<script>
  // ============================================================
  //   PAGINACIÓN CLIENT-SIDE de la tabla de Operaciones
  // ============================================================
  (function() {{
    var tbody = document.getElementById('tbodyOperaciones');
    var sel   = document.getElementById('page_size_ops');
    var ul    = document.getElementById('pag_ops');
    var info  = document.getElementById('info_pag_ops');
    if (!tbody || !sel || !ul) return;

    // Filas reales (excluye filas placeholder de "sin datos")
    var rows = Array.prototype.filter.call(
      tbody.querySelectorAll('tr'),
      function(tr) {{ return tr.cells.length > 1; }}
    );
    if (rows.length === 0) {{ ul.innerHTML = ''; if (info) info.textContent = ''; return; }}

    var pageSize = parseInt(sel.value, 10) || 25;
    var page = 1;

    function render() {{
      var size = pageSize === 0 ? rows.length : pageSize;
      var pages = Math.max(1, Math.ceil(rows.length / size));
      if (page > pages) page = pages;
      var start = (page - 1) * size;
      var end = start + size;
      rows.forEach(function(tr, i) {{
        tr.style.display = (i >= start && i < end) ? '' : 'none';
      }});

      // Info textual
      if (info) {{
        if (pageSize === 0) {{
          info.textContent = '· ' + rows.length + ' filas';
        }} else {{
          info.textContent = '· ' + (start + 1) + '–' + Math.min(end, rows.length) + ' de ' + rows.length;
        }}
      }}

      // Botones (Bootstrap pagination)
      var html = '';
      function btn(label, target, disabled, active) {{
        return '<li class="page-item ' + (disabled ? 'disabled' : '') + ' ' + (active ? 'active' : '') + '">'
             + '<a href="#" class="page-link" data-target="' + target + '">' + label + '</a></li>';
      }}
      html += btn('«', 1, page === 1, false);
      html += btn('‹', page - 1, page === 1, false);

      // Ventana de páginas (max 5)
      var winSize = 5;
      var winStart = Math.max(1, page - 2);
      var winEnd = Math.min(pages, winStart + winSize - 1);
      winStart = Math.max(1, winEnd - winSize + 1);
      for (var p = winStart; p <= winEnd; p++) {{
        html += btn(String(p), p, false, p === page);
      }}

      html += btn('›', page + 1, page === pages, false);
      html += btn('»', pages, page === pages, false);
      ul.innerHTML = html;
    }}

    ul.addEventListener('click', function(e) {{
      var a = e.target.closest('a.page-link');
      if (!a) return;
      e.preventDefault();
      var t = parseInt(a.getAttribute('data-target'), 10);
      if (!isNaN(t) && t >= 1) {{
        page = t;
        render();
        // Scroll a la tabla
        document.getElementById('tablaOperaciones').scrollIntoView({{behavior: 'smooth', block: 'start'}});
      }}
    }});

    sel.addEventListener('change', function() {{
      pageSize = parseInt(sel.value, 10) || 0;
      page = 1;
      render();
    }});

    render();
  }})();
</script>
<script>
  // Manejador del desplegable Parte: la opción especial "__todas__" navega
  // al modo "ver todas"; cualquier otra parte real navega al modo filtros
  // (limpiando ver_todas) y submitea el form para cargar los grupos.
  function onChangeParteOperaciones(sel) {{
    var v = sel.value;
    if (v === '__todas__') {{
      window.location.href = '/operaciones?ver_todas=1';
      return;
    }}
    // Parte normal: si veníamos del modo "ver todas", quitamos el hidden
    var hidden = document.getElementById('hidden_ver_todas');
    if (hidden && hidden.parentNode) {{
      hidden.parentNode.removeChild(hidden);
    }}
    // Reseteamos el grupo (cambia el contexto de parte) y submit
    var selGrupo = sel.form.querySelector('select[name="grupo"]');
    if (selGrupo) {{ selGrupo.value = ''; }}
    sel.form.submit();
  }}
</script>
<script>
  (function() {{
    document.querySelectorAll('form[method="POST"], form[method="post"]').forEach(function(form) {{
      var action = form.getAttribute('action') || '';
      if (!action.startsWith('/operaciones/')) return;
      form.addEventListener('submit', async function(e) {{
        e.preventDefault();
        try {{
          const data = new FormData(form);
          const res = await fetch(action, {{
            method: 'POST',
            body: data,
            credentials: 'same-origin',
            headers: {{ 'X-Requested-With': 'XMLHttpRequest' }}
          }});
          const html = await res.text();
          document.open();
          document.write(html);
          document.close();
        }} catch (err) {{
          console.error('Error AJAX CRUD operaciones:', err);
          form.submit();
        }}
      }});
    }});
  }})();
</script>

</body>
</html>
"""


def page_indicadores_operativa(opciones_html: str, error_message: Optional[str] = None) -> str:
    """
    Página principal del módulo Indicadores de Operativa.
    Permite seleccionar tramo, vía y rango de fechas.
    """
    alert = ""
    if error_message:
        alert = f'''
        <div class="alert alert-danger alert-dismissible fade show mt-3" role="alert">
            {error_message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        '''

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Indicadores de Operativa</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    </head>
    <body class="bg-light">
                {NAV_HTML}

        <div class="container my-5">
            <h1 class="text-center text-primary mb-4">Indicadores de Operativa</h1>
            {alert}

            <form method="POST" action="/indicadores_operativa" class="p-4 bg-white shadow rounded">
                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="tramo" class="form-label fw-bold">Tramo *</label>
                        <select id="tramo" name="tramo" class="form-select border-primary" required onchange="cargarVias()">
                            <option selected disabled>Selecciona un tramo</option>
                            {opciones_html}
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label for="via" class="form-label fw-bold">Vía *</label>
                        <select id="via" name="via" class="form-select border-primary" required>
                            <option selected disabled>Selecciona una vía</option>
                        </select>
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="pto_km_ini" class="form-label fw-bold">Punto km inicio</label>
                        <input type="number" class="form-control border-primary" id="pto_km_ini" name="pto_km_ini" step="0.1">
                    </div>
                    <div class="col-md-6">
                        <label for="pto_km_fin" class="form-label fw-bold">Punto km fin</label>
                        <input type="number" class="form-control border-primary" id="pto_km_fin" name="pto_km_fin" step="0.1">
                    </div>
                </div>

                <div class="row mb-3">
                    <div class="col-md-6">
                        <label for="fecha_inicio" class="form-label fw-bold">Fecha desde</label>
                        <input type="date" class="form-control border-primary" id="fecha_inicio" name="fecha_inicio">
                    </div>
                    <div class="col-md-6">
                        <label for="fecha_fin" class="form-label fw-bold">Fecha hasta</label>
                        <input type="date" class="form-control border-primary" id="fecha_fin" name="fecha_fin">
                    </div>
                </div>

                <div class="text-center mt-4">
                    <button type="submit" class="btn btn-primary px-4">Buscar</button>
                    <a href="/entrada" class="btn btn-primary px-4 volver-btn"><i class="bi bi-arrow-left me-1"></i>Volver Atrás</a>
                </div>
            </form>
        </div>

        <script>
        function cargarVias() {{
            const tramo = document.getElementById('tramo').value;
            if (!tramo) return;
            fetch(`/obtener_vias?tramo=${{encodeURIComponent(tramo)}}`)
                .then(res => res.json())
                .then(vias => {{
                    const selectVia = document.getElementById('via');
                    selectVia.innerHTML = '<option selected disabled>Selecciona una vía</option>';
                    vias.forEach(v => {{
                        const opt = document.createElement('option');
                        opt.value = v;
                        opt.textContent = v;
                        selectVia.appendChild(opt);
                    }});
                }});
        }}
        </script>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return html.replace(b'</body>', SCRIPT_GLOBAL_SYNC.encode('utf-8') + b'\n</body>') if isinstance(html, bytes) else html.replace('</body>', SCRIPT_GLOBAL_SYNC + '\n</body>')

import json

def page_indicadores_operativa_resultados(
    id_tramo: str,
    id_via: str,
    pto_km_ini: str,
    pto_km_fin: str,
    fecha_inicio: str,
    fecha_fin: str,
    labels: list,
    valores: list,
    mensaje_parametros: str
) -> str:

    # Mapeo de indicadores → iconos
    iconos = {
        "Inspecciones realizadas": "img/inspeccion.png",
        "Km auscultados": "img/km.png",
        "Informes manuales": "img/formulario.png",
        "Errores detectados": "img/error.png"
    }

    # Construcción dinámica de las tarjetas
    tarjetas_html = ""
    for label, valor in zip(labels, valores):
        img = iconos.get(label, "")
        
        # Si es número decimal → formatear a 2 decimales
        if isinstance(valor, float):
            valor_formateado = f"{valor:.2f}"
        else:
            valor_formateado = valor

        unidad = " km" if label == "Km" else ""

        tarjetas_html += f"""
        <div class="col-12 col-md-6 col-lg-3">
            <div class="card shadow text-center p-3 indicador-card">
                <h6 class="text-muted mb-2">{label}</h6>
                <h2 class="fw-bold text-primary">{valor_formateado}{unidad}</h2>
                <img src="{img}" class="indicador-icon" alt="{label}">
            </div>
        </div>
        """

    # HTML completo
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Resultados — Indicadores de Operativa</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            .indicador-card {{
                border-radius: 15px;
                transition: transform .2s ease;
            }}
            .indicador-card:hover {{
                transform: scale(1.03);
                box-shadow: 0 0.6rem 1.2rem rgba(0,0,0,0.15);
            }}
            .indicador-icon {{
                width: 60px;
                height: 60px;
                margin-top: 10px;
            }}
        </style>
    </head>

    <body class="bg-light">

        <div class="container mt-4">
            {mensaje_parametros}

            <!-- Botón arriba a la derecha -->
            <div class="d-flex justify-content-end mb-3">
                <a href="/filtros" class="btn btn-primary btn-sm"><i class="bi bi-arrow-left me-1"></i>Volver a filtros</a>
            </div>

            <h2 class="text-center mb-4">Resumen de auscultación de catenaria</h2>

            <div class="row g-4">
                {tarjetas_html}
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

    return html.replace(b'</body>', SCRIPT_GLOBAL_SYNC.encode('utf-8') + b'\n</body>') if isinstance(html, bytes) else html.replace('</body>', SCRIPT_GLOBAL_SYNC + '\n</body>')


def page_modal_medicion_detalle(medicion: dict | None) -> str:
    """
    Devuelve el HTML de un modal Bootstrap con el detalle de una medición.
    Se carga dinámicamente desde Resultados de Mediciones.
    """

    if not medicion:
        return """
<div class="modal fade" id="modal-medicion" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">

      <div class="modal-header">
        <h5 class="modal-title text-danger">
          Medición no encontrada
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
      </div>

      <div class="modal-body">
        No se ha encontrado la medición relacionada.
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
          Cerrar
        </button>
      </div>

    </div>
  </div>
</div>
"""

    # ------------------------------------------------------------
    # INCIDENCIAS → BOTÓN ÚNICO (ABRE MODAL SIEMPRE)
    # ------------------------------------------------------------
    incidencias_html = f"""
        <div class="text-center mt-4 mb-3">
            <button type="button"
                class="btn btn-warning btn-sm"
                onclick="abrirModalIncidenciasMedicion(
                    '{medicion.get('id_tramo')}',
                    '{medicion.get('id_via')}',
                    '{medicion.get('pto_km')}',
                    '{medicion.get('fecha')}',
                    '{medicion.get('hora')}'
                ); return false;">
                <i class="bi bi-exclamation-triangle-fill me-1"></i>
                Ver incidencias asociadas
            </button>
        </div>
        """

    # ------------------------------------------------------------
    # MODAL DE MEDICIÓN
    # ------------------------------------------------------------
    return f"""
<div class="modal fade" id="modal-medicion" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">

      <!-- HEADER -->
      <div class="modal-header">
        <h5 class="modal-title">
          <i class="bi bi-speedometer2 me-2"></i>
          Medición — Tramo {medicion.get('id_tramo')} · Vía {medicion.get('id_via')} · PK {medicion.get('pto_km')}
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
      </div>

      <!-- BODY -->
      <div class="modal-body">

        <h6 class="mb-2 text-center">
          <i class="bi bi-rulers me-1"></i> Altura y posición LAC
        </h6>
        <div class="d-flex flex-wrap gap-2 mb-3 justify-content-center text-center">
          <span class="badge bg-primary">Altura LAC: {medicion.get('altura_LAC')}</span>
          <span class="badge bg-info">Flecha: {medicion.get('flecha')}</span>
          <span class="badge bg-success">Contraflecha: {medicion.get('contraflecha')}</span>
          <span class="badge bg-danger">Descentramiento: {medicion.get('descentramiento')}</span>
        </div>

        <h6 class="mb-2 text-center">
          <i class="bi bi-bezier2 me-1"></i> Geometría y vía
        </h6>
        <ul class="small text-center list-unstyled">
          <li>Pendiente: <strong>{medicion.get('pendiente')}</strong></li>
          <li>Variación pendiente: <strong>{medicion.get('variacion_pendiente')}</strong></li>
          <li>Radio curvatura: <strong>{medicion.get('radio_curvatura')}</strong></li>
        </ul>

        <!-- INCIDENCIAS -->
        {incidencias_html}

        <h6 class="mb-2 text-center">
          <i class="bi bi-gear-fill me-1"></i> Otros parámetros técnicos
        </h6>
        <ul class="small text-center list-unstyled">
          <li>Presión hidráulica: {medicion.get('presion_hidraulica')}</li>
          <li>Tensión batería: {medicion.get('tension_bateria')} mV</li>
          <li>Creado por: {medicion.get('created_by')} · {medicion.get('created_at')}</li>
          <li>Actualizado por: {medicion.get('updated_by')} · {medicion.get('updated_at')}</li>
        </ul>

      </div>

      <!-- FOOTER -->
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
          Cerrar
        </button>
      </div>

    </div>
  </div>
</div>
"""


def page_modal_incidencias_medicion(incidencias: list[dict]) -> str:
    """
    Modal con TODAS las incidencias relacionadas a una medición
    """

    if not incidencias:
        filas = """
        <tr>
            <td colspan="7" class="text-center text-muted">
                No hay incidencias relacionadas.
            </td>
        </tr>
        """
    else:
        filas = ""
        for inc in incidencias:

            # Seguridad total
            nivel = inc.get("nivel", "—")
            poste = inc.get("poste", "—")
            tipo = inc.get("tipo", "—")
            subtipo = inc.get("subtipo", "—")
            valor_medido = inc.get("valor_medido", "—")
            valor_ref = inc.get("valor_referencia", "—")
            relacionada = inc.get("relacionada", True)

            # Badge nivel
            badge = "bg-secondary"
            try:
                n = int(nivel)
                if n == 1:
                    badge = "bg-success"
                elif n == 2:
                    badge = "bg-warning text-dark"
                elif n >= 3:
                    badge = "bg-danger"
            except Exception:
                pass

            filas += f"""
            <tr>
                <td><span class="badge {badge}">Nivel {nivel}</span></td>
                <td>{poste}</td>
                <td>{tipo}</td>
                <td>{subtipo}</td>
                <td>{valor_medido}</td>
                <td>{valor_ref}</td>
                <td class="text-center">
                    {"🔗" if relacionada else ""}
                </td>
            </tr>
            """

    return f"""
<div class="modal fade" id="modal-incidencias" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">

      <div class="modal-header">
        <h5 class="modal-title">
          <i class="bi bi-exclamation-triangle-fill me-2"></i>
          Incidencias relacionadas
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>

      <div class="modal-body">

        <div class="table-responsive">
          <table class="table table-sm table-bordered align-middle text-center">
            <thead class="table-warning">
              <tr>
                <th>Nivel</th>
                <th>Poste</th>
                <th>Tipo</th>
                <th>Subtipo</th>
                <th>Valor medido</th>
                <th>Valor referencia</th>
                <th>Rel.</th>
              </tr>
            </thead>
            <tbody>
              {filas}
            </tbody>
          </table>
        </div>

      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">
          Cerrar
        </button>
      </div>

    </div>
  </div>
</div>
"""


def page_modal_incidencia_detalle(inc: dict | None) -> str:
    if not inc:
        return """
        <div class="modal fade" id="modal-incidencia" tabindex="-1">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-body text-center text-danger">
                Incidencia no encontrada
              </div>
            </div>
          </div>
        </div>
        """

    # --- Badge por nivel ---
    nivel = inc.get("nivel")
    if nivel == 1:
        badge_nivel = '<span class="badge bg-success">Nivel 1</span>'
    elif nivel == 2:
        badge_nivel = '<span class="badge bg-warning text-dark">Nivel 2</span>'
    elif nivel == 3:
        badge_nivel = '<span class="badge bg-danger">Nivel 3</span>'
    else:
        badge_nivel = '<span class="badge bg-secondary">Nivel</span>'

    # --- Coordenadas ---
    coords = inc.get("coordenadas_GPS") or []
    lat, lon = (coords[0], coords[1]) if len(coords) == 2 else ("-", "-")
    enlace_mapa = (
        f"https://www.google.com/maps?q={lat},{lon}"
        if lat != "-" else "#"
    )

    return f"""
<div class="modal fade" id="modal-incidencia" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">

      <div class="modal-header">
        <h5 class="modal-title">
          <i class="bi bi-exclamation-triangle-fill me-2"></i>
          Detalle de Incidencias
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>

      <div class="modal-body">

        <div class="d-flex justify-content-between align-items-center mb-3">
          <div>
            <i class="bi bi-geo-alt-fill"></i>
            Coordenadas: <strong>{lat}</strong>, <strong>{lon}</strong>
          </div>

          <a href="{enlace_mapa}" target="_blank"
             class="btn btn-outline-primary btn-sm">
            <i class="bi bi-map"></i> Ver en mapa
          </a>
        </div>

        <table class="table table-bordered table-hover align-middle text-center">
          <thead class="table-light">
            <tr>
              <th>Nivel</th>
              <th>Poste</th>
              <th>Tipo</th>
              <th>Subtipo</th>
              <th>Valor medido</th>
              <th>Valor referencia</th>
            </tr>
          </thead>

          <tbody>
            <tr>
              <td>{badge_nivel}</td>
              <td>{inc.get('poste','')}</td>
              <td>
                <span class="badge bg-info text-dark">{inc.get('tipo','')}</span>
                <div class="small text-muted mt-1">
                  {inc.get('descripcion_tipo','')}
                </div>
              </td>
              <td>{inc.get('subtipo') or '—'}</td>
              <td>{inc.get('valor_medido','')}</td>
              <td>{inc.get('valor_referencia') or '—'}</td>
            </tr>
          </tbody>
        </table>

      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">
          Cerrar
        </button>
      </div>

    </div>
  </div>
</div>
"""


def page_modal_incidencias_medicion(
    tramo: str,
    via: str,
    pto_km: str,
    fecha: str,
    hora: str,
    incidencias: list,
) -> str:
    """
    Modal Bootstrap con todas las incidencias asociadas a una medición
    """

    filas = ""

    for inc in incidencias:
        filas += """
        <tr>
            <td>{nivel}</td>
            <td>{poste}</td>
            <td>{tipo}</td>
            <td>{subtipo}</td>
            <td>{valor}</td>
        </tr>
        """.format(
            nivel=inc.get("nivel", "—"),
            poste=inc.get("poste", "—"),
            tipo=inc.get("tipo", "—"),
            subtipo=inc.get("subtipo", "—"),
            valor=inc.get("valor_medido", "—"),
        )

    if not filas:
        filas = """
        <tr>
            <td colspan="5" class="text-center text-muted">
                No hay incidencias asociadas
            </td>
        </tr>
        """

    return """
<div class="modal fade" id="modal-incidencias" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">

      <div class="modal-header bg-warning">
        <h5 class="modal-title">
            ⚠ Incidencias relacionadas
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>

      <div class="modal-body">

        <p class="small text-muted">
            Tramo: <strong>{tramo}</strong> ·
            Vía: <strong>{via}</strong> ·
            PK: <strong>{pto_km}</strong><br>
            Fecha: <strong>{fecha}</strong> ·
            Hora: <strong>{hora}</strong>
        </p>

        <div class="table-responsive">
        <table class="table table-bordered table-sm align-middle text-center">
            <thead class="table-light">
                <tr>
                    <th>Nivel</th>
                    <th>Poste</th>
                    <th>Tipo</th>
                    <th>Subtipo</th>
                    <th>Valor</th>
                </tr>
            </thead>
            <tbody>
                {filas}
            </tbody>
        </table>
        </div>

      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal">
            Cerrar
        </button>
      </div>

    </div>
  </div>
</div>
""".format(
        tramo=tramo,
        via=via,
        pto_km=pto_km,
        fecha=fecha,
        hora=hora,
        filas=filas,
    )


# ============================================================
#   PÁGINA DE ALERTAS
# ============================================================


def _paginacion_alertas(pagina: int, total_paginas: int) -> str:
    """Genera el nav de paginación Bootstrap para la página de alertas."""
    if total_paginas <= 1:
        return ""

    def _li(p, label=None, disabled=False, active=False):
        label = label or str(p)
        cls = "page-item"
        if disabled:
            cls += " disabled"
        if active:
            cls += " active"
        href = f"/alertas?pagina={p}"
        inner = (
            f'<span class="page-link">{label}</span>'
            if disabled
            else f'<a class="page-link" href="{href}">{label}</a>'
        )
        return f'<li class="{cls}">{inner}</li>'

    items = []
    items.append(_li(1, "|&laquo;", disabled=(pagina == 1)))
    items.append(_li(pagina - 1, "&laquo;", disabled=(pagina == 1)))

    rango = 2
    desde_p = max(1, pagina - rango)
    hasta_p = min(total_paginas, pagina + rango)
    if pagina - rango < 1:
        hasta_p = min(total_paginas, hasta_p + (rango - pagina + 1))
    if pagina + rango > total_paginas:
        desde_p = max(1, desde_p - (pagina + rango - total_paginas))

    if desde_p > 1:
        items.append(_li(1))
        if desde_p > 2:
            items.append('<li class="page-item disabled"><span class="page-link">…</span></li>')
    for p in range(desde_p, hasta_p + 1):
        items.append(_li(p, active=(p == pagina)))
    if hasta_p < total_paginas:
        if hasta_p < total_paginas - 1:
            items.append('<li class="page-item disabled"><span class="page-link">…</span></li>')
        items.append(_li(total_paginas))

    items.append(_li(pagina + 1, "&raquo;", disabled=(pagina == total_paginas)))
    items.append(_li(total_paginas, "&raquo;|", disabled=(pagina == total_paginas)))

    nav_items = "\n".join(items)
    return f"""
    <nav class="d-flex justify-content-center align-items-center gap-3 mt-4 mb-2" aria-label="Paginación alertas">
      <span class="text-muted small">Página {pagina} de {total_paginas}</span>
      <ul class="pagination pagination-sm mb-0">
        {nav_items}
      </ul>
    </nav>"""


def page_alertas(
    grupos: List[Dict[str, Any]],
    total: int,
    total_global: int = 0,
    pagina: int = 1,
    total_paginas: int = 1,
) -> str:
    """
    Página de alertas: incidencias de nivel 3/4 sin revisar,
    agrupadas por fecha (acordeón colapsable).
    Solo accesible para roles administrador y usuario.
    """

    def _nivel_badge(nivel) -> str:
        try:
            n = int(nivel)
        except Exception:
            n = None
        if n == 3:
            return '<span class="badge badge-nivel badge-nivel-3">Nivel 3</span>'
        if n == 4:
            return '<span class="badge badge-nivel badge-nivel-4">Nivel 4</span>'
        return f'<span class="badge badge-nivel badge-nivel-0">{nivel if nivel is not None else "—"}</span>'

    TIPO_DESC = {
        "KPIT1": "Incidencia de altura (m)",
        "KPIT2": "Incidencia de descentramiento (cm)",
        "KPIT3": "Incidencia de pendiente (‰)",
        "KPIT4": "Incidencia de variación de pendiente (‰)",
        "KPIT5": "Incidencia de flecha (%)",
        "KPIT6": "Incidencia de contraflecha (mm)",
        "KPIT7": "Incidencia de tijera (mm)",
        "KPIT8": "Zona de contacto con el pantógrafo (mm)",
        "KPIT9": "Incidencia por otras causas",
    }
    SUBTIPO_DESC = {
        "rec": "Descentramiento en recta",
        "cpo": "Descentramiento en curva — poste",
        "cva": "Descentramiento en curva — vano",
        "com": "Defecto de compensación",
        "gal": "Gálibo reducido",
        "mon": "Montaje",
    }

    if not grupos:
        cuerpo = '''
        <div class="alert alert-success d-flex align-items-center gap-2 mt-4" role="alert">
          <i class="bi bi-check-circle-fill fs-5"></i>
          <span>No hay incidencias de nivel 3 o 4 pendientes de revisión.</span>
        </div>'''
    else:
        items_acordeon = ""
        for idx, grupo in enumerate(grupos):
            fecha_raw = grupo.get("fecha", "—")
            # Formatea "20251102" → "02/11/2025"
            try:
                from datetime import datetime as _dt
                fecha_display = _dt.strptime(fecha_raw, "%Y%m%d").strftime("%d/%m/%Y")
            except Exception:
                fecha_display = fecha_raw

            total_fecha = sum(
                len(t.get("incidencias", [])) for t in grupo.get("tramos", [])
            )

            filas_tramos = ""
            for tv_idx, tv in enumerate(grupo.get("tramos", [])):
                id_tramo = tv.get("id_tramo", "—")
                id_via = tv.get("id_via", "—")
                tramo_id = f"tramo-{idx}-{tv_idx}"
                n_inc = len(tv.get("incidencias", []))

                filas_inc = ""
                for inc in tv.get("incidencias", []):
                    doc_id = inc.get("doc_id", "")
                    pto_km = inc.get("pto_km", "—")
                    hora = inc.get("hora", "—")
                    nivel = inc.get("nivel")
                    poste = inc.get("poste") or "—"
                    tipo = inc.get("tipo") or "—"
                    subtipo = inc.get("subtipo") or "—"
                    valor = inc.get("valor_medido")
                    valor_fmt = "{:.2f}".format(valor) if isinstance(valor, (int, float)) else (valor or "—")
                    valor_ref = inc.get("valor_referencia")
                    valor_ref_fmt = "{:.2f}".format(valor_ref) if isinstance(valor_ref, (int, float)) else (valor_ref or "—")
                    coords = inc.get("coordenadas_GPS") or []
                    lat, lon = (coords[0], coords[1]) if len(coords) == 2 else (None, None)
                    mapa_btn = (
                        f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" '
                        f'class="btn btn-outline-primary btn-sm py-0 px-2">'
                        f'<i class="bi bi-map"></i> Ver en mapa</a>'
                        if lat is not None else "—"
                    )
                    tipo_desc = TIPO_DESC.get(tipo, "")
                    subtipo_desc = SUBTIPO_DESC.get(subtipo, "")
                    tipo_td = (
                        f'<span class="badge bg-info text-dark" data-bs-toggle="tooltip" '
                        f'data-bs-placement="top" title="{tipo_desc}">{tipo}</span>'
                        if tipo_desc else
                        f'<span class="badge bg-info text-dark">{tipo}</span>'
                    )
                    subtipo_td = (
                        f'<span data-bs-toggle="tooltip" data-bs-placement="top" '
                        f'title="{subtipo_desc}">{subtipo}</span>'
                        if subtipo_desc else subtipo
                    )

                    filas_inc += f"""
                    <tr id="fila-{doc_id}" class="alerta-row"
                        data-nivel="{nivel if nivel is not None else ''}"
                        data-tipo="{tipo}"
                        data-subtipo="{subtipo}"
                        data-poste="{str(poste).lower() if poste else ''}"
                        data-pto-km="{pto_km if pto_km is not None else ''}"
                        data-hora="{hora if hora is not None else ''}">
                      <td class="text-center">
                        <input type="checkbox" class="form-check-input check-revision"
                               data-doc-id="{doc_id}" onchange="toggleRevision(this)">
                      </td>
                      <td>{_nivel_badge(nivel)}</td>
                      <td>{pto_km}</td>
                      <td>{hora}</td>
                      <td>{poste}</td>
                      <td>{tipo_td}</td>
                      <td>{subtipo_td}</td>
                      <td>{valor_fmt}</td>
                      <td>{valor_ref_fmt}</td>
                      <td>{mapa_btn}</td>
                    </tr>"""

                filas_tramos += f"""
                <div class="card mb-3 border-danger">
                  <div class="card-header bg-danger bg-opacity-10 p-0 d-flex align-items-center">
                    <button class="btn flex-grow-1 text-start fw-semibold d-flex align-items-center gap-2 px-3 py-2"
                            type="button" data-bs-toggle="collapse"
                            data-bs-target="#{tramo_id}"
                            aria-expanded="false"
                            aria-controls="{tramo_id}">
                      <i class="bi bi-geo-alt-fill text-danger"></i>
                      <span class="text-muted small">{fecha_display}</span>
                      <span class="text-muted small">|</span>
                      Tramo <strong>{id_tramo}</strong> &nbsp;|&nbsp; Vía <strong>{id_via}</strong>
                      <span class="badge bg-danger ms-3">{n_inc}</span>
                    </button>
                    <div class="pe-2">
                      <button class="btn btn-success btn-sm" id="btn-confirmar-{tramo_id}"
                              onclick="confirmarRevisiones('{tramo_id}')" disabled>
                        <i class="bi bi-check-circle me-1"></i> Confirmar revisiones
                      </button>
                    </div>
                  </div>
                  <div id="{tramo_id}" class="collapse">
                    <div class="card-body p-0">
                      <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0 alertas-table" data-tramo-id="{tramo_id}">
                          <thead class="table-light">
                            <tr>
                              <th style="width:40px">Revisada</th>
                              <th>Nivel <span class="text-muted small">▼</span></th>
                              <th>Pto. km <span class="text-muted small">▼</span></th>
                              <th>Hora <span class="text-muted small">▼</span></th>
                              <th>Poste <span class="text-muted small">▼</span></th>
                              <th>Tipo <span class="text-muted small">▼</span></th>
                              <th>Subtipo <span class="text-muted small">▼</span></th>
                              <th>Valor</th>
                              <th>Referencia</th>
                              <th>Coordenadas</th>
                            </tr>
                            <tr class="filtros-row">
                              <th></th>
                              <th>
                                <select class="form-select form-select-sm filtro-nivel" data-col="nivel">
                                  <option value="">Todos</option>
                                  <option value="3">Nivel 3</option>
                                  <option value="4">Nivel 4</option>
                                </select>
                              </th>
                              <th>
                                <input type="text" class="form-control form-control-sm filtro-pto-km"
                                       data-col="pto_km" placeholder="Buscar…">
                              </th>
                              <th>
                                <input type="text" class="form-control form-control-sm filtro-hora"
                                       data-col="hora" placeholder="HH:MM">
                              </th>
                              <th>
                                <input type="text" class="form-control form-control-sm filtro-poste"
                                       data-col="poste" placeholder="Buscar…">
                              </th>
                              <th>
                                <select class="form-select form-select-sm filtro-tipo" data-col="tipo">
                                  <option value="">Todos</option>
                                </select>
                              </th>
                              <th>
                                <select class="form-select form-select-sm filtro-subtipo" data-col="subtipo">
                                  <option value="">Todos</option>
                                </select>
                              </th>
                              <th></th>
                              <th></th>
                              <th></th>
                            </tr>
                          </thead>
                          <tbody>
                            {filas_inc}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>"""

            items_acordeon += f"""
            <div class="accordion-item">
              <h2 class="accordion-header" id="heading-{idx}">
                <button class="accordion-button collapsed fw-semibold"
                        type="button" data-bs-toggle="collapse"
                        data-bs-target="#collapse-{idx}"
                        aria-expanded="false"
                        aria-controls="collapse-{idx}">
                  <i class="bi bi-calendar-event me-2 text-danger"></i>
                  {fecha_display}
                  <span class="badge bg-danger ms-3">{total_fecha}</span>
                  <span class="text-muted fw-normal ms-2 small">incidencias pendientes</span>
                </button>
              </h2>
              <div id="collapse-{idx}" class="accordion-collapse collapse"
                   aria-labelledby="heading-{idx}">
                <div class="accordion-body">
                  {filas_tramos}
                </div>
              </div>
            </div>"""

        cuerpo = f'''
        <div class="d-flex align-items-center gap-3 mb-4 p-3 bg-danger bg-opacity-10 rounded">
          <i class="bi bi-exclamation-triangle-fill fs-3 text-danger"></i>
          <div>
            <span class="fw-bold fs-5">{total_global}</span>
            <span class="ms-1">incidencias de nivel 3 o 4 pendientes de revisión</span>
            <span class="text-muted small ms-2">— mostrando {total} de esta página</span>
          </div>
        </div>
        <div class="accordion" id="acordeonAlertas">
          {items_acordeon}
        </div>
        {_paginacion_alertas(pagina, total_paginas)}'''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Alertas</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" crossorigin="anonymous">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
  <link rel="shortcut icon" href="/img/logo.png" type="image/x-icon">
  <style>
    body {{ background: #f6f7fb; }}
    .nav-link:hover {{ transform: scale(1.1); transition: transform 0.3s linear; }}
    .badge-nivel {{ padding:.35rem .55rem; border-radius:.5rem; font-weight:700; font-size:.75rem; }}
    .badge-nivel-3 {{ background:#dc2626; color:#fff; }}
    .badge-nivel-4 {{ background:#7f1d1d; color:#fff; }}
    .badge-nivel-0 {{ background:#6b7280; color:#fff; }}
    .fila-revisada td {{ opacity:.45; text-decoration:line-through; }}
    .fila-pendiente td {{ background-color:#fff3cd !important; }}
  </style>
</head>
<body>
    {NAV_HTML}

  <div class="container py-4">
    <div class="d-flex align-items-center justify-content-between gap-3 mb-3">
      <h1 class="h3 mb-0"><i class="bi bi-bell-fill text-danger me-2"></i>Alertas de incidencias</h1>
      <a href="/entrada" class="btn btn-primary btn-sm volver-btn">
        <i class="bi bi-arrow-left me-1"></i>Volver Atrás
      </a>
    </div>
    <p class="text-muted mb-4">
      Incidencias de <strong>nivel 3 y nivel 4</strong> que aún no han sido revisadas,
      agrupadas por fecha. Marca los checkboxes y pulsa <strong>Confirmar revisiones</strong> en cada grupo para registrarlas.
    </p>
    {cuerpo}
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
  <script>
  document.addEventListener('DOMContentLoaded', function () {{
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {{
      new bootstrap.Tooltip(el);
    }});
  }});

  function getCookie(name) {{
    let v = null;
    document.cookie.split(';').forEach(c => {{
      const [k, val] = c.trim().split('=');
      if (k === name) v = decodeURIComponent(val);
    }});
    return v;
  }}

  function toggleRevision(checkbox) {{
    const fila = document.getElementById('fila-' + checkbox.dataset.docId);
    if (fila) {{
      if (checkbox.checked) {{
        fila.classList.add('fila-pendiente');
      }} else {{
        fila.classList.remove('fila-pendiente');
      }}
    }}
    const tramoCollapse = checkbox.closest('.collapse');
    if (tramoCollapse) {{
      const btn = document.getElementById('btn-confirmar-' + tramoCollapse.id);
      if (btn) {{
        btn.disabled = tramoCollapse.querySelectorAll('.check-revision:checked').length === 0;
      }}
    }}
  }}

  async function confirmarRevisiones(tramoid) {{
    const tramoEl = document.getElementById(tramoid);
    if (!tramoEl) return;
    const checkboxes = Array.from(tramoEl.querySelectorAll('.check-revision:checked'));
    if (checkboxes.length === 0) return;

    const btn = document.getElementById('btn-confirmar-' + tramoid);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Confirmando...';

    const errores = [];
    const erroresDetalle = [];
    for (const cb of checkboxes) {{
      const docId = cb.dataset.docId;
      try {{
        const r = await fetch('/alertas/marcar-revision', {{
          method: 'POST',
          headers: {{
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          }},
          body: JSON.stringify({{ doc_id: docId, revisado: true }}),
        }});
        let data = null;
        try {{ data = await r.json(); }} catch (_e) {{ data = null; }}
        if (r.ok && data && data.success) {{
          const fila = document.getElementById('fila-' + docId);
          if (fila) {{
            fila.style.transition = 'opacity 0.4s';
            fila.style.opacity = '0';
            setTimeout(() => fila.remove(), 400);
          }}
        }} else {{
          errores.push(docId);
          const motivo = (data && (data.error || data.message)) || ('HTTP ' + r.status);
          erroresDetalle.push(docId + ': ' + motivo);
          cb.checked = false;
          const fila = document.getElementById('fila-' + docId);
          if (fila) fila.classList.remove('fila-pendiente');
        }}
      }} catch (err) {{
        errores.push(docId);
        erroresDetalle.push(docId + ': ' + (err && err.message ? err.message : 'fetch error'));
        cb.checked = false;
        const fila = document.getElementById('fila-' + docId);
        if (fila) fila.classList.remove('fila-pendiente');
      }}
    }}

    if (errores.length > 0) {{
      console.warn('Errores al confirmar incidencias:', erroresDetalle);
      Swal.fire({{
        icon: 'error',
        title: 'Error',
        html: 'No se pudieron confirmar ' + errores.length + ' incidencia(s).<br><br>'
              + '<small style="text-align:left;display:block;font-family:monospace;'
              + 'white-space:pre-wrap;max-height:240px;overflow:auto">'
              + erroresDetalle.map(function(s){{ return s.replace(/</g,'&lt;'); }}).join('\\n')
              + '</small>',
        confirmButtonColor: '#0d6efd',
      }});
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check-circle me-1"></i> Confirmar revisiones';
    }} else {{
      btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Confirmado';
    }}
  }}

  // ============================================================
  //   FILTROS DE TABLA DE ALERTAS (cabeceras)
  // ============================================================
  document.addEventListener('DOMContentLoaded', function () {{
    document.querySelectorAll('table.alertas-table').forEach(function (tabla) {{
      // Pobla los selects Tipo y Subtipo con los valores únicos de la tabla.
      const tipos = new Set();
      const subtipos = new Set();
      tabla.querySelectorAll('tbody tr.alerta-row').forEach(function (tr) {{
        const tp = (tr.dataset.tipo || '').trim();
        const sb = (tr.dataset.subtipo || '').trim();
        if (tp && tp !== '—') tipos.add(tp);
        if (sb && sb !== '—') subtipos.add(sb);
      }});
      const selTipo = tabla.querySelector('.filtro-tipo');
      const selSub  = tabla.querySelector('.filtro-subtipo');
      Array.from(tipos).sort().forEach(function (v) {{
        const o = document.createElement('option'); o.value = v; o.textContent = v;
        selTipo.appendChild(o);
      }});
      Array.from(subtipos).sort().forEach(function (v) {{
        const o = document.createElement('option'); o.value = v; o.textContent = v;
        selSub.appendChild(o);
      }});

      function aplicarFiltros() {{
        const fNivel  = (tabla.querySelector('.filtro-nivel').value  || '').trim();
        const fTipo   = (tabla.querySelector('.filtro-tipo').value   || '').trim();
        const fSubtipo= (tabla.querySelector('.filtro-subtipo').value|| '').trim();
        const fPoste  = (tabla.querySelector('.filtro-poste').value  || '').trim().toLowerCase();
        const fPtoKm  = (tabla.querySelector('.filtro-pto-km') ? tabla.querySelector('.filtro-pto-km').value : '').trim().toLowerCase();
        const fHora   = (tabla.querySelector('.filtro-hora') ? tabla.querySelector('.filtro-hora').value : '').trim().toLowerCase();
        tabla.querySelectorAll('tbody tr.alerta-row').forEach(function (tr) {{
          let visible = true;
          if (fNivel  && tr.dataset.nivel   !== fNivel)   visible = false;
          if (fTipo   && tr.dataset.tipo    !== fTipo)    visible = false;
          if (fSubtipo&& tr.dataset.subtipo !== fSubtipo) visible = false;
          if (fPoste  && !(tr.dataset.poste || '').includes(fPoste)) visible = false;
          if (fPtoKm  && !(tr.dataset.ptoKm || '').toLowerCase().includes(fPtoKm)) visible = false;
          if (fHora   && !(tr.dataset.hora  || '').toLowerCase().includes(fHora))  visible = false;
          tr.style.display = visible ? '' : 'none';
        }});
      }}

      tabla.querySelectorAll('.filtros-row select, .filtros-row input').forEach(function (el) {{
        el.addEventListener('change', aplicarFiltros);
        el.addEventListener('input',  aplicarFiltros);
        // Evita que clickar el filtro colapse la card padre.
        el.addEventListener('click',  function (e) {{ e.stopPropagation(); }});
      }});
    }});
  }});
  </script>
</body>
</html>"""
