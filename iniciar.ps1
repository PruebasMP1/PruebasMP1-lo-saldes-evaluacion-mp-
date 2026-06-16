# Lanza la app en tu PC. Abre PowerShell en esta carpeta y ejecuta:  .\iniciar.ps1
# La primera vez crea el entorno e instala lo necesario (puede tardar 1-2 min).
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path "$here\.venv")) {
    Write-Host "Creando entorno virtual (.venv)..." -ForegroundColor Cyan
    python -m venv "$here\.venv"
    & "$here\.venv\Scripts\python.exe" -m pip install --upgrade pip
    & "$here\.venv\Scripts\python.exe" -m pip install -r "$here\requirements.txt"
}

& "$here\.venv\Scripts\python.exe" -m streamlit run "$here\app.py"
