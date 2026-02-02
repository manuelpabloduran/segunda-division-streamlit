"""
Archivo de configuración para el proyecto Opta to WhoScored.
Lee credenciales de Streamlit Secrets o variables de entorno.
"""
import os

# Intentar importar streamlit para usar secrets si está disponible
try:
    import streamlit as st
    # Si estamos en Streamlit Cloud, usar secrets
    if hasattr(st, 'secrets') and len(st.secrets) > 0:
        OUTLET_KEY = st.secrets.get("SDAPI_OUTLET_KEY")
        SECRET_KEY = st.secrets.get("SDAPI_SECRET_KEY")
        SECRET_KEY_BACKUP = st.secrets.get("SDAPI_SECRET_KEY_BACKUP", "")
    else:
        # Streamlit importado pero sin secrets, usar env vars
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
SEGUNDA_DIVISION_ESPAÑA_COMP_ID = "3is4bkgf3loxv9qfg3hm8zfqb"  # Competition ID
SEGUNDA_DIVISION_ESPAÑA_TMCL_ID = "dko0hzifl1xv9c51s3ai017v8"  # Tournament Calendar ID (2025/2026)
