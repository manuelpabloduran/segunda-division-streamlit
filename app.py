"""
Streamlit App - Tabla de Clasificación Segunda División España
Con actualización automática de datos desde API de Opta
"""
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from pathlib import Path
from update_utils import (
    get_last_update_info,
    format_last_update_message,
    auto_update_if_needed
)
from data_processing import (
    build_standings_table,
    get_match_details_list,
    get_global_stats,
    get_all_players_for_team,
    get_all_managers_for_team,
    calculate_team_stats_with_players,
    get_filtered_matches_by_players,
    get_minutes_played_by_player,
    calculate_competitiveness_index,
    extract_match_result,
    match_has_red_cards
)

# Configuración de la página
st.set_page_config(
    page_title="Segunda División - Tabla de Clasificación",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("⚽ Segunda División España 2025/2026")
st.markdown("### Tabla de Clasificación y Estadísticas")

# Auto-actualización al cargar la app (silenciosa)
@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_and_update_data():
    """
    Carga datos y actualiza automáticamente si es necesario.
    Se cachea por 1 hora para no hacer requests constantes.
    """
    # Intentar actualización automática (solo si pasaron >24h)
    auto_update_if_needed(max_hours=24, verbose=False)
    
    # Cargar datos
    data_file = Path("segunda_division_2025_2026_matches.json")
    if not data_file.exists():
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


# Cargar datos primero
data = load_and_update_data()

if data is None:
    st.error("⚠️ No hay datos disponibles. Ejecuta el script de descarga primero.")
    st.code("python download_all_matches.py", language="bash")
    st.stop()

# Sidebar - Controles y actualización
with st.sidebar:
    st.header("🔧 Configuración")
    
    # Información de última actualización
    info = get_last_update_info()
    st.info(format_last_update_message(info))
    
    # Botón de actualización manual
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Actualizar", use_container_width=True):
            with st.spinner("Actualizando datos..."):
                result = auto_update_if_needed(force=True, verbose=False)
                
                if result['updated']:
                    st.success(f"✅ {result['newMatches']} partidos nuevos descargados")
                    st.rerun()
                else:
                    if result['reason'] == 'no_new_matches':
                        st.info("✅ No hay partidos nuevos")
                    else:
                        st.warning("⚠️ No se pudo actualizar")
    
    with col2:
        if st.button("ℹ️ Info", use_container_width=True):
            st.session_state['show_info'] = not st.session_state.get('show_info', False)
    
    # Mostrar información detallada si se solicitó
    if st.session_state.get('show_info', False):
        with st.expander("📊 Detalles de datos", expanded=True):
            if info.get('exists'):
                st.metric("Total de partidos", info.get('totalMatches', 0))
                if info.get('lastUpdate'):
                    st.write(f"**Última actualización:**")
                    st.write(info['lastUpdate'].strftime("%d/%m/%Y %H:%M"))
                    st.write(f"Hace {info.get('hoursAgo', 0):.1f} horas")
    
    st.divider()
    
    # Filtros de visualización
    st.header("🎯 Filtros")
    
    # Filtro de tipo de partidos
    match_type = st.radio(
        "Tipo de partidos",
        ["Todos", "Local", "Visitante"],
        horizontal=True,
        help="Filtra por partidos como local, visitante, o todos"
    )
    
    # Filtro de TOP N equipos
    st.subheader("🏆 Filtro vs Rango de Posiciones")
    use_top_n = st.checkbox("Filtrar por rango de posiciones")
    
    top_n_range = None
    if use_top_n:
        col1, col2 = st.columns(2)
        with col1:
            min_pos = st.number_input("Desde posición", min_value=1, max_value=22, value=1, step=1)
        with col2:
            max_pos = st.number_input("Hasta posición", min_value=1, max_value=22, value=5, step=1)
        
        if min_pos > max_pos:
            st.error("⚠️ La posición inicial debe ser menor o igual a la final")
            top_n_range = None
        else:
            top_n_range = (min_pos, max_pos)
            st.caption(f"Analizando partidos contra equipos en posiciones {min_pos} a {max_pos}")
    
    # Filtro de rango de fechas
    st.subheader("📅 Filtro por Fechas")
    use_date_filter = st.checkbox("Filtrar por rango de fechas")
    
    date_range = None
    if use_date_filter:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Fecha inicio", value=pd.to_datetime("2025-08-01").date())
        with col2:
            end_date = st.date_input("Fecha fin", value=pd.to_datetime("2026-02-02").date())
        
        if start_date > end_date:
            st.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin")
            date_range = None
        else:
            date_range = (start_date, end_date)
            st.caption(f"Analizando partidos desde {start_date.strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}")
    
    # Filtro de equipos rivales específicos
    st.subheader("⚽ Filtro por Equipos Rivales")
    use_team_filter = st.checkbox("Filtrar por equipos rivales específicos")
    
    selected_rival_teams = None
    if use_team_filter:
        # Obtener lista de todos los equipos
        temp_standings = build_standings_table(data, match_type='Todos')
        all_teams = sorted(temp_standings['Equipo'].tolist()) if not temp_standings.empty else []
        
        selected_rival_teams = st.multiselect(
            "Selecciona equipos rivales",
            options=all_teams,
            help="La tabla mostrará cómo le fue a cada equipo contra los rivales seleccionados"
        )
        
        if selected_rival_teams:
            st.caption(f"Analizando partidos contra: {', '.join(selected_rival_teams[:3])}{'...' if len(selected_rival_teams) > 3 else ''} ({len(selected_rival_teams)} equipos)")
    
    # Filtros avanzados
    st.subheader("🔬 Filtros Avanzados")
    use_advanced = st.checkbox("Activar filtros avanzados de goles")
    
    advanced_filters = None
    if use_advanced:
        scored_first = st.checkbox("Solo partidos donde el equipo hace el primer gol", key="scored_first")
        conceded_first = st.checkbox("Solo partidos donde el equipo recibe el primer gol", key="conceded_first")
        comeback = st.checkbox("Solo partidos dando vuelta el resultado", key="comeback", help="Partidos donde empezó perdiendo y terminó empatando o ganando")
        no_red_cards = st.checkbox("Solo partidos sin tarjetas rojas", key="no_red_cards", help="Excluye partidos donde hubo expulsiones")
        
        if scored_first or conceded_first or comeback or no_red_cards:
            advanced_filters = {
                'scored_first': scored_first,
                'conceded_first': conceded_first,
                'comeback': comeback,
                'no_red_cards': no_red_cards
            }
            
            filters_active = []
            if scored_first:
                filters_active.append("Hace 1er gol")
            if conceded_first:
                filters_active.append("Recibe 1er gol")
            if comeback:
                filters_active.append("Remontadas")
            if no_red_cards:
                filters_active.append("Sin rojas")
            
            st.caption(f"Filtros activos: {', '.join(filters_active)}")
    
    st.divider()
    
    # Botón para borrar todos los filtros
    if st.button("🗑️ Borrar todos los filtros", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# Procesar datos con filtros
standings = build_standings_table(data, match_type=match_type, top_n_range=top_n_range, date_range=date_range, rival_teams=selected_rival_teams, advanced_filters=advanced_filters)
matches_list = get_match_details_list(data)
global_stats = get_global_stats(standings)

# Obtener equipos en el rango para mostrar información
filtered_team_names = None
if top_n_range:
    full_standings = build_standings_table(data, match_type='Todos')
    min_pos, max_pos = top_n_range
    filtered_team_names = full_standings[(full_standings['Pos'] >= min_pos) & (full_standings['Pos'] <= max_pos)]['Equipo'].tolist()

# Mostrar metadata
metadata = data.get('metadata', {})
matches = data.get('matches', [])

# Métricas principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Partidos Jugados", global_stats['total_matches'])

with col2:
    st.metric("Equipos", global_stats['total_teams'])

with col3:
    st.metric("Goles Totales", global_stats['total_goals'])

with col4:
    st.metric("Líder", global_stats['leader'], f"{global_stats['leader_points']} pts")

st.divider()

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(["📊 Tabla de Clasificación", "🔍 Listado de Partidos", "📈 Estadísticas", "👥 Análisis Equipo"])

with tab1:
    st.subheader("Tabla de Clasificación - Segunda División")
    
    # Mostrar información de filtros aplicados
    if filtered_team_names:
        min_pos, max_pos = top_n_range
        st.info(f"🎯 **Filtro activo:** Solo partidos vs equipos en posiciones {min_pos} a {max_pos}")
        with st.expander(f"Ver {len(filtered_team_names)} equipos considerados"):
            for i, team in enumerate(filtered_team_names, min_pos):
                st.write(f"{i}. {team}")
    
    if standings.empty:
        st.warning("No hay datos de clasificación disponibles")
    else:
        # Selector de equipo para ver detalles
        st.markdown("**💡 Selecciona un equipo para ver sus resultados:**")
        selected_team = st.selectbox(
            "Equipo",
            options=["Ninguno"] + standings['Equipo'].tolist(),
            label_visibility="collapsed"
        )
        
        # Mostrar tabla
        st.dataframe(
            standings,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pos": st.column_config.NumberColumn("Pos", width="small"),
                "Equipo": st.column_config.TextColumn("Equipo", width="large"),
                "PJ": st.column_config.NumberColumn("PJ", help="Partidos Jugados"),
                "G": st.column_config.NumberColumn("G", help="Ganados"),
                "E": st.column_config.NumberColumn("E", help="Empatados"),
                "P": st.column_config.NumberColumn("P", help="Perdidos"),
                "GF": st.column_config.NumberColumn("GF", help="Goles a Favor"),
                "GC": st.column_config.NumberColumn("GC", help="Goles en Contra"),
                "DG": st.column_config.NumberColumn("DG", help="Diferencia de Goles"),
                "Pts": st.column_config.NumberColumn(
                    "Pts",
                    help="Puntos",
                    width="medium"
                ),
                "%Pts": st.column_config.NumberColumn(
                    "%Pts",
                    help="Porcentaje de puntos obtenidos",
                    format="%.1f%%",
                    width="small"
                )
            }
        )
        
        # Mostrar resultados del equipo seleccionado
        if selected_team != "Ninguno":
            st.divider()
            st.subheader(f"📋 Resultados de {selected_team}")
            
            # Filtrar partidos del equipo según los filtros aplicados
            team_matches = matches_list[
                (matches_list['Local'] == selected_team) | 
                (matches_list['Visitante'] == selected_team)
            ].copy()
            
            # Aplicar filtro de tipo de partido
            if match_type == 'Local':
                team_matches = team_matches[team_matches['Local'] == selected_team]
            elif match_type == 'Visitante':
                team_matches = team_matches[team_matches['Visitante'] == selected_team]
            
            # Aplicar filtro de TOP N si está activo
            if filtered_team_names:
                def match_in_filter(row):
                    # Determinar quién es el rival del equipo seleccionado
                    rival = row['Visitante'] if row['Local'] == selected_team else row['Local']
                    
                    if match_type == 'Local':
                        # El equipo seleccionado juega de local, verificar que el visitante esté en el filtro
                        return row['Visitante'] in filtered_team_names
                    elif match_type == 'Visitante':
                        # El equipo seleccionado juega de visitante, verificar que el local esté en el filtro
                        return row['Local'] in filtered_team_names
                    else:  # 'Todos'
                        # Verificar que el rival esté en el filtro (excluyendo al equipo seleccionado)
                        return rival in filtered_team_names and rival != selected_team
                
                team_matches = team_matches[team_matches.apply(match_in_filter, axis=1)]
            
            # Aplicar filtro de equipos rivales específicos si está activo
            if selected_rival_teams:
                def match_in_rival_filter(row):
                    # Determinar quién es el rival del equipo seleccionado
                    rival = row['Visitante'] if row['Local'] == selected_team else row['Local']
                    
                    if match_type == 'Local':
                        # El equipo seleccionado juega de local, verificar que el visitante esté en el filtro
                        return row['Visitante'] in selected_rival_teams
                    elif match_type == 'Visitante':
                        # El equipo seleccionado juega de visitante, verificar que el local esté en el filtro
                        return row['Local'] in selected_rival_teams
                    else:  # 'Todos'
                        # Verificar que el rival esté en el filtro (excluyendo al equipo seleccionado)
                        return rival in selected_rival_teams and rival != selected_team
                
                team_matches = team_matches[team_matches.apply(match_in_rival_filter, axis=1)]
            
            # Aplicar filtro de fechas si está activo
            if date_range:
                start_date, end_date = date_range
                team_matches = team_matches[
                    (team_matches['Fecha'] >= pd.to_datetime(start_date)) & 
                    (team_matches['Fecha'] <= pd.to_datetime(end_date))
                ]
            
            # Aplicar filtros avanzados si están activos
            if advanced_filters:
                from data_processing import analyze_match_goals
                
                def passes_advanced_filters(row):
                    # Buscar el partido en los datos originales
                    current_match = None
                    for match in data.get('matches', []):
                        if 'matchInfo' not in match:
                            continue
                        match_info = match['matchInfo']
                        contestants = match_info.get('contestant', [])
                        if not isinstance(contestants, list):
                            contestants = [contestants]
                        
                        home = None
                        away = None
                        for c in contestants:
                            if c.get('position') == 'home':
                                home = c.get('name')
                            elif c.get('position') == 'away':
                                away = c.get('name')
                        
                        if home == row['Local'] and away == row['Visitante']:
                            current_match = match
                            break
                    
                    if not current_match:
                        return False
                    
                    # Aplicar filtro de tarjetas rojas
                    if advanced_filters.get('no_red_cards'):
                        if match_has_red_cards(current_match):
                            return False
                    
                    # Reconstruir el match_result para análisis de goles
                    match_result = {
                        'home_team': row['Local'],
                        'away_team': row['Visitante'],
                        'home_id': None,
                        'away_id': None,
                        'winner': 'home' if row['GF_Local'] > row['GF_Visitante'] else ('away' if row['GF_Local'] < row['GF_Visitante'] else 'draw'),
                        'goals': current_match.get('liveData', {}).get('goal', [])
                    }
                    
                    contestants = current_match['matchInfo'].get('contestant', [])
                    if not isinstance(contestants, list):
                        contestants = [contestants]
                    match_result['home_id'] = next((c.get('id') for c in contestants if c.get('position') == 'home'), None)
                    match_result['away_id'] = next((c.get('id') for c in contestants if c.get('position') == 'away'), None)
                    
                    goal_analysis = analyze_match_goals(match_result, selected_team)
                    
                    if advanced_filters.get('scored_first') and not goal_analysis['scored_first']:
                        return False
                    if advanced_filters.get('conceded_first') and not goal_analysis['conceded_first']:
                        return False
                    if advanced_filters.get('comeback') and not goal_analysis['comeback']:
                        return False
                    
                    return True
                
                team_matches = team_matches[team_matches.apply(passes_advanced_filters, axis=1)]
            
            if team_matches.empty:
                st.warning(f"No hay partidos para {selected_team} con los filtros aplicados")
            else:
                st.write(f"**Total de partidos: {len(team_matches)}**")
                
                # Preparar datos para mostrar
                display_matches = team_matches[['Fecha', 'Local', 'Resultado', 'Visitante', 'GF_Local', 'GF_Visitante']].copy()
                # Convertir fecha manejando valores nulos
                display_matches['Fecha'] = display_matches['Fecha'].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else 'N/A'
                )
                
                # Determinar resultado para el equipo seleccionado (G/E/P)
                def get_team_result(row):
                    if row['Local'] == selected_team:
                        if row['GF_Local'] > row['GF_Visitante']:
                            return 'G'
                        elif row['GF_Local'] < row['GF_Visitante']:
                            return 'P'
                        else:
                            return 'E'
                    else:  # Visitante
                        if row['GF_Visitante'] > row['GF_Local']:
                            return 'G'
                        elif row['GF_Visitante'] < row['GF_Local']:
                            return 'P'
                        else:
                            return 'E'
                
                display_matches['Result'] = display_matches.apply(get_team_result, axis=1)
                
                # Aplicar estilos con colores transparentes
                def highlight_result(row):
                    if row['Result'] == 'G':
                        color = 'background-color: rgba(0, 255, 0, 0.15)'  # Verde transparente
                    elif row['Result'] == 'P':
                        color = 'background-color: rgba(255, 0, 0, 0.15)'  # Rojo transparente
                    else:  # Empate
                        color = 'background-color: rgba(255, 255, 0, 0.15)'  # Amarillo transparente
                    return [color] * len(row)
                
                # Aplicar estilo al DataFrame completo y luego mostrar solo las columnas deseadas
                styled_df = display_matches.style.apply(highlight_result, axis=1)
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Fecha": st.column_config.TextColumn("Fecha", width="small"),
                        "Local": st.column_config.TextColumn("Local", width="medium"),
                        "Resultado": st.column_config.TextColumn("Resultado", width="small"),
                        "Visitante": st.column_config.TextColumn("Visitante", width="medium"),
                        "GF_Local": None,  # Ocultar columna
                        "GF_Visitante": None,  # Ocultar columna
                        "Result": None  # Ocultar columna
                    }
                )
        
        # Información adicional
        st.caption(f"📅 Datos actualizados hasta: {metadata.get('filterDate', 'N/A')}")
        st.caption(f"⚽ Promedio de goles por partido: {global_stats['avg_goals_per_match']:.2f}")
        
        # Botón para descargar tabla como CSV
        csv = standings.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar tabla (CSV)",
            data=csv,
            file_name="segunda_division_clasificacion.csv",
            mime="text/csv"
        )

