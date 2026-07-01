# -*- coding: utf-8 -*-
"""
monitor_salud.py — Vigilante de la app (chequeo de salud).

Revisa dos cosas y avisa si algo anda mal:
  1) Que la app publicada responda (está viva).
  2) Que la base Neon esté conectada y con las tablas (que SÍ se está guardando).

Lo usa el chequeo automático diario. También lo puedes correr a mano:
    .venv\\Scripts\\python.exe monitor_salud.py

La conexión a Neon se lee del archivo local .monitor/neon_dsn.txt (fuera de git)
o de la variable de entorno NEON_DSN. Sale con código 1 si detecta problemas.
"""
import os
import sys
import urllib.request

APP_URL = "https://g8v5frppzqqynukttbxtry.streamlit.app/"


def leer_dsn():
    env = os.environ.get("NEON_DSN")
    if env:
        return env.strip()
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".monitor", "neon_dsn.txt")
    if os.path.exists(ruta):
        return open(ruta, encoding="utf-8").read().strip()
    return None


def main():
    problemas = []

    # 1) ¿La app responde? (sin seguir el redirect de login, para no confundirlo con caída)
    class _SinRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    try:
        opener = urllib.request.build_opener(_SinRedirect)
        code = opener.open(APP_URL, timeout=30).status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        code = None
        problemas.append(f"La app no responde: {e}")

    if code is not None:
        print(f"App HTTP: {code}")
        if code >= 500:
            problemas.append(f"La app está caída (código {code})")
        elif code in (302, 303, 307):
            print("  (nota: la app está PRIVADA — redirige a login. El equipo no puede entrar sin ponerla pública.)")

    # 2) ¿Neon vivo y guardando?
    dsn = leer_dsn()
    if not dsn:
        problemas.append("No encontré la conexión a Neon (.monitor/neon_dsn.txt ni NEON_DSN)")
    else:
        try:
            from sqlalchemy import create_engine, text
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            if "sslmode=" not in dsn:
                dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
            eng = create_engine(dsn, pool_pre_ping=True)
            with eng.connect() as cx:
                n_eval = cx.execute(text("select count(*) from evaluaciones")).scalar()
                n_mues = cx.execute(text("select count(*) from muestras")).scalar()
            print(f"Neon OK · evaluaciones={n_eval} · muestras={n_mues}")
        except Exception as e:
            problemas.append(f"Neon inaccesible / sin guardar: {e}")

    if problemas:
        print("\n[ALERTA] revisar:")
        for p in problemas:
            print("  -", p)
        return 1
    print("\n[OK] app viva y guardando en Neon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
