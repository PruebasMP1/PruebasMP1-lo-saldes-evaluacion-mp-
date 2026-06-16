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

    def __init__(self, ruta: str = "datos/evaluaciones.db"):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self.ruta = ruta
        self._crear_tabla()

    def _conn(self):
        return sqlite3.connect(self.ruta)

    def _crear_tabla(self):
        cols = ", ".join(f'"{c}" TEXT' for c in campos.COLUMNAS)
        with self._conn() as cx:
            cx.execute(f'CREATE TABLE IF NOT EXISTS evaluaciones ({cols})')

    def guardar(self, registro: dict):
        valores = [str(registro.get(c, "")) for c in campos.COLUMNAS]
        marcadores = ", ".join("?" for _ in campos.COLUMNAS)
        nombres = ", ".join(f'"{c}"' for c in campos.COLUMNAS)
        with self._conn() as cx:
            cx.execute(
                f'INSERT INTO evaluaciones ({nombres}) VALUES ({marcadores})',
                valores,
            )

    def leer_todo(self) -> pd.DataFrame:
        with self._conn() as cx:
            try:
                df = pd.read_sql_query("SELECT * FROM evaluaciones", cx)
            except Exception:
                df = pd.DataFrame(columns=campos.COLUMNAS)
        return df


# --------------------------------------------------------------------------- #
#  Adaptador 2: planilla Google  (para la versión online persistente)
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

        sheet_id = st.secrets["gsheets"]["spreadsheet_id"]
        hoja_nombre = st.secrets["gsheets"].get("worksheet", "evaluaciones")
        libro = cliente.open_by_key(sheet_id)
        try:
            self.hoja = libro.worksheet(hoja_nombre)
        except Exception:
            self.hoja = libro.add_worksheet(hoja_nombre, rows=1000, cols=len(campos.COLUMNAS))
        # Asegurar fila de encabezados.
        encabezados = self.hoja.row_values(1)
        if encabezados != campos.COLUMNAS:
            self.hoja.update("A1", [campos.COLUMNAS])

    def guardar(self, registro: dict):
        fila = [str(registro.get(c, "")) for c in campos.COLUMNAS]
        self.hoja.append_row(fila, value_input_option="USER_ENTERED")

    def leer_todo(self) -> pd.DataFrame:
        registros = self.hoja.get_all_records()  # usa la fila 1 como encabezado
        if not registros:
            return pd.DataFrame(columns=campos.COLUMNAS)
        return pd.DataFrame(registros)


# --------------------------------------------------------------------------- #
#  Selección automática del almacén
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def obtener_almacen():
    """Devuelve el almacén a usar. Google Sheets si hay credenciales; si no, SQLite."""
    # ¿Hay credenciales configuradas? Si no existe el archivo de secrets (caso normal
    # cuando pruebas en tu PC), st.secrets lanza error: lo tomamos como "modo local"
    # y NO mostramos ninguna alerta.
    try:
        tiene_credenciales = ("gcp_service_account" in st.secrets) and ("gsheets" in st.secrets)
    except Exception:
        tiene_credenciales = False

    if tiene_credenciales:
        try:
            return _AlmacenGoogleSheets()
        except Exception as e:  # credenciales presentes pero mal puestas: avisar
            st.warning(f"Hay credenciales pero no pude conectar con Google Sheets ({e}). Usando archivo local.")
    return _AlmacenSQLite()


def nuevo_id() -> str:
    """ID legible y ordenable por fecha: EVAL-AAAAMMDD-HHMMSS."""
    return "EVAL-" + datetime.now(_TZ_CHILE).strftime("%Y%m%d-%H%M%S")


def marca_de_tiempo() -> str:
    return _ahora_chile()