with tab2:
    st.subheader("Listado de Partidos")
    
    if matches_list.empty:
        st.warning("No hay partidos disponibles")
    else:
        # Filtros
        col1, col2 = st.columns(2)
        
        date_range = None
        
        with col1:
            teams = sorted(list(set(matches_list['Local'].tolist() + matches_list['Visitante'].tolist())))
            selected_team = st.selectbox("Filtrar por equipo", ["Todos"] + teams)
        
        with col2:
            # Filtro de rango de fechas
            if not matches_list['Fecha'].isna().all():
                min_date = matches_list['Fecha'].min().date()
                max_date = matches_list['Fecha'].max().date()
                
                date_range = st.date_input(
                    "Rango de fechas",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
        
        # Aplicar filtros
        filtered_matches = matches_list.copy()
        
        if selected_team != "Todos":
            filtered_matches = filtered_matches[
                (filtered_matches['Local'] == selected_team) | 
                (filtered_matches['Visitante'] == selected_team)
            ]
        
        if date_range and len(date_range) == 2:
            filtered_matches = filtered_matches[
                (filtered_matches['Fecha'].dt.date >= date_range[0]) &
                (filtered_matches['Fecha'].dt.date <= date_range[1])
            ]
        
        # Mostrar total de partidos
        st.write(f"**Mostrando {len(filtered_matches)} partidos**")
        
        # Mostrar tabla de partidos
        display_df = filtered_matches[['Fecha', 'Local', 'Resultado', 'Visitante']].copy()
        display_df['Fecha'] = display_df['Fecha'].dt.strftime('%d/%m/%Y')
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fecha": st.column_config.TextColumn("Fecha", width="small"),
                "Local": st.column_config.TextColumn("Local", width="medium"),
                "Resultado": st.column_config.TextColumn("Resultado", width="small"),
                "Visitante": st.column_config.TextColumn("Visitante", width="medium")
            }
        )

