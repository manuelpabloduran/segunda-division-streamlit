"""
Archivo de configuración EJEMPLO para el proyecto Opta to WhoScored.
Copiar este archivo como config.py y completar con tus credenciales.

IMPORTANTE: config.py está en .gitignore y NO debe subirse a GitHub.
"""
import os

# ============================================================================
# CONFIGURACIÓN DE LA API DE STATS PERFORM
# ============================================================================
# Obtener credenciales de Streamlit Secrets o variables de entorno
# En Streamlit Cloud: Settings -> Secrets
# En local: Reemplazar los valores o usar variables de entorno

OUTLET_KEY = os.getenv("SDAPI_OUTLET_KEY", "TU_OUTLET_KEY_AQUI")
SECRET_KEY = os.getenv("SDAPI_SECRET_KEY", "TU_SECRET_KEY_AQUI")
SECRET_KEY_BACKUP = "TU_SECRET_KEY_BACKUP_AQUI"  # SK#2 (backup)

# ============================================================================
# URLs DE LA API
# ============================================================================
BASE_URL = "https://api.performfeeds.com"
OAUTH_URL = "https://oauth.performgroup.com/oauth/token"

# ============================================================================
# CONFIGURACIÓN GENERAL
# ============================================================================
SPORT = "soccer"
TIMEOUT = 25
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.5

# ============================================================================
# COMPETICIONES
# ============================================================================
# La Liga Primera División (2026/2027)
LA_LIGA_PRIMERA_DIVISION_COMP_ID = "34pl8szyvrbwcmfkuocjm3r6t"  # Competition ID
LA_LIGA_PRIMERA_DIVISION_TMCL_ID = "830epggffy1nfkfyrtpqdwhlg"  # Tournament Calendar ID (2026/2027)

# Compatibilidad
SEGUNDA_DIVISION_ESPAÑA_COMP_ID = LA_LIGA_PRIMERA_DIVISION_COMP_ID
SEGUNDA_DIVISION_ESPAÑA_TMCL_ID = LA_LIGA_PRIMERA_DIVISION_TMCL_ID
