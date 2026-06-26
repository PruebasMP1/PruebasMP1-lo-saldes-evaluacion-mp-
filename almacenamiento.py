# -*- coding: utf-8 -*-
"""
almacenamiento.py — Dónde se guardan las evaluaciones.

Idea clave (esto es lo que hace que la app funcione IGUAL en tu PC y online):

  • En tu PC, mientras pruebas: guarda en un archivo local SQLite
    ('datos/evaluaciones.db'). No necesitas configurar nada.

  • En la nube (Streamlit Community Cloud): guarda en una PLANILLA GOOGLE.
    Esto es importante porque el disco de la nube se borra cada cierto tiempo;
    la planilla NO. Así tu repositorio de pruebas sobrevive y, de yapa, puedes
    abrir la planilla en Google y verla/exportarla como Excel cuando quieras.

La app elige sola: si encuentra las credenciales de Google configuradas
(en st.secrets), usa la planilla; si no, usa el archivo local.

Glosario rápido:
  - SQLite     = una base de datos guardada en UN solo archivo, sin instalar nada.
  - st.secrets = la "caja fuerte" de Streamlit para guardar claves/credenciales.
  - gspread    = librería de Python para leer/escribir planillas de Google.
"""
from __future__ import annotations

import base64
import io
import os
import sqlite3
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st

import campos

# Hora de Chile (UTC-4 / UTC-3 según horario; usamos -4 fijo, suficiente para registro).
_TZ_CHILE = timezone(timedelta(hours=-4))


def _ahora_chile() -> str:
    return datetime.now(_TZ_CHILE).strftime("%Y-%m-%d %H:%M")


# --------------------------------------------------------------------------- #
#  Adaptador 1: archivo local SQLite  (para probar en tu PC)
# --------------------------------------------------------------------------- #
class _AlmacenSQLite:
    nombre = "Archivo local (SQLite)"

    def __init__(self, ruta: str = None):
        # Ruta ANCLADA a la carpeta del código (no depende de desde dónde se lance
        # la app). Así el formulario y los scripts siempre leen el mismo archivo.
        if ruta is None:
            base = os.path.dirname(os.path.abspath(__file__))
            ruta = os.path.join(base, "datos", "evaluaciones.db")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self.ruta = ruta
        self._listas = set()  # tablas ya preparadas en esta sesión

    def _conn(self):
        return sqlite3.connect(self.ruta)

    def _preparar(self, tabla: str, columnas: list):
        if tabla in self._listas:
            return
        cols = ", ".join(f'"{c}" TEXT' for c in columnas)
        with self._conn() as cx:
            cx.execute(f'CREATE TABLE IF NOT EXISTS "{tabla}" ({cols})')
            # Agregar columnas nuevas que falten (auto-migración).
            existentes = {r[1] for r in cx.execute(f'PRAGMA table_info("{tabla}")')}
            for c in columnas:
                if c not in existentes:
                    cx.execute(f'ALTER TABLE "{tabla}" ADD COLUMN "{c}" TEXT')
        self._listas.add(tabla)

    def guardar(self, tabla: str, columnas: list, registro: dict):
        self._preparar(tabla, columnas)
        valores = [str(registro.get(c, "")) for c in columnas]
        marcadores = ", ".join("?" for _ in columnas)
        nombres = ", ".join(f'"{c}"' for c in columnas)
        with self._conn() as cx:
            cx.execute(f'INSERT INTO "{tabla}" ({nombres}) VALUES ({marcadores})', valores)

    def leer(self, tabla: str, columnas: list) -> pd.DataFrame:
        self._preparar(tabla, columnas)
        with self._conn() as cx:
            try:
                return pd.read_sql_query(f'SELECT * FROM "{tabla}"', cx)
            except Exception:
                return pd.DataFrame(columns=columnas)


