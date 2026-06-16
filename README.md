# 🥖 Evaluación de Materia Prima · Panificadora Lo Saldes

Espacio web que **conecta Abastecimiento con Producción**: cuando llevas una
materia prima alternativa, producción la prueba y registra aquí su evaluación.
Todo queda en un **repositorio consultable** para tener data y comparar proveedores.

Es el espejo digital de tu *"Ficha de Evaluación Técnica y Sensorial de Muestra
de Materia Prima"* (Word), con sus 4 secciones:

1. Información general (fecha, responsable, producto, proveedor, uso, lote)
2. Evaluación técnica (apariencia, textura, comportamiento térmico, merma, etc.)
3. Evaluación sensorial 0–5 (sabor, aroma, textura en boca, integración, aceptación)
4. Recomendación de Producción (¿apto?, ¿para qué uso?, ¿reformular?)

---

## ▶️ Probarla en tu PC (ahora mismo)

1. Abre **PowerShell** en esta carpeta (clic derecho → "Abrir en Terminal", o
   `cd` hasta `Documents\lo-saldes-evaluacion-mp`).
2. Ejecuta:

   ```powershell
   .\iniciar.ps1
   ```

   La primera vez crea el entorno e instala lo necesario (1–2 min). Luego abre
   sola en el navegador en `http://localhost:8501`.

Mientras pruebas en tu PC, los datos se guardan en un archivo local
(`datos/evaluaciones.db`). No necesitas configurar nada.

> **Glosario:**
> - *Streamlit* = forma de crear apps web con Python (lo que ves en el navegador).
> - *PowerShell* = la terminal de Windows donde escribes comandos.
> - *localhost:8501* = la dirección donde corre la app **solo en tu PC**.

---

## 🌐 Ponerla en internet (link/QR para producción)

Eso está en **[DEPLOY.md](DEPLOY.md)**. Resumen del porqué:

- Para que producción entre desde su celular con un **link o QR**, la app debe
  vivir en la nube (usamos **Streamlit Community Cloud**, gratis).
- El repositorio de datos se guarda en una **planilla Google** para que **no se
  borre** (el disco de la nube sí se borra; la planilla no). De paso, puedes abrir
  esa planilla y verla/exportarla como Excel cuando quieras.

---

## 🗂️ Archivos del proyecto

| Archivo | Qué hace |
|---|---|
| `app.py` | La app: formulario + repositorio. |
| `campos.py` | **Las preguntas de la ficha**. Edita aquí para agregar/quitar campos. |
| `almacenamiento.py` | Dónde se guardan los datos (archivo local o planilla Google). |
| `requirements.txt` | Librerías que necesita la app. |
| `iniciar.ps1` | Lanzador para tu PC. |
| `DEPLOY.md` | Guía paso a paso para publicarla en internet. |
| `.streamlit/secrets.toml.example` | Plantilla de credenciales (no contiene claves). |

---

## ➕ ¿Quieres cambiar una pregunta?

Abre `campos.py` y edita la sección correspondiente. Todo el formulario y el
repositorio se ajustan solos. No toques nada más.
