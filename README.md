# ⚽ Segunda División España - Análisis de Datos

Aplicación Streamlit para análisis detallado de estadísticas de la Segunda División de España usando datos de Stats Perform (Opta).

## 🚀 Características

### 📊 Tabla de Clasificación
- Visualización completa de la tabla con: Posición, PJ, G, E, P, GF, GC, DG, Pts, %Pts
- Resultados individuales por equipo con colores (verde: victoria, amarillo: empate, rojo: derrota)
- Auto-actualización de datos cada 24 horas

### 🔍 Filtros Avanzados

#### Filtros de Tipo de Partido
- **Local/Visitante**: Analiza rendimiento como local o visitante
- **TOP N**: Filtra partidos vs equipos en posiciones específicas (ej: TOP 5, posiciones 15-22)
- **Equipos Rivales**: Selecciona equipos específicos para análisis
- **Rango de Fechas**: Filtra por período temporal

#### Filtros Especiales
- **Primer Gol**: Solo partidos donde el equipo marca primero
- **Recibe Primer Gol**: Partidos donde el equipo recibe el primer gol
- **Remontadas**: Partidos donde el equipo empezó perdiendo y terminó empatando o ganando
- **Sin Tarjetas Rojas**: Excluye partidos con expulsiones

### 👥 Análisis por Jugadores
- Filtra rendimiento del equipo según jugadores titulares
- **Incluir jugadores**: Todos deben ser titulares
- **Excluir jugadores**: Ninguno debe ser titular
- **Filtro por Entrenador**: Analiza rendimiento por DT (útil cuando hay cambios de entrenador)
- Métricas completas: Partidos, Puntos, %Pts, GF, GC, DG, Victorias, Empates, Derrotas
- Tabla de resultados con colores

### 🔍 Otras Funcionalidades
- **Listado de Partidos**: Vista detallada con filtros
- **Estadísticas Generales**: Top 5 goleadores, mejores defensas, más victorias, mejor diferencia de goles
- **Botón Borrar Filtros**: Resetea todos los filtros activos

## 📦 Instalación Local

```bash
# Clonar repositorio
git clone <URL_DEL_REPO>
cd streamlit_partidos

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración ejemplo
cp config.example.py config.py

# Editar config.py con tus credenciales de Stats Perform API
# O configurar variables de entorno:
# SDAPI_OUTLET_KEY, SDAPI_SECRET_KEY, SDAPI_SECRET_KEY_BACKUP
```

## 🌐 Despliegue en Streamlit Cloud

### Paso 1: Preparar el Repositorio

1. **Crear repositorio público en GitHub**
   ```bash
   # Asegurarte de que config.py NO esté en el repo (está en .gitignore)
   git add .
   git commit -m "Preparar para despliegue en Streamlit Cloud"
   git push origin main
   ```

2. **Verificar que estos archivos SÍ estén en el repo:**
   - ✅ `config.example.py` (sin credenciales)
   - ✅ `.streamlit/secrets.toml.example` (plantilla)
   - ✅ `.gitignore` (con `config.py` listado)
   - ✅ Todos los demás archivos `.py`

3. **Verificar que estos archivos NO estén:**
   - ❌ `config.py` (contiene credenciales)
   - ❌ `.env` (si existe)
   - ❌ Datos en `match_cache/` y `segunda_division_2025_2026_matches.json`

### Paso 2: Configurar Streamlit Cloud

1. **Ir a [share.streamlit.io](https://share.streamlit.io)**

2. **Conectar tu repositorio de GitHub**
   - Click "New app"
   - Seleccionar tu repositorio
   - Branch: `main` (o `master`)
   - Main file path: `app.py`

3. **Configurar Secrets** (⚠️ IMPORTANTE)
   - Click en "Advanced settings" → "Secrets"
   - Copiar el contenido de `.streamlit/secrets.toml.example`
   - **Reemplazar con tus credenciales reales:**
   ```toml
   SDAPI_OUTLET_KEY = "tu_outlet_key_real"
   SDAPI_SECRET_KEY = "tu_secret_key_real"
   SDAPI_SECRET_KEY_BACKUP = "tu_secret_key_backup_real"
   ```
   - ⚠️ Estas credenciales permanecen privadas en Streamlit Cloud

4. **Deploy!**
   - Click "Deploy"
   - Esperar a que la app se inicie (puede tardar 2-3 minutos)

### Paso 3: Verificación

- ✅ La app carga correctamente
- ✅ Los datos se descargan desde la API
- ✅ Las credenciales NO son visibles en el código público

### 🔒 Seguridad

- ✅ `config.py` está en `.gitignore` y nunca se sube a GitHub
- ✅ Las credenciales solo existen en Streamlit Cloud Secrets
- ✅ El código público usa `config.example.py` como referencia
- ✅ La app lee secrets automáticamente desde `st.secrets`

## 🎮 Uso

```bash
# Ejecutar la aplicación
streamlit run app.py

# O usar el script batch en Windows
run_streamlit.bat
```

La aplicación se abrirá en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
streamlit_partidos/
├── app.py                          # Aplicación principal Streamlit
├── config.py                       # Configuración de API y competición
├── data_processing.py              # Procesamiento de datos y estadísticas
├── stats_perform_client.py         # Cliente para API de Stats Perform
├── download_all_matches.py         # Script para descargar partidos
├── update_utils.py                 # Utilidades de actualización automática
├── requirements.txt                # Dependencias Python
├── run_streamlit.bat              # Script de ejecución Windows
├── .env                           # Variables de entorno (no incluido)
└── .gitignore                     # Archivos ignorados por Git
```

## 🔧 Tecnologías

- **Streamlit**: Framework de UI
- **Pandas**: Procesamiento de datos
- **Plotly**: Visualizaciones (preparado para uso futuro)
- **Stats Perform (Opta) API**: Fuente de datos oficial

## 📊 Datos

Los datos se obtienen de la API oficial de Stats Perform (Opta) y se actualizan automáticamente cada 24 horas. La aplicación descarga:
- Partidos jugados de la Segunda División España
- Estadísticas completas de cada partido
- Alineaciones y datos de jugadores
- Eventos del partido (goles, tarjetas, etc.)

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es privado y está destinado para uso personal.

## 👨‍💻 Autor

Manuel Duran

---

**Nota**: Se requieren credenciales válidas de Stats Perform API para usar esta aplicación.
