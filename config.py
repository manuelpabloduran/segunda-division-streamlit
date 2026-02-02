"""
Archivo de configuración para el proyecto Opta to WhoScored.
"""
import os

# Configuración de la API de Stats Perform
OUTLET_KEY = os.getenv("SDAPI_OUTLET_KEY", "czumn6sja9291tylsewlnuyl0")
SECRET_KEY = os.getenv("SDAPI_SECRET_KEY", "jol3ie4f5ies1kcxo2q9xro3g")  # SK#1
SECRET_KEY_BACKUP = "jhiwomwenwi21k1k6nji36ine"  # SK#2 (backup)

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
