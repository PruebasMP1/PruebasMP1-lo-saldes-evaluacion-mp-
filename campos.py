# -*- coding: utf-8 -*-
"""
campos.py — Definición ÚNICA de la ficha de evaluación de materia prima.

Esto es la "fuente de la verdad": tanto el formulario (lo que ve producción)
como el almacenamiento (la planilla / base de datos) leen de aquí. Si quieres
agregar, quitar o renombrar una pregunta, se hace SOLO en este archivo y todo
el resto se ajusta solo.

Cada campo es una tupla:
    (clave_interna, etiqueta_visible, tipo, opciones)

- clave_interna: nombre corto sin tildes ni espacios (sirve de columna).
- etiqueta_visible: el texto que lee la persona de producción.
- tipo: "text" | "textarea" | "select" | "multiselect" | "number" | "score" | "date"
- opciones: lista de alternativas (solo para select / multiselect).

Espejo de "Ficha de Evaluación Técnica y Sensorial de Muestra de Materia Prima".
"""

GENERAL = [
    ("fecha_evaluacion", "Fecha de evaluación", "date", None),
    ("responsable", "Responsable de evaluación", "text", None),
    ("producto_evaluado", "Producto evaluado (ej: Queso Mantecoso)", "text", None),
    ("proveedor", "Proveedor", "text", None),
    ("tipo_uso_esperado", "Tipo de uso esperado (ej: Empanadas, Quiches)", "text", None),
    ("lote_muestra", "Lote / Fecha de muestra", "text", None),
]

TECNICA = [
    ("apariencia_visual", "Apariencia visual del producto", "textarea", None),
    ("textura_fisica", "Textura física al tacto", "textarea", None),
    ("comportamiento_termico", "Comportamiento en procesos térmicos", "textarea", None),
    ("corte_manipulacion", "Corte o manipulación", "textarea", None),
    ("compatibilidad_masas", "Compatibilidad con masas o preparaciones actuales",
     "select", ["Alta", "Media", "Baja"]),
    ("merma_estimada_pct", "Nivel de merma o desperdicio estimado (%)", "number", None),
    ("facilidad_manipulacion", "Facilidad de manipulación", "select", ["Alta", "Media", "Baja"]),
    ("requiere_ajustes", "Requiere ajustes en la receta o proceso", "select", ["Sí", "No", "Parcial"]),
    ("comentarios_tecnicos", "Comentarios técnicos adicionales", "textarea", None),
]

SENSORIAL = [
    ("sabor", "Sabor", "score", None),
    ("aroma", "Aroma", "score", None),
    ("textura_boca", "Textura en boca", "score", None),
    ("integracion", "Integración con el resto del producto", "score", None),
    ("aceptacion_general", "Aceptación general del equipo", "score", None),
]

RECOMENDACION = [
    ("es_apto", "¿El producto es apto como materia prima?", "select",
     ["Sí", "No", "Con observaciones"]),
    ("uso_recomendado", "¿Se recomienda su uso para…?", "multiselect",
     ["Empanadas horno", "Empanadas fritas", "Quiches", "Tapaditos", "Otro"]),
    ("requiere_reformulacion", "¿Requiere reformulación o pruebas adicionales?",
     "select", ["Sí", "No"]),
    ("comentarios_finales", "Comentarios finales del evaluador", "textarea", None),
]

# Secciones en orden, tal como aparecen en la ficha original.
SECCIONES = [
    ("1. Información general", GENERAL),
    ("2. Evaluación técnica", TECNICA),
    ("3. Evaluación sensorial (post preparación)", SENSORIAL),
    ("4. Recomendación del área de producción", RECOMENDACION),
]

# Lista plana de todos los campos (útil para recorrer todo de una vez).
TODOS = GENERAL + TECNICA + SENSORIAL + RECOMENDACION

# Claves de los puntajes sensoriales (para calcular el promedio).
CLAVES_SENSORIAL = [c[0] for c in SENSORIAL]

# Orden final de columnas en el repositorio (id y fecha de registro primero).
COLUMNAS = (
    ["id", "registrado_en"]
    + [c[0] for c in TODOS]
    + ["promedio_sensorial"]
)

# Etiqueta legible por columna (para mostrar tablas y exportar bonito).
ETIQUETAS = {c[0]: c[1] for c in TODOS}
ETIQUETAS["id"] = "ID"
ETIQUETAS["registrado_en"] = "Registrado en"
ETIQUETAS["promedio_sensorial"] = "Promedio sensorial"
