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
#  Atajos de lectura/escritura para las dos tablas (evaluaciones y muestras)
# --------------------------------------------------------------------------- #
def leer_evals():
    return almacen.leer("evaluaciones", campos.COLUMNAS)


def guardar_eval(registro):
    almacen.guardar("evaluaciones", campos.COLUMNAS, registro)


def leer_muestras():
    return almacen.leer("muestras", campos.COLUMNAS_MUESTRA)


def guardar_muestra(registro):
    almacen.guardar("muestras", campos.COLUMNAS_MUESTRA, registro)


def muestras_pendientes():
    """Muestras entregadas que aún NO tienen una evaluación enlazada."""
    m = leer_muestras()
    if m.empty:
        return m
    e = leer_evals()
    usados = set(e["id_muestra"].astype(str)) if "id_muestra" in e.columns else set()
    return m[~m["id_muestra"].astype(str).isin(usados)]


# --------------------------------------------------------------------------- #
#  Encabezado
# --------------------------------------------------------------------------- #
st.title("🥖 Evaluación de Materia Prima")
st.caption(
    "Panificadora Lo Saldes · puente entre Abastecimiento y Producción. "
    f"Guardando en: **{almacen.nombre}**"
)

# Blindaje: aviso imposible de ignorar si NO estamos en una base persistente.
if not getattr(almacen, "persistente", False):
    st.error(
        "⚠️ **MODO TEMPORAL — los datos NO se guardan.** Ahora mismo se está usando "
        "almacenamiento local; en la nube esto se **borra al reiniciar**. "
        "**No cargues datos reales** hasta que aquí arriba diga "
        "*«Guardando en: Base de datos en la nube (Neon · Postgres)»*.",
        icon="🚨",
    )

tab_muestra, tab_form, tab_repo, tab_dash = st.tabs(
    ["📦 Entrega de muestra", "📝 Evaluación", "📊 Repositorio de pruebas", "📈 Dashboard"]
)


# --------------------------------------------------------------------------- #
#  Helper: dibuja un campo según su tipo y devuelve el valor ingresado.
#  'key' permite reutilizar el mismo campo en formularios distintos sin choques.
# --------------------------------------------------------------------------- #
def _widget(clave, etiqueta, tipo, opciones, key=None):
    key = key or clave
    if tipo == "text":
        return st.text_input(etiqueta, key=key)
    if tipo == "textarea":
        return st.text_area(etiqueta, key=key, height=80)
    if tipo == "date":
        return st.date_input(etiqueta, key=key).strftime("%Y-%m-%d")
    if tipo == "number":
        return st.number_input(etiqueta, min_value=0.0, max_value=100.0, step=0.5, key=key)
    if tipo == "select":
        return st.selectbox(etiqueta, options=["—"] + opciones, key=key)
    if tipo == "multiselect":
        return ", ".join(st.multiselect(etiqueta, options=opciones, key=key))
    if tipo == "score":
        return st.slider(etiqueta + "  (0 = malo · 5 = excelente)", 0, 5, 3, key=key)
    return st.text_input(etiqueta, key=key)


