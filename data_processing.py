"""
Módulo para procesar datos de partidos y generar estadísticas.
"""
import pandas as pd
from typing import List, Dict, Any


def extract_match_result(match: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae información relevante de un partido.
    
    Args:
        match: Diccionario con datos del partido
        
    Returns:
        Diccionario con información procesada del partido
    """
    if 'matchInfo' not in match:
        return None
    
    match_info = match['matchInfo']
    match_id = match_info.get('id')
    date = match_info.get('date')
    
    # Obtener equipos
    contestants = match_info.get('contestant', [])
    if not isinstance(contestants, list):
        contestants = [contestants]
    
    home_team = None
    away_team = None
    home_id = None
    away_id = None
    
    for contestant in contestants:
        if contestant.get('position') == 'home':
            home_team = contestant.get('name')
            home_id = contestant.get('id')
        elif contestant.get('position') == 'away':
            away_team = contestant.get('name')
            away_id = contestant.get('id')
    
    # Obtener resultado
    if 'liveData' not in match or 'matchDetails' not in match['liveData']:
        return None
    
    match_details = match['liveData']['matchDetails']
    match_status = match_details.get('matchStatus')
    
    # Solo procesar partidos jugados
    if match_status != 'Played':
        return None
    
    scores = match_details.get('scores', {}).get('total', {})
    home_goals = scores.get('home', 0)
    away_goals = scores.get('away', 0)
    
    # Determinar resultado
    if home_goals > away_goals:
        winner = 'home'
    elif away_goals > home_goals:
        winner = 'away'
    else:
        winner = 'draw'
    
    return {
        'match_id': match_id,
        'date': date,
        'home_team': home_team,
        'home_id': home_id,
        'away_team': away_team,
        'away_id': away_id,
        'home_goals': home_goals,
        'away_goals': away_goals,
        'winner': winner,
        'match_status': match_status,
        'goals': match.get('liveData', {}).get('goal', [])  # Agregar info de goles
    }


def match_has_red_cards(match: Dict[str, Any]) -> bool:
    """
    Verifica si un partido tuvo tarjetas rojas.
    
    Args:
        match: Datos completos del partido
        
    Returns:
        True si hubo tarjetas rojas, False en caso contrario
    """
    if 'liveData' not in match or 'lineUp' not in match['liveData']:
        return False
    
    lineups = match['liveData'].get('lineUp', [])
    if not isinstance(lineups, list):
        lineups = [lineups]
    
    # Buscar en los stats de cada equipo si hay totalRedCard > 0
    for lineup in lineups:
        team_stats = lineup.get('stat', [])
        if not isinstance(team_stats, list):
            team_stats = [team_stats]
        
        for stat in team_stats:
            if stat.get('type') == 'totalRedCard':
                red_cards = int(stat.get('value', 0))
                if red_cards > 0:
                    return True
    
    return False


def analyze_match_goals(match_result: Dict[str, Any], team_name: str) -> Dict[str, bool]:
    """
    Analiza los goles de un partido para un equipo específico.
    
    Args:
        match_result: Resultado procesado del partido
        team_name: Nombre del equipo a analizar
        
    Returns:
        Diccionario con flags: scored_first, conceded_first, comeback
    """
    if not match_result or 'goals' not in match_result:
        return {'scored_first': False, 'conceded_first': False, 'comeback': False}
    
    goals = match_result.get('goals', [])
    if not goals or not isinstance(goals, list):
        return {'scored_first': False, 'conceded_first': False, 'comeback': False}
    
    home_team = match_result['home_team']
    away_team = match_result['away_team']
    home_id = match_result['home_id']
    away_id = match_result['away_id']
    
    # Determinar si el equipo es local o visitante
    is_home = (team_name == home_team)
    team_id = home_id if is_home else away_id
    
    # Ordenar goles por tiempo
    sorted_goals = sorted(goals, key=lambda g: (g.get('periodId', 0), g.get('timeMin', 0)))
    
    if not sorted_goals:
        return {'scored_first': False, 'conceded_first': False, 'comeback': False}
    
    # Analizar primer gol
    first_goal = sorted_goals[0]
    first_goal_contestant = first_goal.get('contestantId')
    
    scored_first = (first_goal_contestant == team_id)
    conceded_first = (first_goal_contestant != team_id)
    
    # Analizar comeback (empezó perdiendo y terminó empatando o ganando)
    comeback = False
    if conceded_first:  # Solo puede haber comeback si recibió el primer gol
        # Simular el marcador gol por gol
        team_score = 0
        opponent_score = 0
        was_losing = False
        
        for goal in sorted_goals:
            if goal.get('contestantId') == team_id:
                team_score += 1
            else:
                opponent_score += 1
            
            # Verificar si estuvo perdiendo
            if opponent_score > team_score:
                was_losing = True
        
        # Si estuvo perdiendo y terminó empatando o ganando
        final_result = match_result['winner']
        if was_losing:
            if is_home and final_result in ['home', 'draw']:
                comeback = True
            elif not is_home and final_result in ['away', 'draw']:
                comeback = True
    
    return {
        'scored_first': scored_first,
        'conceded_first': conceded_first,
        'comeback': comeback
    }


def calculate_team_stats(matches: List[Dict[str, Any]], match_type: str = 'Todos', top_n_range: tuple = None, reference_standings: pd.DataFrame = None, rival_teams: list = None, advanced_filters: dict = None) -> pd.DataFrame:
    """
    Calcula estadísticas completas para cada equipo.
    
    Args:
        matches: Lista de partidos procesados
        match_type: 'Todos', 'Local', o 'Visitante'
        top_n_range: Tupla (min, max) para filtrar por rango de posiciones (ej: (1, 5) para TOP 5)
        reference_standings: Tabla de clasificación de referencia para filtrar TOP N
        rival_teams: Lista de equipos rivales específicos a considerar
        advanced_filters: Filtros avanzados (scored_first, conceded_first, comeback)
        
    Returns:
        DataFrame con estadísticas de todos los equipos
    """
    # Si se requiere filtro TOP N, obtener lista de equipos en el rango
    top_teams_list = None
    if top_n_range and reference_standings is not None:
        min_pos, max_pos = top_n_range
        top_teams_list = reference_standings[(reference_standings['Pos'] >= min_pos) & (reference_standings['Pos'] <= max_pos)]['Equipo'].tolist()
    
    # Si se especifican equipos rivales, usar esa lista (tiene prioridad sobre TOP N)
    if rival_teams and len(rival_teams) > 0:
        top_teams_list = rival_teams
    
    # Diccionario para acumular estadísticas por equipo
    team_stats = {}
    
    for match in matches:
        if match is None:
            continue
        
        home_team = match['home_team']
        away_team = match['away_team']
        home_goals = match['home_goals']
        away_goals = match['away_goals']
        winner = match['winner']
        
        # Aplicar filtro de TOP N equipos
        if top_teams_list is not None:
            # Determinar si el partido debe ser considerado
            should_include = False
            
            if match_type == 'Local':
                # Solo si juega de local Y el rival está en el rango TOP
                should_include = away_team in top_teams_list
            elif match_type == 'Visitante':
                # Solo si juega de visitante Y el rival está en el rango TOP
                should_include = home_team in top_teams_list
            else:  # 'Todos'
                # Incluir si AL MENOS uno de los dos equipos está en el rango TOP
                should_include = (home_team in top_teams_list or away_team in top_teams_list)
            
            if not should_include:
                continue
        
        # Inicializar equipos si no existen
        for team in [home_team, away_team]:
            if team not in team_stats:
                team_stats[team] = {
                    'Equipo': team,
                    'PJ': 0,  # Partidos jugados
                    'G': 0,   # Ganados
                    'E': 0,   # Empatados
                    'P': 0,   # Perdidos
                    'GF': 0,  # Goles a favor
                    'GC': 0,  # Goles en contra
                    'DG': 0,  # Diferencia de goles
                    'Pts': 0  # Puntos
                }
        
        # Actualizar estadísticas del equipo local (si aplica filtro)
        if match_type in ['Todos', 'Local']:
            # Si hay filtro TOP N, solo contar si el rival está en la lista
            if top_teams_list is None or away_team in top_teams_list:
                # Aplicar filtros avanzados
                should_count_home = True
                if advanced_filters:
                    goal_analysis = analyze_match_goals(match, home_team)
                    if advanced_filters.get('scored_first') and not goal_analysis['scored_first']:
                        should_count_home = False
                    if advanced_filters.get('conceded_first') and not goal_analysis['conceded_first']:
                        should_count_home = False
                    if advanced_filters.get('comeback') and not goal_analysis['comeback']:
                        should_count_home = False
                
                if should_count_home:
                    team_stats[home_team]['PJ'] += 1
                    team_stats[home_team]['GF'] += home_goals
                    team_stats[home_team]['GC'] += away_goals
                    
                    if winner == 'home':
                        team_stats[home_team]['G'] += 1
                        team_stats[home_team]['Pts'] += 3
                    elif winner == 'draw':
                        team_stats[home_team]['E'] += 1
                        team_stats[home_team]['Pts'] += 1
                    else:
                        team_stats[home_team]['P'] += 1
        
        # Actualizar estadísticas del equipo visitante (si aplica filtro)
        if match_type in ['Todos', 'Visitante']:
            # Si hay filtro TOP N, solo contar si el rival está en la lista
            if top_teams_list is None or home_team in top_teams_list:
                # Aplicar filtros avanzados
                should_count_away = True
                if advanced_filters:
                    goal_analysis = analyze_match_goals(match, away_team)
                    if advanced_filters.get('scored_first') and not goal_analysis['scored_first']:
                        should_count_away = False
                    if advanced_filters.get('conceded_first') and not goal_analysis['conceded_first']:
                        should_count_away = False
                    if advanced_filters.get('comeback') and not goal_analysis['comeback']:
                        should_count_away = False
                
                if should_count_away:
                    team_stats[away_team]['PJ'] += 1
                    team_stats[away_team]['GF'] += away_goals
                    team_stats[away_team]['GC'] += home_goals
                    
                    if winner == 'away':
                        team_stats[away_team]['G'] += 1
                        team_stats[away_team]['Pts'] += 3
                    elif winner == 'draw':
                        team_stats[away_team]['E'] += 1
                        team_stats[away_team]['Pts'] += 1
                    else:
                        team_stats[away_team]['P'] += 1
    
    # Calcular diferencia de goles
    for team in team_stats.values():
        team['DG'] = team['GF'] - team['GC']
        # Calcular porcentaje de puntos obtenidos
        max_points = team['PJ'] * 3
        team['%Pts'] = round((team['Pts'] / max_points * 100), 1) if max_points > 0 else 0.0
    
    # Convertir a DataFrame
    df = pd.DataFrame(list(team_stats.values()))
    
    # Ordenar por puntos (desc), diferencia de goles (desc), goles a favor (desc)
    df = df.sort_values(
        by=['Pts', 'DG', 'GF'], 
        ascending=[False, False, False]
    ).reset_index(drop=True)
    
    # Añadir columna de posición
    df.insert(0, 'Pos', range(1, len(df) + 1))
    
    return df


def build_standings_table(data: Dict[str, Any], match_type: str = 'Todos', top_n_range: tuple = None, date_range: tuple = None, rival_teams: list = None, advanced_filters: dict = None) -> pd.DataFrame:
    """
    Construye la tabla de clasificación completa desde los datos crudos.
    
    Args:
        data: Datos completos del archivo JSON
        match_type: 'Todos', 'Local', o 'Visitante'
        top_n_range: Tupla (min, max) para filtrar por rango de posiciones
        date_range: Tupla (start_date, end_date) para filtrar por fechas
        rival_teams: Lista de equipos rivales específicos a considerar
        
    Returns:
        DataFrame con la tabla de clasificación
    """
    if 'matches' not in data:
        return pd.DataFrame()
    
    matches_raw = data['matches']
    
    # Extraer resultados de TODOS los partidos (sin filtros) para la referencia TOP N
    all_matches_for_reference = []
    for match in matches_raw:
        result = extract_match_result(match)
        if result is not None:
            all_matches_for_reference.append(result)
    
    # Extraer resultados de partidos CON filtros aplicados
    matches_processed = []
    for match in matches_raw:
        result = extract_match_result(match)
        if result is not None:
            # Aplicar filtro de fechas si está activo
            if date_range:
                # Limpiar la fecha removiendo la 'Z' y parsear
                date_str = result['date']
                if isinstance(date_str, str):
                    date_str = date_str.replace('Z', '')
                
                try:
                    match_date = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')
                    if pd.notna(match_date):
                        start_date, end_date = date_range
                        # Normalizar a solo fecha (sin hora) para comparación
                        match_date_only = match_date.normalize()
                        start_datetime = pd.Timestamp(start_date)
                        end_datetime = pd.Timestamp(end_date)
                        
                        if not (start_datetime <= match_date_only <= end_datetime):
                            continue
                except:
                    # Si hay error al parsear, incluir el partido
                    pass
            
            # Aplicar filtro de tarjetas rojas si está activo
            if advanced_filters and advanced_filters.get('no_red_cards'):
                if match_has_red_cards(match):
                    continue
            
            matches_processed.append(result)
    
    # Si necesitamos filtrar por TOP N, calcular tabla completa como referencia (sin filtros de fecha)
    reference_standings = None
    if top_n_range:
        reference_standings = calculate_team_stats(all_matches_for_reference, match_type='Todos')
    
    # Calcular estadísticas con filtros
    standings = calculate_team_stats(matches_processed, match_type=match_type, top_n_range=top_n_range, reference_standings=reference_standings, rival_teams=rival_teams, advanced_filters=advanced_filters)
    
    return standings


def get_match_details_list(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Obtiene lista de todos los partidos con detalles.
    
    Args:
        data: Datos completos del archivo JSON
        
    Returns:
        DataFrame con listado de partidos
    """
    if 'matches' not in data:
        return pd.DataFrame()
    
    matches_raw = data['matches']
    matches_list = []
    
    for match in matches_raw:
        result = extract_match_result(match)
        if result is not None:
            matches_list.append({
                'Fecha': result['date'],
                'Local': result['home_team'],
                'Visitante': result['away_team'],
                'Resultado': f"{result['home_goals']} - {result['away_goals']}",
                'GF_Local': result['home_goals'],
                'GF_Visitante': result['away_goals']
            })
    
    df = pd.DataFrame(matches_list)
    
    # Convertir fecha a datetime si es posible
    if not df.empty:
        # El formato de fecha es "2022-05-15Z" - necesitamos parsearlo correctamente
        df['Fecha'] = df['Fecha'].apply(lambda x: x.replace('Z', '') if isinstance(x, str) else x)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y-%m-%d', errors='coerce')
        df = df.sort_values('Fecha', ascending=False)
    
    return df


def get_team_summary(standings: pd.DataFrame, team_name: str) -> Dict[str, Any]:
    """
    Obtiene resumen de estadísticas para un equipo específico.
    
    Args:
        standings: DataFrame con tabla de clasificación
        team_name: Nombre del equipo
        
    Returns:
        Diccionario con estadísticas del equipo
    """
    team_row = standings[standings['Equipo'] == team_name]
    
    if team_row.empty:
        return None
    
    return team_row.iloc[0].to_dict()


def get_global_stats(standings: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula estadísticas globales de la liga.
    
    Args:
        standings: DataFrame con tabla de clasificación
        
    Returns:
        Diccionario con estadísticas globales
    """
    return {
        'total_teams': len(standings),
        'total_matches': standings['PJ'].sum() // 2,  # Dividir por 2 porque cada partido cuenta para 2 equipos
        'total_goals': standings['GF'].sum(),
        'avg_goals_per_match': standings['GF'].sum() / (standings['PJ'].sum() / 2) if standings['PJ'].sum() > 0 else 0,
        'leader': standings.iloc[0]['Equipo'] if len(standings) > 0 else None,
        'leader_points': int(standings.iloc[0]['Pts']) if len(standings) > 0 else 0
    }


def get_team_starting_players(match: Dict[str, Any], team_name: str) -> List[str]:
    """
    Obtiene la lista de jugadores titulares de un equipo en un partido.
    
    Args:
        match: Datos completos del partido
        team_name: Nombre del equipo
        
    Returns:
        Lista de nombres de jugadores titulares
    """
    if 'liveData' not in match or 'lineUp' not in match['liveData']:
        return []
    
    lineups = match['liveData'].get('lineUp', [])
    if not isinstance(lineups, list):
        lineups = [lineups]
    
    # Buscar el lineup del equipo
    for lineup in lineups:
        contestant_id = lineup.get('contestantId')
        
        # Verificar si este lineup corresponde al equipo
        if 'matchInfo' in match:
            contestants = match['matchInfo'].get('contestant', [])
            if not isinstance(contestants, list):
                contestants = [contestants]
            
            for contestant in contestants:
                if contestant.get('id') == contestant_id and contestant.get('name') == team_name:
                    # Este es el lineup del equipo que buscamos
                    players = lineup.get('player', [])
                    if not isinstance(players, list):
                        players = [players]
                    
                    # Filtrar solo titulares (los que NO tienen position "Substitute")
                    starters = [
                        p.get('matchName', p.get('lastName', ''))
                        for p in players
                        if p.get('position') != 'Substitute'
                    ]
                    return starters
    
    return []


def get_team_manager(match: Dict[str, Any], team_name: str) -> str:
    """
    Obtiene el nombre del entrenador de un equipo en un partido.
    
    Args:
        match: Datos completos del partido
        team_name: Nombre del equipo
        
    Returns:
        Nombre del entrenador o cadena vacía si no se encuentra
    """
    if 'liveData' not in match or 'lineUp' not in match['liveData']:
        return ""
    
    lineups = match['liveData'].get('lineUp', [])
    if not isinstance(lineups, list):
        lineups = [lineups]
    
    # Buscar el lineup del equipo
    for lineup in lineups:
        contestant_id = lineup.get('contestantId')
        
        # Verificar si este lineup corresponde al equipo
        if 'matchInfo' in match:
            contestants = match['matchInfo'].get('contestant', [])
            if not isinstance(contestants, list):
                contestants = [contestants]
            
            for contestant in contestants:
                if contestant.get('id') == contestant_id and contestant.get('name') == team_name:
                    # Este es el lineup del equipo que buscamos
                    team_officials = lineup.get('teamOfficial', [])
                    if not isinstance(team_officials, list):
                        team_officials = [team_officials]
                    
                    # Buscar el manager
                    for official in team_officials:
                        if official.get('type') == 'manager':
                            # Construir nombre completo: preferir matchName, sino firstName + lastName
                            match_name = official.get('matchName')
                            if match_name:
                                return match_name
                            
                            first_name = official.get('firstName', official.get('shortFirstName', ''))
                            last_name = official.get('lastName', official.get('shortLastName', ''))
                            
                            if first_name and last_name:
                                return f"{first_name} {last_name}"
                            elif last_name:
                                return last_name
                            elif first_name:
                                return first_name
                            
                            return ''
    
    return ""


def get_all_players_for_team(data: Dict[str, Any], team_name: str) -> List[str]:
    """
    Obtiene la lista de todos los jugadores que jugaron para un equipo.
    
    Args:
        data: Datos completos del archivo JSON
        team_name: Nombre del equipo
        
    Returns:
        Lista ordenada de nombres de jugadores únicos
    """
    all_players = set()
    
    if 'matches' not in data:
        return []
    
    for match in data['matches']:
        starters = get_team_starting_players(match, team_name)
        all_players.update(starters)
    
    return sorted(list(all_players))


def get_all_managers_for_team(data: Dict[str, Any], team_name: str) -> List[str]:
    """
    Obtiene la lista de todos los entrenadores de un equipo.
    
    Args:
        data: Datos completos del archivo JSON
        team_name: Nombre del equipo
        
    Returns:
        Lista ordenada de nombres de entrenadores únicos
    """
    all_managers = set()
    
    if 'matches' not in data:
        return []
    
    for match in data['matches']:
        manager = get_team_manager(match, team_name)
        if manager:
            all_managers.add(manager)
    
    return sorted(list(all_managers))


def calculate_team_stats_with_players(data: Dict[str, Any], team_name: str, include_players: List[str] = None, exclude_players: List[str] = None, manager: str = None) -> Dict[str, Any]:
    """
    Calcula estadísticas de un equipo filtrado por jugadores titulares.
    
    Args:
        data: Datos completos del archivo JSON
        team_name: Nombre del equipo
        include_players: Lista de jugadores que DEBEN ser titulares (todos)
        exclude_players: Lista de jugadores que NO deben ser titulares (ninguno)
        
    Returns:
        Diccionario con estadísticas
    """
    if 'matches' not in data:
        return {
            'total_matches': 0,
            'total_points': 0,
            'points_percentage': 0.0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'wins': 0,
            'draws': 0,
            'losses': 0
        }
    
    stats = {
        'total_matches': 0,
        'total_points': 0,
        'points_percentage': 0.0,
        'goals_for': 0,
        'goals_against': 0,
        'goal_difference': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0
    }
    
    for match in data['matches']:
        # Extraer resultado del partido
        result = extract_match_result(match)
        if result is None:
            continue
        
        # Verificar si el equipo participa en este partido
        is_home = (result['home_team'] == team_name)
        is_away = (result['away_team'] == team_name)
        
        if not is_home and not is_away:
            continue
        
        # Obtener jugadores titulares del equipo en este partido
        starters = get_team_starting_players(match, team_name)
        
        # Aplicar filtros de jugadores
        if include_players:
            # Todos los jugadores incluidos deben estar en los titulares
            if not all(player in starters for player in include_players):
                continue
        
        if exclude_players:
            # Ninguno de los jugadores excluidos debe estar en los titulares
            if any(player in starters for player in exclude_players):
                continue
        
        # Aplicar filtro de entrenador
        if manager:
            match_manager = get_team_manager(match, team_name)
            if match_manager != manager:
                continue
        
        # Contar este partido
        stats['total_matches'] += 1
        
        # Calcular resultado para el equipo
        if is_home:
            stats['goals_for'] += result['home_goals']
            stats['goals_against'] += result['away_goals']
            
            if result['winner'] == 'home':
                stats['wins'] += 1
                stats['total_points'] += 3
            elif result['winner'] == 'draw':
                stats['draws'] += 1
                stats['total_points'] += 1
            else:
                stats['losses'] += 1
        else:  # is_away
            stats['goals_for'] += result['away_goals']
            stats['goals_against'] += result['home_goals']
            
            if result['winner'] == 'away':
                stats['wins'] += 1
                stats['total_points'] += 3
            elif result['winner'] == 'draw':
                stats['draws'] += 1
                stats['total_points'] += 1
            else:
                stats['losses'] += 1
    
    # Calcular diferencia de goles y porcentaje de puntos
    stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
    if stats['total_matches'] > 0:
        max_points = stats['total_matches'] * 3
        stats['points_percentage'] = (stats['total_points'] / max_points * 100) if max_points > 0 else 0.0
    
    return stats


def get_filtered_matches_by_players(data: Dict[str, Any], team_name: str, include_players: List[str] = None, exclude_players: List[str] = None, manager: str = None) -> pd.DataFrame:
    """
    Obtiene la lista de partidos filtrados por jugadores titulares.
    
    Args:
        data: Datos completos del archivo JSON
        team_name: Nombre del equipo
        include_players: Lista de jugadores que DEBEN ser titulares (todos)
        exclude_players: Lista de jugadores que NO deben ser titulares (ninguno)
        manager: Nombre del entrenador a filtrar (opcional)
        
    Returns:
        DataFrame con partidos filtrados
    """
    if 'matches' not in data:
        return pd.DataFrame()
    
    filtered_matches = []
    
    for match in data['matches']:
        # Extraer resultado del partido
        result = extract_match_result(match)
        if result is None:
            continue
        
        # Verificar si el equipo participa en este partido
        is_home = (result['home_team'] == team_name)
        is_away = (result['away_team'] == team_name)
        
        if not is_home and not is_away:
            continue
        
        # Obtener jugadores titulares del equipo en este partido
        starters = get_team_starting_players(match, team_name)
        
        # Aplicar filtros de jugadores
        if include_players:
            # Todos los jugadores incluidos deben estar en los titulares
            if not all(player in starters for player in include_players):
                continue
        
        if exclude_players:
            # Ninguno de los jugadores excluidos debe estar en los titulares
            if any(player in starters for player in exclude_players):
                continue
        
        # Aplicar filtro de entrenador
        if manager:
            match_manager = get_team_manager(match, team_name)
            if match_manager != manager:
                continue
        
        # Agregar partido a la lista
        filtered_matches.append({
            'Fecha': result['date'],
            'Local': result['home_team'],
            'Visitante': result['away_team'],
            'Resultado': f"{result['home_goals']} - {result['away_goals']}",
            'GF_Local': result['home_goals'],
            'GF_Visitante': result['away_goals']
        })
    
    df = pd.DataFrame(filtered_matches)
    
    if not df.empty:
        # Convertir fecha a datetime
        df['Fecha'] = df['Fecha'].apply(lambda x: x.replace('Z', '') if isinstance(x, str) else x)
        df['Fecha'] = pd.to_datetime(df['Fecha'], format='%Y-%m-%d', errors='coerce')
        df = df.sort_values('Fecha', ascending=False)
        df['Fecha'] = df['Fecha'].dt.strftime('%d/%m/%Y')
    
    return df
