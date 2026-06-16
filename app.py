# -*- coding: utf-8 -*-
"""
app.py — Evaluación de Materia Prima · Panificadora Lo Saldes

Espacio online que conecta ABASTECIMIENTO con PRODUCCIÓN:
producción ingresa cómo le fue probando la materia prima alternativa que llevó
abastecimiento, y todo queda en un repositorio consultable.

Dos pestañas:
  📝 Nueva evaluación  → el formulario (espejo de la ficha en Word).
  📊 Repositorio       → todas las pruebas, filtrables y descargables.
"""
from io import BytesIO

import pandas as pd
import streamlit as st

import campos
import almacenamiento as alm

st.set_page_config(
    page_title="Evaluación de Materia Prima · Lo Saldes",
    page_icon="🥖",
    layout="centered",
)


# --------------------------------------------------------------------------- #
#  (Opcional) Contraseña simple. Solo se activa si configuras app_password
#  en los secrets. Si no, la app queda abierta (útil mientras pruebas).
# --------------------------------------------------------------------------- #
def _control_acceso() -> bool:
    try:
        clave_real = st.secrets.get("app_password")
    except Exception:
        clave_real = None
    if not clave_real:
        return True  # sin contraseña configurada → acceso libre
    if st.session_state.get("acceso_ok"):
        return True
    st.title("🥖 Evaluación de Materia Prima")
    clave = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if clave == clave_real:
            st.session_state["acceso_ok"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    return False


if not _control_acceso():
    st.stop()


almacen = alm.obtener_almacen()


# --------------------------------------------------------------------------- #
#  Encabezado
# --------------------------------------------------------------------------- #
st.title("🥖 Evaluación de Materia Prima")
st.caption(
    "Panificadora Lo Saldes · puente entre Abastecimiento y Producción. "
    f"Guardando en: **{almacen.nombre}**"
)

tab_form, tab_repo = st.tabs(["📝 Nueva evaluación", "📊 Repositorio de pruebas"])


# --------------------------------------------------------------------------- #
#  Helper: dibuja un campo según su tipo y devuelve el valor ingresado.
# --------------------------------------------------------------------------- #
def _widget(clave, etiqueta, tipo, opciones):
    if tipo == "text":
        return st.text_input(etiqueta, key=clave)
    if tipo == "textarea":
        return st.text_area(etiqueta, key=clave, height=80)
    if tipo == "date":
        return st.date_input(etiqueta, key=clave).strftime("%Y-%m-%d")
    if tipo == "number":
        return st.number_input(etiqueta, min_value=0.0, max_value=100.0, step=0.5, key=clave)
    if tipo == "select":
        return st.selectbox(etiqueta, options=["—"] + opciones, key=clave)
    if tipo == "multiselect":
        return ", ".join(st.multiselect(etiqueta, options=opciones, key=clave))
    if tipo == "score":
        return st.slider(etiqueta + "  (0 = malo · 5 = excelente)", 0, 5, 3, key=clave)
    return st.text_input(etiqueta, key=clave)


# =========================================================================== #
#  PESTAÑA 1 · FORMULARIO
# =========================================================================== #
with tab_form:
    st.info(
        "Completa la ficha luego de probar la muestra. Los campos de sabor, aroma, "
        "etc. van de **0 a 5**. Al final presiona **Guardar evaluación**.",
        icon="📝",
    )

    with st.form("ficha", clear_on_submit=True):
        valores = {}
        for titulo, lista in campos.SECCIONES:
            st.subheader(titulo)
            for clave, etiqueta, tipo, opciones in lista:
                valores[clave] = _widget(clave, etiqueta, tipo, opciones)
            st.divider()

        enviado = st.form_submit_button("✅ Guardar evaluación", type="primary", use_container_width=True)

    if enviado:
        # Validación mínima: producto + responsable.
        if not valores.get("producto_evaluado") or not valores.get("responsable"):
            st.error("Faltan datos: indica al menos **Producto evaluado** y **Responsable**.")
        else:
            # Promedio sensorial (0-5), redondeado a 2 decimales.
            puntajes = [float(valores.get(k, 0) or 0) for k in campos.CLAVES_SENSORIAL]
            promedio = round(sum(puntajes) / len(puntajes), 2) if puntajes else 0
            valores["promedio_sensorial"] = promedio
            valores["id"] = alm.nuevo_id()
            valores["registrado_en"] = alm.marca_de_tiempo()

            almacen.guardar(valores)
            st.success(
                f"¡Guardado! ID **{valores['id']}** · promedio sensorial **{promedio}/5**. "
                "Lo verás en la pestaña *Repositorio*."
            )
            st.balloons()


# =========================================================================== #
#  PESTAÑA 2 · REPOSITORIO
# =========================================================================== #
with tab_repo:
    df = almacen.leer_todo()

    if df.empty:
        st.info("Aún no hay evaluaciones registradas. Carga la primera en la pestaña *Nueva evaluación*.")
    else:
        # Orden: más recientes arriba.
        if "registrado_en" in df.columns:
            df = df.sort_values("registrado_en", ascending=False)

        # --- Filtros ---
        c1, c2 = st.columns(2)
        with c1:
            f_prod = st.text_input("Filtrar por producto", "")
        with c2:
            f_prov = st.text_input("Filtrar por proveedor", "")

        vista = df.copy()
        if f_prod:
            vista = vista[vista["producto_evaluado"].str.contains(f_prod, case=False, na=False)]
        if f_prov:
            vista = vista[vista["proveedor"].str.contains(f_prov, case=False, na=False)]

        # --- Métricas rápidas ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Pruebas mostradas", len(vista))
        try:
            prom = pd.to_numeric(vista["promedio_sensorial"], errors="coerce").mean()
            m2.metric("Promedio sensorial", f"{prom:.2f}/5" if pd.notna(prom) else "—")
        except Exception:
            m2.metric("Promedio sensorial", "—")
        try:
            aptos = (vista["es_apto"] == "Sí").sum()
            m3.metric("Aprobadas como apta", int(aptos))
        except Exception:
            m3.metric("Aprobadas como apta", "—")

        # --- Tabla con etiquetas legibles ---
        cols_mostrar = [c for c in campos.COLUMNAS if c in vista.columns]
        tabla = vista[cols_mostrar].rename(columns=campos.ETIQUETAS)
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        # --- Descargas ---
        st.subheader("Descargar repositorio")
        d1, d2 = st.columns(2)
        with d1:
            csv = tabla.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ CSV", csv, "evaluaciones_mp.csv", "text/csv", use_container_width=True)
        with d2:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                tabla.to_excel(writer, index=False, sheet_name="Evaluaciones")
            st.download_button(
                "⬇️ Excel",
                buffer.getvalue(),
                "evaluaciones_mp.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