# =========================================================================== #
#  PESTAÑA 0 · ENTREGA DE MUESTRA  (módulo previo — lo usa Abastecimiento)
# =========================================================================== #
with tab_muestra:
    st.info(
        "**Abastecimiento:** registra aquí la muestra que llevas a Producción. "
        "Quedará como *pendiente* hasta que Producción la pruebe y la enlace a una evaluación.",
        icon="📦",
    )

    with st.form("form_muestra", clear_on_submit=True):
        vals_m = {}
        for clave, etiqueta, tipo, opciones in campos.MUESTRA:
            vals_m[clave] = _widget(clave, etiqueta, tipo, opciones, key="m_" + clave)
        enviar_m = st.form_submit_button(
            "📦 Registrar muestra entregada", type="primary", use_container_width=True
        )

    if enviar_m:
        if not vals_m.get("producto") or not vals_m.get("proveedor"):
            st.error("Faltan datos: indica al menos **Materia prima** y **Proveedor**.")
        else:
            vals_m["id_muestra"] = alm.nuevo_id_muestra()
            vals_m["registrado_en"] = alm.marca_de_tiempo()
            guardar_muestra(vals_m)
            st.success(
                f"✅ Muestra registrada: **{vals_m['id_muestra']}** "
                f"({vals_m['producto']} / {vals_m['proveedor']}). "
                "Producción ya puede elegirla en la pestaña *Evaluación*."
            )

    st.divider()
    st.subheader("⏳ Muestras pendientes de evaluación")
    pend = muestras_pendientes()
    if pend.empty:
        st.caption("No hay muestras pendientes. ¡Todo lo entregado ya fue evaluado!")
    else:
        cols_p = [c for c in campos.COLUMNAS_MUESTRA if c in pend.columns]
        st.dataframe(
            pend[cols_p].rename(columns=campos.ETIQUETAS_MUESTRA),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================================== #
#  PESTAÑA 1 · FORMULARIO
# =========================================================================== #
with tab_form:
    # --- Módulo previo: elegir la muestra entregada por Abastecimiento ---
    pend = muestras_pendientes()
    muestra_sel = None
    if not pend.empty:
        opciones_m = {"— Sin muestra asociada (evaluación libre) —": None}
        for _, r in pend.iterrows():
            etq = (f"{r['id_muestra']} · {r.get('producto', '')} / {r.get('proveedor', '')}"
                   f" · entregada {r.get('fecha_entrega', '')}")
            opciones_m[etq] = r
        sel_label = st.selectbox(
            "¿Evalúas una muestra entregada por Abastecimiento?",
            list(opciones_m.keys()),
            key="sel_muestra",
        )
        muestra_sel = opciones_m[sel_label]
        if muestra_sel is not None:
            st.success(
                f"🔗 Evaluando muestra **{muestra_sel['id_muestra']}** — "
                f"{muestra_sel.get('producto', '')} / {muestra_sel.get('proveedor', '')}. "
                f"Objetivo: {muestra_sel.get('objetivo', '') or '—'}"
            )
    else:
        st.caption(
            "No hay muestras pendientes registradas por Abastecimiento. "
            "Puedes igual hacer una evaluación libre."
        )

    st.info(
        "Completa la ficha luego de probar la muestra. Los campos de sabor, aroma, "
        "etc. van de **0 a 5**. Al final presiona **Guardar evaluación**.",
        icon="📝",
    )

    with st.form("ficha", clear_on_submit=True):
        valores = {}
        foto_mp_file = None
        foto_resultado_file = None
        for titulo, lista in campos.SECCIONES:
            st.subheader(titulo)
            for clave, etiqueta, tipo, opciones in lista:
                # Si hay muestra asociada, producto y proveedor vienen de ella (no se reescriben).
                if muestra_sel is not None and clave == "producto_evaluado":
                    valores[clave] = str(muestra_sel.get("producto", "") or "")
                    st.text_input(etiqueta, value=valores[clave], disabled=True, key="lock_prod")
                elif muestra_sel is not None and clave == "proveedor":
                    valores[clave] = str(muestra_sel.get("proveedor", "") or "")
                    st.text_input(etiqueta, value=valores[clave], disabled=True, key="lock_prov")
                else:
                    valores[clave] = _widget(clave, etiqueta, tipo, opciones)

            # Foto de la materia prima evaluada → al final de la sección 1.
            if titulo.startswith("1."):
                foto_mp_file = st.file_uploader(
                    "📷 Foto de la materia prima evaluada",
                    type=["jpg", "jpeg", "png"],
                    key="foto_mp",
                    help="Desde el celular puedes tomar la foto en el momento o elegirla de la galería.",
                )
            # Foto del resultado final → al final de la sección 4.
            if titulo.startswith("4."):
                foto_resultado_file = st.file_uploader(
                    "📷 Foto del resultado final (producto ya preparado)",
                    type=["jpg", "jpeg", "png"],
                    key="foto_res",
                )
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
            # Enlace con la muestra entregada (vacío si fue evaluación libre).
            valores["id_muestra"] = (
                str(muestra_sel["id_muestra"]) if muestra_sel is not None else ""
            )

            # Fotos → comprimidas a texto antes de guardar.
            valores["foto_materia_prima"] = alm.preparar_imagen(foto_mp_file)
            valores["foto_resultado"] = alm.preparar_imagen(foto_resultado_file)

            guardar_eval(valores)
            enlace = f" · enlazada a muestra **{valores['id_muestra']}**" if valores["id_muestra"] else ""
            st.success(
                f"¡Guardado! ID **{valores['id']}** · promedio sensorial **{promedio}/5**{enlace}. "
                "Lo verás en la pestaña *Repositorio*."
            )
            st.balloons()


# =========================================================================== #
#  PESTAÑA 2 · REPOSITORIO
# =========================================================================== #
with tab_repo:
    df = leer_evals()

    if df.empty:
        st.info("Aún no hay evaluaciones registradas. Carga la primera en la pestaña *Evaluación*.")
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

        # --- Tabla con etiquetas legibles (sin el texto crudo de las fotos) ---
        cols_mostrar = [
            c for c in campos.COLUMNAS
            if c in vista.columns and c not in campos.CLAVES_FOTO
        ]
        tabla = vista[cols_mostrar].copy()
        # En vez del texto de la imagen, una marca de si hay foto o no.
        for clave in campos.CLAVES_FOTO:
            if clave in vista.columns:
                tabla[clave] = vista[clave].apply(lambda x: "✅" if str(x).strip() else "—")
        tabla = tabla.rename(columns=campos.ETIQUETAS)
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        # --- Visor de fotos por evaluación ---
        tiene_fotos = any(
            c in vista.columns and vista[c].astype(str).str.strip().any()
            for c in campos.CLAVES_FOTO
        )
        if tiene_fotos:
            st.subheader("📷 Ver fotos de una evaluación")
            opciones = {
                f"{r.get('id', '?')} · {r.get('producto_evaluado', '')}": i
                for i, r in vista.iterrows()
            }
            etiqueta_sel = st.selectbox("Elige una evaluación", list(opciones.keys()))
            fila = vista.loc[opciones[etiqueta_sel]]
            f1, f2 = st.columns(2)
            with f1:
                img_mp = alm.imagen_desde_texto(fila.get("foto_materia_prima", ""))
                st.caption("Materia prima")
                st.image(img_mp, use_container_width=True) if img_mp else st.write("— sin foto —")
            with f2:
                img_res = alm.imagen_desde_texto(fila.get("foto_resultado", ""))
                st.caption("Resultado final")
                st.image(img_res, use_container_width=True) if img_res else st.write("— sin foto —")

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


# =========================================================================== #
#  PESTAÑA 3 · DASHBOARD  (protegido con clave corta propia)
# =========================================================================== #
def _dashboard_desbloqueado() -> bool:
    """El dashboard pide una clave corta SOLO si se configuró 'dash_password'.
    Así producción carga datos libre, pero los números de gestión quedan reservados."""
    try:
        clave_dash = st.secrets.get("dash_password")
    except Exception:
        clave_dash = None
    if not clave_dash:
        return True  # sin clave configurada → dashboard visible (útil al probar en PC)
    if st.session_state.get("dash_ok"):
        return True
    st.subheader("🔒 Dashboard reservado")
    st.caption("Esta sección es para Control de Gestión. Ingresa la clave para verla.")
    clave = st.text_input("Clave del dashboard", type="password", key="dash_clave")
    if st.button("Ver dashboard", key="dash_btn"):
        if clave == str(clave_dash):
            st.session_state["dash_ok"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta.")
    return False


with tab_dash:
    if not _dashboard_desbloqueado():
        st.stop()

    df = leer_evals()

    if df.empty:
        st.info("Aún no hay datos. Carga algunas evaluaciones para poder comparar y decidir.")
    else:
        # --- Columnas auxiliares numéricas (para rankear y graficar) ---
        df = df.copy()
        df["_prom"] = pd.to_numeric(df.get("promedio_sensorial"), errors="coerce")
        df["_merma"] = pd.to_numeric(df.get("merma_estimada_pct"), errors="coerce")
        for k in campos.CLAVES_SENSORIAL:
            df["_" + k] = pd.to_numeric(df.get(k), errors="coerce")
        # Orden de aptitud: apta primero (0), con observaciones (1), no (2), sin dato (3).
        _ORDEN_APTO = {"Sí": 0, "Con observaciones": 1, "No": 2}
        df["_rank_apto"] = df.get("es_apto", "").map(_ORDEN_APTO).fillna(3)

        def _mejor_opcion(grupo):
            """Devuelve la fila recomendada de un grupo: apta con mayor sensorial y menor merma."""
            aptas = grupo[grupo["es_apto"] == "Sí"]
            base = aptas if not aptas.empty else grupo
            return base.sort_values(["_prom", "_merma"], ascending=[False, True]).iloc[0], not aptas.empty

        # --- Indicadores de contexto ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Pruebas registradas", len(df))
        n_prod = df["producto_evaluado"].replace("", pd.NA).nunique()
        c2.metric("Materias primas evaluadas", int(n_prod))
        aptas_tot = (df["es_apto"] == "Sí").sum()
        c3.metric("% de pruebas aprobadas", f"{(aptas_tot/len(df)*100):.0f}%")

        st.divider()

        # ====================================================================== #
        #  RECOMENDACIÓN POR MATERIA PRIMA  (la vista para decidir de un vistazo)
        # ====================================================================== #
        st.subheader("🏆 Recomendación por materia prima")
        st.caption("Para cada insumo, la alternativa mejor evaluada (apta, mejor sensorial, menor merma).")

        filas = []
        for prod, g in df.groupby("producto_evaluado"):
            if not str(prod).strip():
                continue
            mejor, hay_apta = _mejor_opcion(g)
            filas.append({
                "Materia prima": prod,
                "Proveedor recomendado": mejor.get("proveedor", "?") if hay_apta else "— sin opción apta —",
                "Sensorial (0-5)": f"{mejor['_prom']:.1f}" if pd.notna(mejor["_prom"]) else "—",
                "Merma %": f"{mejor['_merma']:.0f}" if pd.notna(mejor["_merma"]) else "—",
                "N° alternativas probadas": g["proveedor"].replace("", pd.NA).nunique(),
                "Total pruebas": len(g),
            })
        if filas:
            resumen = pd.DataFrame(filas).sort_values("Materia prima")
            st.dataframe(resumen, use_container_width=True, hide_index=True)
        else:
            st.info("Falta completar el campo 'Producto evaluado' para poder recomendar.")

        st.divider()

        # ====================================================================== #
        #  COMPARADOR EN DETALLE  (elegir un insumo y ver todas sus alternativas)
        # ====================================================================== #
        st.subheader("🔎 Comparar alternativas en detalle")
        productos = sorted([p for p in df["producto_evaluado"].dropna().unique() if str(p).strip()])
        if productos:
            sel = st.selectbox("Elige la materia prima a decidir", productos)
            sub = df[df["producto_evaluado"] == sel].copy().reset_index(drop=True)

            # Recomendación destacada para el insumo elegido.
            mejor, hay_apta = _mejor_opcion(sub)
            prom_txt = f"{mejor['_prom']:.1f}/5" if pd.notna(mejor["_prom"]) else "s/d"
            merma_txt = f"{mejor['_merma']:.0f}%" if pd.notna(mejor["_merma"]) else "s/d"
            if hay_apta:
                st.success(
                    f"✅ **Recomendada para {sel}: {mejor.get('proveedor', '?')}** — "
                    f"sensorial {prom_txt}, apta, merma {merma_txt}."
                )
            else:
                st.warning(
                    f"⚠️ Ninguna alternativa de **{sel}** fue marcada como *apta* todavía. "
                    f"La mejor evaluada hasta ahora es **{mejor.get('proveedor', '?')}** ({prom_txt})."
                )

            # Tabla comparativa con los factores que importan para elegir.
            cols_decision = {
                "proveedor": "Proveedor",
                "es_apto": "¿Apta?",
                "_prom": "Sensorial",
                "merma_estimada_pct": "Merma %",
                "compatibilidad_masas": "Compat. masas",
                "facilidad_manipulacion": "Facilidad",
                "requiere_ajustes": "¿Ajustes?",
                "uso_recomendado": "Usos recomendados",
                "fecha_evaluacion": "Fecha",
            }
            presentes = [c for c in cols_decision if c in sub.columns]
            tabla_dec = sub.sort_values(["_rank_apto", "_prom"], ascending=[True, False])[presentes].copy()
            tabla_dec["_prom"] = tabla_dec["_prom"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
            tabla_dec = tabla_dec.rename(columns=cols_decision)
            st.markdown("**Todas las alternativas probadas** (la mejor arriba)")
            st.dataframe(tabla_dec, use_container_width=True, hide_index=True)

            # Perfil sensorial por alternativa: muestra POR QUÉ puntúa así.
            cols_sens = ["_" + k for k in campos.CLAVES_SENSORIAL]
            if sub[cols_sens].notna().any().any():
                # Etiqueta única por alternativa (proveedor + fecha).
                sub["_opcion"] = (
                    sub["proveedor"].replace("", "(s/proveedor)").fillna("(s/proveedor)")
                    + " · " + sub.get("fecha_evaluacion", "").astype(str)
                )
                sub["_opcion"] = sub["_opcion"] + sub.groupby("_opcion").cumcount().apply(
                    lambda n: "" if n == 0 else f" ({n + 1})"
                )
                perfil = sub.set_index("_opcion")[cols_sens]
                perfil.columns = [campos.ETIQUETAS.get(k, k) for k in campos.CLAVES_SENSORIAL]
                st.markdown("**Perfil sensorial por alternativa** (0–5 en cada atributo)")
                st.bar_chart(perfil.T)
        else:
            st.info("Aún no hay productos con nombre para comparar.")
