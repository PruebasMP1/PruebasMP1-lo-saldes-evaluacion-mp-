# 🌐 Publicar la app en internet (con datos que NO se borran)

Meta: un link público `https://<algo>.streamlit.app` (y su QR) que producción
pueda abrir desde el celular, y que las evaluaciones queden guardadas para siempre
en una **planilla Google**.

Hay **3 etapas**. Tómalas con calma; cada una se hace **una sola vez**.
Cuando quieras, las hacemos juntos y yo te voy guiando comando por comando.

---

## Etapa A · La planilla Google que guarda los datos

> Por qué: la nube de Streamlit borra los archivos cada cierto tiempo. Una planilla
> Google NO se borra y te sirve además como respaldo en formato Excel.

1. Crea una planilla nueva en Google Sheets (en blanco). Ponle nombre, ej.
   *"Evaluaciones MP Lo Saldes"*.
2. Mira la dirección (URL) de la planilla. El **ID** es el texto largo entre `/d/` y `/edit`:
   `https://docs.google.com/spreadsheets/d/`**`ESTE_ES_EL_ID`**`/edit`
   Guárdalo, lo usarás en la Etapa C.

---

## Etapa B · La "cuenta de servicio" (la llave que deja a la app escribir en la planilla)

> Glosario: una *cuenta de servicio* es un usuario robot de Google. La app entra a
> la planilla como ese robot, no como tú. Google entrega un archivo **JSON** con su llave.

1. Entra a **https://console.cloud.google.com** (con tu cuenta Google).
2. Arriba, crea un **proyecto nuevo** (ej. `lo-saldes-mp`).
3. Menú ☰ → **APIs y servicios → Biblioteca**. Busca y **habilita**:
   - *Google Sheets API*
   - *Google Drive API*
4. Menú ☰ → **APIs y servicios → Credenciales → Crear credenciales → Cuenta de servicio**.
   Ponle un nombre (ej. `escritor-evaluaciones`) y créala.
5. Entra a esa cuenta de servicio → pestaña **Claves → Agregar clave → Crear clave nueva → JSON**.
   Se descarga un archivo `.json`. **Guárdalo bien, no lo subas a internet.**
6. Abre ese JSON y copia el valor de **`client_email`** (algo como
   `escritor-evaluaciones@...iam.gserviceaccount.com`).
7. Vuelve a tu **planilla Google** → botón **Compartir** → pega ese correo y dale
   permiso de **Editor**. (Así el robot puede escribir.)

---

## Etapa C · Subir el código y desplegar

### C.1 · Cuentas (gratis, una vez)
- **GitHub** → https://github.com (aloja el código).
- **Streamlit Community Cloud** → https://share.streamlit.io (entra con "Continue with GitHub").

### C.2 · Subir el código a GitHub
En PowerShell, dentro de esta carpeta:

```powershell
git init
git add .
git commit -m "App evaluacion materia prima"
```

Luego, en GitHub crea un repositorio **nuevo y vacío** (puede ser **privado**),
copia su URL y ejecuta (cambia TU_USUARIO):

```powershell
git remote add origin https://github.com/TU_USUARIO/lo-saldes-evaluacion-mp.git
git branch -M main
git push -u origin main
```

> Tranquilo: el `.gitignore` ya evita que se suban tus datos locales y tus claves.

### C.3 · Desplegar
1. En https://share.streamlit.io → **Create app → Deploy from GitHub**.
2. Elige tu repositorio, rama `main`, archivo principal **`app.py`**.
3. En **Advanced settings → Secrets**, pega esto (rellena con tus datos del JSON y
   el ID de la planilla — usa `.streamlit/secrets.toml.example` como guía):

   ```toml
   app_password = "una-clave-para-producción"

   [gsheets]
   spreadsheet_id = "EL_ID_DE_TU_PLANILLA"
   worksheet = "evaluaciones"

   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "...@....iam.gserviceaccount.com"
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```
4. **Deploy**. En 1–2 minutos tendrás tu link `https://...streamlit.app`.

### C.4 · Compartir con producción
- Manda el **link + la contraseña** por WhatsApp interno.
- Para un **QR**: pega el link en cualquier generador de QR (ej. busca "generar QR")
  e imprímelo para pegarlo en la zona de pruebas de producción.

---

## 🔄 Actualizar la app después
Haz cambios en tu PC y luego:

```powershell
git add . ; git commit -m "ajustes" ; git push
```

Streamlit Cloud redepliega solo en ~1 minuto.

---

## ✅ Cómo saber que quedó con datos persistentes
Cuando entres a la app publicada, abajo del título dirá:
**"Guardando en: Planilla Google (persistente)"**. Si dijera *"Archivo local"*, es que
faltó algún secreto — revísalos en Streamlit Cloud → Settings → Secrets.