with tab3:
    st.subheader("Estadísticas de la Liga")
    
    if not standings.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🔝 Top 5 Goleadores (Equipos)**")
            top_scorers = standings.nlargest(5, 'GF')[['Equipo', 'GF']]
            st.dataframe(top_scorers, hide_index=True, use_container_width=True)
            
            st.write("**🛡️ Top 5 Mejores Defensas**")
            best_defense = standings.nsmallest(5, 'GC')[['Equipo', 'GC']]
            st.dataframe(best_defense, hide_index=True, use_container_width=True)
        
        with col2:
            st.write("**📈 Mayor Diferencia de Goles**")
            best_diff = standings.nlargest(5, 'DG')[['Equipo', 'DG']]
            st.dataframe(best_diff, hide_index=True, use_container_width=True)
            
            st.write("**🎯 Más Victorias**")
            most_wins = standings.nlargest(5, 'G')[['Equipo', 'G']]
            st.dataframe(most_wins, hide_index=True, use_container_width=True)
    else:
        st.warning("No hay datos de estadísticas disponibles")

with tab4:
    st.subheader("Análisis por Jugadores")
    
    if not standings.empty:
        # Selector de equipo
        selected_team_analysis = st.selectbox(
            "Selecciona un equipo:",
            standings['Equipo'].tolist(),
            key="team_analysis"
        )
        
        # Obtener todos los jugadores del equipo
        all_players = get_all_players_for_team(data, selected_team_analysis)
        
        # Obtener todos los entrenadores del equipo
        all_managers = get_all_managers_for_team(data, selected_team_analysis)
        
        if all_players:
            col1, col2 = st.columns(2)
            
            with col1:
                include_players = st.multiselect(
                    "Jugadores a incluir (todos deben ser titulares):",
                    all_players,
                    key="include_players"
                )
            
            with col2:
                exclude_players = st.multiselect(
                    "Jugadores a excluir (no deben ser titulares):",
                    all_players,
                    key="exclude_players"
                )
            
            # Selector de entrenador (si hay más de uno)
            selected_manager = None
            if len(all_managers) > 1:
                st.write("**Filtrar por entrenador:**")
                manager_options = ["Todos"] + all_managers
                selected_manager_option = st.selectbox(
                    "Entrenador:",
                    manager_options,
                    key="manager_filter"
                )
                if selected_manager_option != "Todos":
                    selected_manager = selected_manager_option
            elif len(all_managers) == 1:
                st.info(f"ℹ️ Entrenador: {all_managers[0]}")
            
            # Filtro de rango de fechas
            st.write("**Filtrar por rango de fechas:**")
            
            # Obtener fechas de partidos del equipo
            team_matches = []
            for match in data['matches']:
                result = extract_match_result(match)
                if result and (result['home_team'] == selected_team_analysis or result['away_team'] == selected_team_analysis):
                    try:
                        # Intentar parsear la fecha, manejando diferentes formatos
                        date_str = result['date']
                        if date_str:
                            # Limpiar la fecha si tiene Z o timezone
                            date_str = str(date_str).replace('Z', '').split('T')[0]
                            parsed_date = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')
                            if pd.notna(parsed_date):
                                team_matches.append(parsed_date)
                    except:
                        continue
            
            if team_matches:
                min_date = min(team_matches).date()
                max_date = max(team_matches).date()
                
                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input(
                        "Desde:",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="start_date_analysis"
                    )
                with col_date2:
                    end_date = st.date_input(
                        "Hasta:",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="end_date_analysis"
                    )
                
                # Convertir a datetime para comparación
                date_range = (pd.to_datetime(start_date), pd.to_datetime(end_date))
            else:
                date_range = None
            
            # Validar que no haya jugadores en ambas listas
            if include_players and exclude_players:
                overlap = set(include_players) & set(exclude_players)
                if overlap:
                    st.error(f"⚠️ Los siguientes jugadores están en ambas listas: {', '.join(overlap)}")
                    st.stop()
            
            # Calcular estadísticas
            stats = calculate_team_stats_with_players(
                data, 
                selected_team_analysis, 
                include_players if include_players else None,
                exclude_players if exclude_players else None,
                selected_manager,
                match_type,
                filtered_team_names,  # top_n_teams ya calculado
                date_range,
                selected_rival_teams,
                advanced_filters
            )
            
            # Mostrar estadísticas
            st.divider()
            
            if stats['total_matches'] > 0:
                # Título con información de filtros
                filter_info = []
                if include_players:
                    filter_info.append(f"Con: {', '.join(include_players)}")
                if exclude_players:
                    filter_info.append(f"Sin: {', '.join(exclude_players)}")
                if selected_manager:
                    filter_info.append(f"DT: {selected_manager}")
                
                if filter_info:
                    st.write(f"**Rendimiento {' | '.join(filter_info)}**")
                else:
                    st.write(f"**Rendimiento general de {selected_team_analysis}**")
                
                # Métricas principales
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Partidos", stats['total_matches'])
                
                with col2:
                    st.metric("Puntos", stats['total_points'])
                
                with col3:
                    st.metric("% Pts", f"{stats['points_percentage']:.1f}%")
                
                with col4:
                    st.metric("DG", f"{stats['goal_difference']:+d}")
                
                # Métricas secundarias
                col5, col6, col7 = st.columns(3)
                
                with col5:
                    st.metric("GF", stats['goals_for'])
                
                with col6:
                    st.metric("GC", stats['goals_against'])
                
                with col7:
                    avg_goals = stats['goals_for'] / stats['total_matches']
                    st.metric("GF/Partido", f"{avg_goals:.2f}")
                
                # Desglose de resultados
                st.divider()
                st.write("**Desglose de resultados**")
                
                col8, col9, col10 = st.columns(3)
                
                with col8:
                    st.metric("Victorias", stats['wins'], delta=None)
                
                with col9:
                    st.metric("Empates", stats['draws'], delta=None)
                
                with col10:
                    st.metric("Derrotas", stats['losses'], delta=None)
                
                # Gráfico de minutos jugados por jugador
                st.divider()
                st.write("**⏱️ Minutos Jugados por Jugador**")
                
                player_minutes = get_minutes_played_by_player(
                    data,
                    selected_team_analysis,
                    include_players if include_players else None,
                    exclude_players if exclude_players else None,
                    selected_manager,
                    date_range if date_range else None,
                    match_type,
                    filtered_team_names,
                    selected_rival_teams,
                    advanced_filters
                )
                
                if player_minutes:
                    # Convertir a DataFrame y ordenar de mayor a menor
                    minutes_df = pd.DataFrame([
                        {'Jugador': player, 'Minutos': minutes}
                        for player, minutes in player_minutes.items()
                        if minutes > 0  # Solo mostrar jugadores con minutos
                    ])
                    
                    if not minutes_df.empty:
                        minutes_df = minutes_df.sort_values('Minutos', ascending=True)  # Ascendente para barras horizontales
                        
                        # Crear gráfico de barras horizontales
                        fig = px.bar(
                            minutes_df,
                            x='Minutos',
                            y='Jugador',
                            orientation='h',
                            text='Minutos',
                            title=None
                        )
                        
                        # Personalizar el gráfico
                        fig.update_traces(
                            texttemplate='%{text}',
                            textposition='outside',
                            marker_color='#1f77b4'
                        )
                        
                        fig.update_layout(
                            height=max(400, len(minutes_df) * 25),  # Altura dinámica según número de jugadores
                            xaxis_title='Minutos Totales',
                            yaxis_title=None,
                            showlegend=False,
                            margin=dict(l=10, r=10, t=10, b=40)
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No hay datos de minutos jugados disponibles")
                else:
                    st.info("No hay datos de minutos jugados disponibles")
                
                # Gráfico de índice de competitividad
                st.divider()
                st.write("**📊 Índice de Competitividad vs Diferencia de Gol**")
                
                competitiveness_df = calculate_competitiveness_index(
                    data,
                    selected_team_analysis,
                    include_players if include_players else None,
                    exclude_players if exclude_players else None,
                    selected_manager,
                    date_range if date_range else None,
                    match_type,
                    filtered_team_names,
                    selected_rival_teams,
                    advanced_filters
                )
                
                if not competitiveness_df.empty and len(competitiveness_df) > 0:
                    # Filtrar jugadores con pocos minutos (menos del 5% del total)
                    competitiveness_df = competitiveness_df[competitiveness_df['pct_minutes_played'] >= 0.05].copy()
                    
                    if not competitiveness_df.empty:
                        # Selectores de variables para el gráfico
                        st.write("**Seleccionar variables para el gráfico:**")
                        col_x, col_y = st.columns(2)
                        
                        # Opciones disponibles - solo incluir las que existen en el DataFrame
                        all_metric_options = {
                            'avg_indice_competitividad': 'Índice Promedio (General)',
                            'sum_played_gd': 'Diferencia de Gol en Campo',
                            'indice_titular': 'Índice como Titular',
                            'indice_suplente_ganando': 'Índice Suplente (Ganando)',
                            'indice_suplente_empatando': 'Índice Suplente (Empatando)',
                            'indice_suplente_perdiendo': 'Índice Suplente (Perdiendo)',
                            'sum_diff_points': 'Diferencia de Puntos',
                            'total_minutes_played': 'Minutos Totales'
                        }
                        
                        # Filtrar solo métricas que existen en el DataFrame
                        metric_options = {k: v for k, v in all_metric_options.items() if k in competitiveness_df.columns}
                        available_metrics = list(metric_options.keys())
                        
                        # Determinar índices default (si existen)
                        default_x = 0 if 'avg_indice_competitividad' in available_metrics else 0
                        default_y = available_metrics.index('sum_played_gd') if 'sum_played_gd' in available_metrics else (1 if len(available_metrics) > 1 else 0)
                        
                        with col_x:
                            x_metric = st.selectbox(
                                "Eje X:",
                                options=available_metrics,
                                index=default_x,
                                format_func=lambda x: metric_options[x],
                                key="x_metric_selector"
                            )
                        
                        with col_y:
                            y_metric = st.selectbox(
                                "Eje Y:",
                                options=available_metrics,
                                index=default_y,
                                format_func=lambda x: metric_options[x],
                                key="y_metric_selector"
                            )
                        
                        # Determinar columna de tamaño según métrica seleccionada
                        size_metric = 'pct_minutes_played'  # Default
                        if 'titular' in x_metric or 'titular' in y_metric:
                            if 'minutes_titular' in competitiveness_df.columns:
                                size_metric = 'minutes_titular'
                        elif 'suplente_ganando' in x_metric or 'suplente_ganando' in y_metric:
                            if 'minutes_suplente_ganando' in competitiveness_df.columns:
                                size_metric = 'minutes_suplente_ganando'
                        elif 'suplente_empatando' in x_metric or 'suplente_empatando' in y_metric:
                            if 'minutes_suplente_empatando' in competitiveness_df.columns:
                                size_metric = 'minutes_suplente_empatando'
                        elif 'suplente_perdiendo' in x_metric or 'suplente_perdiendo' in y_metric:
                            if 'minutes_suplente_perdiendo' in competitiveness_df.columns:
                                size_metric = 'minutes_suplente_perdiendo'
                        
                        # Filtrar filas con datos válidos en ambas métricas
                        # Verificar que ambas columnas existan antes de filtrar
                        if x_metric in competitiveness_df.columns and y_metric in competitiveness_df.columns:
                            valid_data = competitiveness_df[
                                competitiveness_df[x_metric].notna() & 
                                competitiveness_df[y_metric].notna()
                            ].copy()
                        else:
                            valid_data = competitiveness_df.copy()

                        
                        if not valid_data.empty:
                            # Determinar métrica de color (usar % minutos o minutos específicos si existen)
                            color_metric = size_metric if size_metric in valid_data.columns else 'pct_minutes_played'
                            
                            # Crear gráfico scatter con gradient de color
                            fig_comp = px.scatter(
                                valid_data,
                                x=x_metric,
                                y=y_metric,
                                size=size_metric if size_metric in valid_data.columns else 'pct_minutes_played',
                                color=color_metric,
                                text='player_name',
                                title=None,
                                labels=metric_options,
                                color_continuous_scale='Viridis'
                            )
                            
                            # Líneas de referencia en promedios
                            x_mean = valid_data[x_metric].mean()
                            y_mean = valid_data[y_metric].mean()
                            
                            fig_comp.add_hline(y=y_mean, line_dash="dash", line_color="gray", opacity=0.5)
                            fig_comp.add_vline(x=x_mean, line_dash="dash", line_color="gray", opacity=0.5)
                            
                            # Calcular sizeref dinámico basado en los valores reales
                            size_col = size_metric if size_metric in valid_data.columns else 'pct_minutes_played'
                            max_size = valid_data[size_col].max()
                            sizeref_value = max_size / 50 if max_size > 0 else 2
                            
                            # Personalizar apariencia
                            fig_comp.update_traces(
                                textposition='top center',
                                marker=dict(
                                    sizemode='diameter',
                                    sizeref=sizeref_value,
                                    line=dict(width=1, color='white')
                                )
                            )
                            
                            fig_comp.update_layout(
                                height=600,
                                showlegend=False,
                                xaxis_title=metric_options[x_metric],
                                yaxis_title=metric_options[y_metric],
                                margin=dict(l=10, r=10, t=30, b=10)
                            )
                            
                            st.plotly_chart(fig_comp, use_container_width=True)
                        else:
                            st.info("No hay datos suficientes para mostrar el gráfico con las métricas seleccionadas")
                        
                        # Mostrar tabla de datos
                        with st.expander("📋 Ver datos detallados"):
                            # Preparar columnas para mostrar
                            display_cols = ['player_name', 'avg_indice_competitividad', 'sum_played_gd', 'sum_diff_points', 
                                          'indice_titular', 'indice_suplente_ganando', 'indice_suplente_empatando', 
                                          'indice_suplente_perdiendo', 'total_minutes_played', 'pct_minutes_played', 'n_games']
                            
                            # Filtrar solo columnas que existen
                            available_cols = [col for col in display_cols if col in competitiveness_df.columns]
                            display_df = competitiveness_df[available_cols].copy()
                            
                            # Renombrar columnas
                            col_names = {
                                'player_name': 'Jugador',
                                'avg_indice_competitividad': 'Índice Promedio',
                                'sum_played_gd': 'DG en Campo',
                                'sum_diff_points': 'Dif. Puntos',
                                'indice_titular': 'Índice Titular',
                                'indice_suplente_ganando': 'Índice Supl. Ganando',
                                'indice_suplente_empatando': 'Índice Supl. Empatando',
                                'indice_suplente_perdiendo': 'Índice Supl. Perdiendo',
                                'total_minutes_played': 'Minutos',
                                'pct_minutes_played': '% Minutos',
                                'n_games': 'Partidos'
                            }
                            display_df = display_df.rename(columns={k: v for k, v in col_names.items() if k in display_df.columns})
                            display_df = display_df.sort_values('Índice Promedio', ascending=False)
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay suficientes datos (se requiere al menos 5% de minutos jugados)")
                else:
                    st.info("No hay datos de índice de competitividad disponibles")
                
                # Tabla de partidos
                st.divider()
                st.write("**📋 Partidos**")
                
                filtered_matches = get_filtered_matches_by_players(
                    data,
                    selected_team_analysis,
                    include_players if include_players else None,
                    exclude_players if exclude_players else None,
                    selected_manager,
                    match_type,
                    filtered_team_names,
                    date_range,
                    selected_rival_teams,
                    advanced_filters
                )
                
                if not filtered_matches.empty:
                    # Calcular resultado para el equipo
                    def get_team_result(row):
                        if row['Local'] == selected_team_analysis:
                            if row['GF_Local'] > row['GF_Visitante']:
                                return 'G'
                            elif row['GF_Local'] < row['GF_Visitante']:
                                return 'P'
                            else:
                                return 'E'
                        else:  # Visitante
                            if row['GF_Visitante'] > row['GF_Local']:
                                return 'G'
                            elif row['GF_Visitante'] < row['GF_Local']:
                                return 'P'
                            else:
                                return 'E'
                    
                    filtered_matches['Result'] = filtered_matches.apply(get_team_result, axis=1)
                    
                    # Aplicar estilos con colores transparentes
                    def highlight_result(row):
                        if row['Result'] == 'G':
                            color = 'background-color: rgba(0, 255, 0, 0.15)'  # Verde transparente
                        elif row['Result'] == 'P':
                            color = 'background-color: rgba(255, 0, 0, 0.15)'  # Rojo transparente
                        else:  # Empate
                            color = 'background-color: rgba(255, 255, 0, 0.15)'  # Amarillo transparente
                        return [color] * len(row)
                    
                    # Aplicar estilo al DataFrame completo
                    styled_df = filtered_matches.style.apply(highlight_result, axis=1)
                    
                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Fecha": st.column_config.TextColumn("Fecha", width="small"),
                            "Local": st.column_config.TextColumn("Local", width="medium"),
                            "Resultado": st.column_config.TextColumn("Resultado", width="small"),
                            "Visitante": st.column_config.TextColumn("Visitante", width="medium"),
                            "GF_Local": None,  # Ocultar columna
                            "GF_Visitante": None,  # Ocultar columna
                            "Result": None  # Ocultar columna
                        }
                    )
                else:
                    st.info("No hay partidos para mostrar")
            else:
                st.warning("⚠️ No hay partidos que cumplan con los criterios seleccionados")
        else:
            st.info("ℹ️ No hay datos de alineaciones disponibles para este equipo")
    else:
        st.warning("No hay datos disponibles")

# Footer
st.divider()
st.caption(f"Datos de Opta Sports API | Temporada {metadata.get('season', '2025/2026')}")