# --------------------------------------------------------------------------- #
#  Adaptador 2: Neon / Postgres  (base de datos en la nube, persistente)
# --------------------------------------------------------------------------- #
class _AlmacenPostgres:
    nombre = "Base de datos en la nube (Neon · Postgres)"

    def __init__(self, dsn: str):
        from sqlalchemy import create_engine

        # Neon a veces entrega "postgres://"; SQLAlchemy quiere "postgresql://".
        if dsn.startswith("postgres://"):
            dsn = dsn.replace("postgres://", "postgresql://", 1)
        # Asegurar conexión cifrada (Neon lo exige).
        if "sslmode=" not in dsn:
            dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
        # pool_pre_ping = reconecta solo si Neon "durmió" la base por inactividad.
        self.engine = create_engine(dsn, pool_pre_ping=True)
        self._listas = set()  # tablas ya preparadas en esta sesión

    def _preparar(self, tabla: str, columnas: list):
        if tabla in self._listas:
            return
        from sqlalchemy import text
        cols = ", ".join(f'"{c}" TEXT' for c in columnas)
        pk = columnas[0]  # primera columna = clave primaria (id o id_muestra)
        with self.engine.begin() as cx:
            cx.execute(text(f'CREATE TABLE IF NOT EXISTS "{tabla}" ({cols}, PRIMARY KEY ("{pk}"))'))
            # Agregar columnas nuevas que falten (auto-migración).
            for c in columnas:
                cx.execute(text(f'ALTER TABLE "{tabla}" ADD COLUMN IF NOT EXISTS "{c}" TEXT'))
        self._listas.add(tabla)

    def guardar(self, tabla: str, columnas: list, registro: dict):
        from sqlalchemy import text
        self._preparar(tabla, columnas)
        nombres = ", ".join(f'"{c}"' for c in columnas)
        binds = ", ".join(f":{c}" for c in columnas)
        params = {c: str(registro.get(c, "")) for c in columnas}
        with self.engine.begin() as cx:
            cx.execute(text(f'INSERT INTO "{tabla}" ({nombres}) VALUES ({binds})'), params)

    def leer(self, tabla: str, columnas: list) -> pd.DataFrame:
        self._preparar(tabla, columnas)
        try:
            return pd.read_sql(f'SELECT * FROM "{tabla}"', self.engine)
        except Exception:
            return pd.DataFrame(columns=columnas)


# --------------------------------------------------------------------------- #
#  Adaptador 3: planilla Google  (alternativa persistente; queda disponible)
# --------------------------------------------------------------------------- #
class _AlmacenGoogleSheets:
    nombre = "Planilla Google (persistente)"

    def __init__(self):
        import gspread
        from google.oauth2.service_account import Credentials

        cred_info = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(cred_info, scopes=scopes)
        cliente = gspread.authorize(creds)
        self.libro = cliente.open_by_key(st.secrets["gsheets"]["spreadsheet_id"])

    def _hoja(self, tabla: str, columnas: list):
        """Devuelve la hoja (una por tabla), creándola y poniéndole encabezados."""
        try:
            hoja = self.libro.worksheet(tabla)
        except Exception:
            hoja = self.libro.add_worksheet(tabla, rows=1000, cols=len(columnas))
        if hoja.row_values(1) != columnas:
            hoja.update("A1", [columnas])
        return hoja

    def guardar(self, tabla: str, columnas: list, registro: dict):
        hoja = self._hoja(tabla, columnas)
        fila = [str(registro.get(c, "")) for c in columnas]
        hoja.append_row(fila, value_input_option="USER_ENTERED")

    def leer(self, tabla: str, columnas: list) -> pd.DataFrame:
        registros = self._hoja(tabla, columnas).get_all_records()
        if not registros:
            return pd.DataFrame(columns=columnas)
        return pd.DataFrame(registros)


