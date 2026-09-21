
# Mensajes para usuarios
USUARIOS = {
    #Alta de Usuario
    "create_success": "Usuario creado correctamente",
    "create_exists": "Ya existe un usuario con ese código. No es posible crear un duplicado.",
    "create_error": "Error al crear usuario",
    "create_invalid": "Datos inválidos al crear usuario",
    "not_found": "Usuario no encontrado",
    "db_error": "Error de base de datos al gestionar usuario",
    "unexpected": "Error inesperado al gestionar usuario",
    
    #Modificar Usuario
    "update_success": "Usuario actualizado correctamente",
    "update_error": "Error al actualizar usuario",
    "update_invalid": "Datos inválidos al actualizar usuario",


    #Eliminar Usuario
    "delete_success": "Usuario eliminado correctamente",
    "delete_error": "Error al eliminar usuario",
}

# Mensajes para tramos
TRAMOS = {

    #Alta de Tramo
    "create_success": "Tramo creado correctamente",
    "create_exists": "Ya existe un tramo con ese código. No es posible crear un duplicado.",
    "create_error": "Error al crear tramo",
    "create_invalid": "Datos inválidos al crear tramo",
    "not_found": "Tramo no encontrado",
    "db_error": "Error de base de datos al gestionar tramo",
    "unexpected": "Error inesperado al gestionar tramo",
    
    #Modificar Tramo
    "update_success": "Tramo actualizado correctamente",
    "update_error": "Error al actualizar tramo",
    "update_invalid": "Datos inválidos al actualizar tramo",

    #Eliminar Tramo
    "delete_success": "Tramo eliminado correctamente",
    "delete_error": "Error al eliminar tramo",
}

# Mensajes genéricos
GENERIC = {
    "not_found": "No se encontraron resultados",
    "no_data": "No hay datos disponibles",
    "db_error": "Error de base de datos",
    "unexpected": "Error inesperado",
    "invalid_data": "Datos inválidos",
    "no_data_for_filters": "No hay datos disponibles para los filtros seleccionados",
    "error_processing_filters": "Error al procesar los filtros de búsqueda",
}


# Mensajes relacionado a indicadores
INDICADORES = {
    "tramo_edit_not_found": "El tramo a editar no existe en la base de datos",
    "no_data_for_filters": "No se encontraron datos para los filtros seleccionados",
    "no_indicators_calculated": "No se pudieron calcular los indicadores para los parámetros seleccionados",
    "no_incidence_data": "No se encontraron datos de incidencias para los filtros seleccionados",
    "error_calculating_indicators": "Error al calcular indicadores",
    "error_generating_incidence_chart": "Error al generar gráfico de incidencias",
    "no_kpig_or_incidence_selected": "No se seleccionaron KPIG/KG ni incidencias ni indicadores para mostrar",
    "error_operativa": "Error al procesar los indicadores de operativa"
}
# Mensajes para umbrales
UMBRALES = {
    "create_success": "Umbral creado correctamente.",
    "create_exists": "Ya existe un umbral con esa clave.",
    "create_invalid": "Datos de umbral inválidos",
    "create_error": "Error al crear el umbral",
    "update_success": "Umbral actualizado correctamente.",
    "update_invalid": "Datos de umbral inválidos",
    "update_error": "Error al actualizar el umbral",
    "delete_success": "Umbral eliminado correctamente.",
    "delete_error": "Error al eliminar el umbral",
    "not_found": "Umbral no encontrado",
    "db_error": "Error de base de datos",
    "unexpected": "Error inesperado"
}
UMBRALES_CODES = {  
    # Validación de pares y forma
    "N1_INVALID": "N1 inválido.",
    "N2_INVALID": "N2 inválido.",
    "N3_INVALID": "N3 inválido.",
    "N4_INVALID": "N4 inválido.",
    "PAIR_SHAPE": "Cada N* debe ser una lista con dos valores ['min'-'max'].",
    "PAIR_EMPTY": "En cada N*, min y max no pueden estar vacíos.",
    "PAIR_NOT_NUMERIC": "En cada N*, min y max deben ser numéricos.",
    "PAIR_MIN_GE_MAX": "En cada N*, se exige min < max.",
    "NEGATIVE_VALUE": "No se admiten valores negativos en los rangos.",

    # Dirección y contigüidad
    "DIR_UNDETERMINED": "No se puede determinar la dirección: N1 y N2 no son contiguos.",
    "ASC_N1N2": "Ascendente: se espera N1.max = N2.min.",
    "ASC_N2N3": "Ascendente: se espera N2.max = N3.min.",
    "ASC_N3N4": "Ascendente: se espera N3.max = N4.min.",
    "DESC_N1N2": "Descendente: se espera N1.min = N2.max.",
    "DESC_N2N3": "Descendente: se espera N2.min = N3.max.",
    "DESC_N3N4": "Descendente: se espera N3.min = N4.max.",

    # Velocidad por tipo
    "SPEED_REQUIRED": "Para 'pendiente' y 'var_pendiente' la velocidad es obligatoria.",
    "SPEED_NOT_NUMERIC": "La velocidad debe ser numérica.",
    "SPEED_NEGATIVE": "La velocidad no puede ser negativa.",
    "SPEED_NOT_APPLICABLE": "La velocidad no aplica para este tipo (debe venir vacía).",

    # Valor de referencia
    "VREF_NOT_NUMERIC": "El valor de referencia debe ser numérico.",
    "VREF_NEGATIVE": "El valor de referencia no puede ser negativo.",
    "VREF_IN_RANGE": "El valor de referencia no puede estar dentro de ningún rango N*.",

    # Fallback genérico
    "VALIDATION_FAILED": "Validación fallida.",

    # Cruce tipo ↔ tipología/velocidad
    "REQ_TIPOLOGIA": "Debe informar la tipología para este tipo.",
    "VELOCIDAD_MUST_BE_EMPTY": "La velocidad debe estar vacía para este tipo.",
    "TIPOLOGIA_MUST_BE_EMPTY": "La tipología debe estar vacía cuando el tipo requiere velocidad.",
    "XOR_TIPOLOGIA_VELOCIDAD": "Debe indicar solo uno: o tipología o velocidad (no ambos).",
}

OPERACIONES = {

    #Alta de Subgrupo
    "create_success": "Subgrupo creado correctamente",
    "create_exists": "Ya existe un subgrupo con ese código. No es posible crear un duplicado.",
    "create_error": "Error al crear subgrupo",
    "create_invalid": "Datos inválidos al crear subgrupo",
    "not_found": "Subgrupo no encontrado",
    "db_error": "Error de base de datos al gestionar subgrupo",
    "unexpected": "Error inesperado al gestionar subgrupo",
    
    #Modificar Subgrupo
    "update_success": "Subgrupo actualizado correctamente",
    "update_error": "Error al actualizar subgrupo",
    "update_invalid": "Datos inválidos al actualizar subgrupo",

    #Eliminar Subgrupo
    "delete_success": "Subgrupo eliminado correctamente",
    "delete_error": "Error al eliminar subgrupo",
}
