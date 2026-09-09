"""
Archivo de configuración para el proyecto Opta to WhoScored.
Lee credenciales de Streamlit Secrets o variables de entorno.
"""
import os

# Intentar importar streamlit para usar secrets si está disponible
try:
    import streamlit as st
    # Intentar usar secrets de Streamlit Cloud
    try:
        OUTLET_KEY = st.secrets.get("SDAPI_OUTLET_KEY")
        SECRET_KEY = st.secrets.get("SDAPI_SECRET_KEY")
        SECRET_KEY_BACKUP = st.secrets.get("SDAPI_SECRET_KEY_BACKUP", "")
    except (FileNotFoundError, Exception):
        # Secrets no disponibles, usar env vars
        OUTLET_KEY = os.getenv("SDAPI_OUTLET_KEY")
        SECRET_KEY = os.getenv("SDAPI_SECRET_KEY")
        SECRET_KEY_BACKUP = os.getenv("SDAPI_SECRET_KEY_BACKUP", "")
except ImportError:
    # Streamlit no disponible, usar env vars
    OUTLET_KEY = os.getenv("SDAPI_OUTLET_KEY")
    SECRET_KEY = os.getenv("SDAPI_SECRET_KEY")
    SECRET_KEY_BACKUP = os.getenv("SDAPI_SECRET_KEY_BACKUP", "")

# Validar que las credenciales estén configuradas
if not OUTLET_KEY or not SECRET_KEY:
    raise ValueError(
        "❌ Credenciales de API no configuradas.\n\n"
        "Para Streamlit Cloud: Configura secrets en Settings -> Secrets\n"
        "Para local: Configura variables de entorno SDAPI_OUTLET_KEY y SDAPI_SECRET_KEY"
    )

# URLs de la API
BASE_URL = "https://api.performfeeds.com"
OAUTH_URL = "https://oauth.performgroup.com/oauth/token"

# Configuración general
SPORT = "soccer"
TIMEOUT = 25
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.5

# Competiciones
# La Liga Primera División 2026/2027
LA_LIGA_PRIMERA_DIVISION_COMP_ID = "34pl8szyvrbwcmfkuocjm3r6t"  # Competition ID
LA_LIGA_PRIMERA_DIVISION_TMCL_ID = "830epggffy1nfkfyrtpqdwhlg"  # Tournament Calendar ID (2026/2027)

# Compatibilidad hacia atrás con la versión actual del proyecto
SEGUNDA_DIVISION_ESPAÑA_COMP_ID = LA_LIGA_PRIMERA_DIVISION_COMP_ID
SEGUNDA_DIVISION_ESPAÑA_TMCL_ID = LA_LIGA_PRIMERA_DIVISION_TMCL_ID