# --------------------------------------------------------------------------- #
#  Selección automática del almacén
# --------------------------------------------------------------------------- #
def _leer_dsn_postgres():
    """Lee el texto de conexión a Neon/Postgres desde los secretos (si existe)."""
    try:
        if "database_url" in st.secrets:
            return str(st.secrets["database_url"])
        if "neon" in st.secrets and "dsn" in st.secrets["neon"]:
            return str(st.secrets["neon"]["dsn"])
    except Exception:
        return None
    return None


@st.cache_resource(show_spinner=False)
def obtener_almacen():
    """Elige el almacén: Neon (preferido) → Google Sheets → archivo local SQLite.

    Si no hay secretos configurados (caso normal al probar en tu PC), usa el
    archivo local sin mostrar ninguna alerta.
    """
    # 1) Neon / Postgres — la opción elegida para la nube.
    dsn = _leer_dsn_postgres()
    if dsn:
        try:
            return _AlmacenPostgres(dsn)
        except Exception as e:
            st.warning(f"Hay conexión a la base pero no pude conectar ({e}). Usando archivo local.")

    # 2) Google Sheets — alternativa, si algún día configuras esas credenciales.
    try:
        tiene_credenciales = ("gcp_service_account" in st.secrets) and ("gsheets" in st.secrets)
    except Exception:
        tiene_credenciales = False
    if tiene_credenciales:
        try:
            return _AlmacenGoogleSheets()
        except Exception as e:
            st.warning(f"Hay credenciales pero no pude conectar con Google Sheets ({e}). Usando archivo local.")

    # 3) Archivo local (para probar en tu PC).
    return _AlmacenSQLite()


# --------------------------------------------------------------------------- #
#  Fotos: comprimir una imagen subida a texto (base64) y volver a leerla.
# --------------------------------------------------------------------------- #
# Límite seguro de caracteres por celda de Google Sheets (el real es 50.000).
_LIMITE_CHARS = 48000


def preparar_imagen(archivo_subido) -> str:
    """Recibe una foto subida y devuelve la imagen comprimida como texto base64.

    La achica y baja calidad hasta que entre en el límite de una celda de la
    planilla Google. Devuelve "" si no se subió ninguna foto.
    """
    if archivo_subido is None:
        return ""
    from PIL import Image  # se importa aquí para no exigir Pillow si no hay fotos

    try:
        imagen = Image.open(archivo_subido).convert("RGB")
    except Exception:
        return ""

    # Va probando tamaños/calidades de mayor a menor hasta que el texto entre.
    ultimo = ""
    for max_lado, calidad in [(640, 70), (512, 60), (400, 55), (320, 45), (240, 40)]:
        copia = imagen.copy()
        copia.thumbnail((max_lado, max_lado))
        buffer = io.BytesIO()
        copia.save(buffer, format="JPEG", quality=calidad)
        texto = base64.b64encode(buffer.getvalue()).decode("ascii")
        ultimo = texto
        if len(texto) <= _LIMITE_CHARS:
            return texto
    return ultimo  # si nada entró, igual guardamos la versión más chica


def imagen_desde_texto(texto: str):
    """Devuelve los bytes de la imagen desde el texto base64 (o None si está vacío)."""
    if not texto or not isinstance(texto, str):
        return None
    if texto.startswith("data:"):  # por si quedó con prefijo
        texto = texto.split(",", 1)[-1]
    try:
        return base64.b64decode(texto)
    except Exception:
        return None


def nuevo_id() -> str:
    """ID legible y ordenable por fecha: EVAL-AAAAMMDD-HHMMSS."""
    return "EVAL-" + datetime.now(_TZ_CHILE).strftime("%Y%m%d-%H%M%S")


def nuevo_id_muestra() -> str:
    """N° de muestra legible y ordenable: MUE-AAAAMMDD-HHMMSS."""
    return "MUE-" + datetime.now(_TZ_CHILE).strftime("%Y%m%d-%H%M%S")


def marca_de_tiempo() -> str:
    return _ahora_chile()
