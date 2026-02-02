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

## 📦 Instalación

```bash
# Clonar repositorio
git clone <URL_DEL_REPO>
cd streamlit_partidos

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
# Crear archivo .env con tus credenciales de Stats Perform API
```

### Contenido del archivo `.env`:
```
STATS_PERFORM_USERNAME=tu_usuario
STATS_PERFORM_PASSWORD=tu_password
```

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
