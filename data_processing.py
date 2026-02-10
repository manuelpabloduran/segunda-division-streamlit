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


def get_minutes_played_by_player(data: Dict[str, Any], team_name: str, include_players: List[str] = None, exclude_players: List[str] = None, manager: str = None, date_range: tuple = None) -> Dict[str, int]:
    """
    Obtiene los minutos jugados totales por cada jugador en partidos filtrados.
    
    Args:
        data: Datos completos del archivo JSON
        team_name: Nombre del equipo
        include_players: Lista de jugadores que DEBEN ser titulares (todos)
        exclude_players: Lista de jugadores que NO deben ser titulares (ninguno)
        manager: Nombre del entrenador a filtrar (opcional)
        date_range: Tupla (start_date, end_date) en formato datetime (opcional)
        
    Returns:
        Diccionario con {nombre_jugador: minutos_totales}
    """
    if 'matches' not in data:
        return {}
    
    player_minutes = {}
    
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
        
        # Aplicar filtro de fechas si existe
        if date_range:
            try:
                date_str = str(result['date']).replace('Z', '').split('T')[0]
                match_date = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')
                if pd.isna(match_date) or not (date_range[0] <= match_date <= date_range[1]):
                    continue
            except:
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
        
        # Obtener el contestantId del equipo
        contestant_id = None
        match_info = match.get('matchInfo', {})
        for contestant in match_info.get('contestant', []):
            if contestant.get('name') == team_name:
                contestant_id = contestant.get('id')
                break
        
        if not contestant_id:
            continue
        
        # Extraer minutos jugados de cada jugador del equipo
        lineup = match.get('liveData', {}).get('lineUp', [])
        for team_lineup in lineup:
            if team_lineup.get('contestantId') != contestant_id:
                continue
            
            # Iterar sobre los jugadores de este equipo
            players = team_lineup.get('player', [])
            for player_data in players:
                player_name = player_data.get('matchName', '')
                if not player_name:
                    continue
                
                # Buscar estadística de minutos jugados
                stats = player_data.get('stat', [])
                minutes = 0
                for stat in stats:
                    if stat.get('type') == 'minsPlayed':
                        try:
                            minutes = int(stat.get('value', 0))
                        except (ValueError, TypeError):
                            minutes = 0
                        break
                
                # Sumar minutos al jugador
                if player_name in player_minutes:
                    player_minutes[player_name] += minutes
                else:
                    player_minutes[player_name] = minutes
    
    return player_minutes


def calculate_competitiveness_index(data: Dict[str, Any], team_name: str, include_players: List[str] = None, exclude_players: List[str] = None, manager: str = None, date_range: tuple = None) -> pd.DataFrame:
    """
    Calcula el índice de competitividad por jugador según la fórmula:
    indice = (minutes_norm + played_points + diff_points + played_gd + total_points) / 3.33
    
    Returns DataFrame con métricas por jugador.
    """
    if 'matches' not in data:
        return pd.DataFrame()
    
    player_match_records = []
    
    for match in data['matches']:
        result = extract_match_result(match)
        if result is None:
            continue
        
        # Verificar equipo participa
        is_home = (result['home_team'] == team_name)
        is_away = (result['away_team'] == team_name)
        if not is_home and not is_away:
            continue
        
        # Aplicar filtro de fechas si existe
        if date_range:
            try:
                date_str = str(result['date']).replace('Z', '').split('T')[0]
                match_date = pd.to_datetime(date_str, format='%Y-%m-%d', errors='coerce')
                if pd.isna(match_date) or not (date_range[0] <= match_date <= date_range[1]):
                    continue
            except:
                continue
        
        # Filtros de jugadores titulares
        starters = get_team_starting_players(match, team_name)
        if include_players and not all(p in starters for p in include_players):
            continue
        if exclude_players and any(p in starters for p in exclude_players):
            continue
        
        # Filtro de entrenador
        if manager:
            match_manager = get_team_manager(match, team_name)
            if match_manager != manager:
                continue
        
        # Calcular resultado final del partido
        team_goals = result['home_goals'] if is_home else result['away_goals']
        rival_goals = result['away_goals'] if is_home else result['home_goals']
        
        if team_goals > rival_goals:
            total_result = 'win'
            total_points = 3
        elif team_goals < rival_goals:
            total_result = 'loss'
            total_points = 0
        else:
            total_result = 'draw'
            total_points = 1
        
        total_gd = team_goals - rival_goals
        
        # Obtener tramos de jugadores y goles
        player_segments = get_player_segments_in_match(match, team_name)
        player_is_starter = get_player_starter_status(match, team_name)
        goals_timeline = get_goals_timeline(match, team_name)
        match_end_time = get_match_end_time(match, goals_timeline)
        
        # Para cada jugador calcular sus métricas
        for player_name, segment in player_segments.items():
            min_start, min_end_or_none = segment
            min_end = min_end_or_none if min_end_or_none is not None else match_end_time
            
            minutes_played = min_end - min_start
            minutes_norm = min(minutes_played / 90, 1.0)
            
            # Determinar si es titular o suplente
            is_starter = player_is_starter.get(player_name, False)
            
            # Si es suplente, determinar resultado del equipo al momento de entrar
            sub_entry_situation = None
            if not is_starter and min_start > 0:
                gf_before, gc_before = calculate_goals_in_segment(goals_timeline, 0, min_start, is_home)
                if gf_before > gc_before:
                    sub_entry_situation = 'winning'
                elif gf_before < gc_before:
                    sub_entry_situation = 'losing'
                else:
                    sub_entry_situation = 'drawing'
            
            # Goles en su tramo
            gf_played, gc_played = calculate_goals_in_segment(goals_timeline, min_start, min_end, is_home)
            played_gd = gf_played - gc_played
            
            # Resultado en su tramo
            if gf_played > gc_played:
                played_result = 'win'
                played_points = 3
            elif gf_played < gc_played:
                played_result = 'loss'
                played_points = 0
            else:
                played_result = 'draw'
                played_points = 1
            
            # Goles sin el jugador (resto del partido)
            gf_without, gc_without = calculate_goals_outside_segment(goals_timeline, min_start, min_end, match_end_time, is_home)
            minutes_without = match_end_time - minutes_played
            
            # Resultado sin el jugador
            if minutes_without == 0:
                without_result = None
                without_points = None
                diff_points = 0.0
            else:
                if gf_without > gc_without:
                    without_result = 'win'
                    without_points = 3
                elif gf_without < gc_without:
                    without_result = 'loss'
                    without_points = 0
                else:
                    without_result = 'draw'
                    without_points = 1
                
                diff_points = played_points - without_points
            
            # Índice de competitividad
            indice = (minutes_norm + played_points + diff_points + played_gd + total_points) / 3.33
            
            player_match_records.append({
                'player_name': player_name,
                'match_date': result['date'],
                'rival': result['away_team'] if is_home else result['home_team'],
                'minutes_played': minutes_played,
                'minutes_norm': minutes_norm,
                'played_points': played_points,
                'without_points': without_points,
                'diff_points': diff_points,
                'played_gd': played_gd,
                'total_points': total_points,
                'indice_competitividad': indice,
                'total_result': total_result,
                'is_starter': is_starter,
                'sub_entry_situation': sub_entry_situation
            })
    
    if not player_match_records:
        return pd.DataFrame()
    
    df = pd.DataFrame(player_match_records)
    
    # Calcular métricas generales
    df_player = df.groupby('player_name', as_index=False).agg(
        total_minutes_played=('minutes_played', 'sum'),
        avg_indice_competitividad=('indice_competitividad', 'mean'),
        sum_played_gd=('played_gd', 'sum'),
        sum_diff_points=('diff_points', 'sum'),
        n_games=('match_date', 'count')
    )
    
    # Calcular índices por condición
    # Titular
    df_starter = df[df['is_starter'] == True].groupby('player_name', as_index=False).agg(
        indice_titular=('indice_competitividad', 'mean'),
        minutes_titular=('minutes_played', 'sum')
    )
    
    # Suplente ganando
    df_sub_winning = df[(df['is_starter'] == False) & (df['sub_entry_situation'] == 'winning')].groupby('player_name', as_index=False).agg(
        indice_suplente_ganando=('indice_competitividad', 'mean'),
        minutes_suplente_ganando=('minutes_played', 'sum')
    )
    
    # Suplente empatando
    df_sub_drawing = df[(df['is_starter'] == False) & (df['sub_entry_situation'] == 'drawing')].groupby('player_name', as_index=False).agg(
        indice_suplente_empatando=('indice_competitividad', 'mean'),
        minutes_suplente_empatando=('minutes_played', 'sum')
    )
    
    # Suplente perdiendo
    df_sub_losing = df[(df['is_starter'] == False) & (df['sub_entry_situation'] == 'losing')].groupby('player_name', as_index=False).agg(
        indice_suplente_perdiendo=('indice_competitividad', 'mean'),
        minutes_suplente_perdiendo=('minutes_played', 'sum')
    )
    
    # Merge todos
    df_player = df_player.merge(df_starter, on='player_name', how='left')
    df_player = df_player.merge(df_sub_winning, on='player_name', how='left')
    df_player = df_player.merge(df_sub_drawing, on='player_name', how='left')
    df_player = df_player.merge(df_sub_losing, on='player_name', how='left')
    
    # Calcular partidos totales del equipo (con filtros aplicados)
    total_team_games = len(df['match_date'].unique())
    df_player['pct_minutes_played'] = (df_player['total_minutes_played'] / (total_team_games * 90)).clip(upper=1.0)
    
    return df_player


def get_player_segments_in_match(match: Dict[str, Any], team_name: str) -> Dict[str, tuple]:
    """
    Retorna dict {player_name: (min_start, min_end_or_None)}
    None significa que jugó hasta el final del partido.
    """
    segments = {}
    
    match_info = match.get('matchInfo', {})
    contestant_id = None
    for c in match_info.get('contestant', []):
        if c.get('name') == team_name:
            contestant_id = c.get('id')
            break
    
    if not contestant_id:
        return segments
    
    live_data = match.get('liveData', {})
    lineup = live_data.get('lineUp', [])
    
    # Encontrar jugadores del equipo
    team_lineup = None
    for tl in lineup:
        if tl.get('contestantId') == contestant_id:
            team_lineup = tl
            break
    
    if not team_lineup:
        return segments
    
    players = team_lineup.get('player', [])
    
    # Mapear playerId -> matchName
    player_id_to_name = {p.get('playerId'): p.get('matchName') for p in players if p.get('matchName')}
    
    # Obtener sustituciones
    substitutes = live_data.get('substitute', [])
    team_subs = [s for s in substitutes if s.get('contestantId') == contestant_id]
    
    # Construir diccionario de entrada/salida
    player_in = {}   # playerId -> timeMin
    player_out = {}  # playerId -> timeMin
    
    for sub in team_subs:
        on_id = sub.get('playerOnId')
        off_id = sub.get('playerOffId')
        time_min = sub.get('timeMin', 0)
        
        if on_id:
            player_in[on_id] = time_min
        if off_id:
            player_out[off_id] = time_min
    
    # Para cada jugador determinar su tramo
    for player in players:
        player_id = player.get('playerId')
        player_name = player.get('matchName')
        
        if not player_name:
            continue
        
        stats = player.get('stat', [])
        game_started = any(s.get('type') == 'gameStarted' and s.get('value') == '1' for s in stats)
        
        if game_started:
            # Titular
            min_start = 0
            min_end = player_out.get(player_id)  # None si no salió
        else:
            # Suplente
            min_start = player_in.get(player_id)
            if min_start is None:
                continue  # No entró
            min_end = player_out.get(player_id)  # None si no salió
        
        segments[player_name] = (min_start, min_end)
    
    return segments


def get_player_starter_status(match: Dict[str, Any], team_name: str) -> Dict[str, bool]:
    """
    Retorna dict {player_name: is_starter}
    """
    starter_status = {}
    
    match_info = match.get('matchInfo', {})
    contestant_id = None
    for c in match_info.get('contestant', []):
        if c.get('name') == team_name:
            contestant_id = c.get('id')
            break
    
    if not contestant_id:
        return starter_status
    
    live_data = match.get('liveData', {})
    lineup = live_data.get('lineUp', [])
    
    # Encontrar jugadores del equipo
    team_lineup = None
    for tl in lineup:
        if tl.get('contestantId') == contestant_id:
            team_lineup = tl
            break
    
    if not team_lineup:
        return starter_status
    
    players = team_lineup.get('player', [])
    
    for player in players:
        player_name = player.get('matchName')
        if not player_name:
            continue
        
        stats = player.get('stat', [])
        game_started = any(s.get('type') == 'gameStarted' and s.get('value') == '1' for s in stats)
        
        starter_status[player_name] = game_started
    
    return starter_status


def get_goals_timeline(match: Dict[str, Any], team_name: str) -> List[Dict]:
    """
    Retorna lista de goles con {timeMin, is_team_goal, is_home}
    """
    timeline = []
    
    result = extract_match_result(match)
    if not result:
        return timeline
    
    is_home = (result['home_team'] == team_name)
    
    match_info = match.get('matchInfo', {})
    contestant_id = None
    for c in match_info.get('contestant', []):
        if c.get('name') == team_name:
            contestant_id = c.get('id')
            break
    
    live_data = match.get('liveData', {})
    goals = live_data.get('goal', [])
    
    for goal in goals:
        time_min = goal.get('timeMin', 0)
        goal_contestant = goal.get('contestantId')
        is_team_goal = (goal_contestant == contestant_id)
        
        timeline.append({
            'timeMin': time_min,
            'is_team_goal': is_team_goal,
            'is_home': is_home
        })
    
    return timeline


def get_match_end_time(match: Dict[str, Any], goals_timeline: List[Dict]) -> int:
    """
    Determina el minuto final del partido basándose en goles y sustituciones.
    """
    max_time = 90
    
    # Máximo de goles
    if goals_timeline:
        max_goal_time = max(g['timeMin'] for g in goals_timeline)
        max_time = max(max_time, max_goal_time)
    
    # Máximo de sustituciones
    live_data = match.get('liveData', {})
    substitutes = live_data.get('substitute', [])
    if substitutes:
        max_sub_time = max(s.get('timeMin', 0) for s in substitutes)
        max_time = max(max_time, max_sub_time)
    
    return max_time


def calculate_goals_in_segment(goals_timeline: List[Dict], min_start: int, min_end: int, is_home: bool) -> tuple:
    """
    Retorna (goles_a_favor, goles_en_contra) en el segmento [min_start, min_end]
    """
    gf = 0
    gc = 0
    
    for goal in goals_timeline:
        time = goal['timeMin']
        if min_start <= time <= min_end:
            if goal['is_team_goal']:
                gf += 1
            else:
                gc += 1
    
    return gf, gc


def calculate_goals_outside_segment(goals_timeline: List[Dict], min_start: int, min_end: int, match_end: int, is_home: bool) -> tuple:
    """
    Retorna (goles_a_favor, goles_en_contra) FUERA del segmento [min_start, min_end]
    """
    gf = 0
    gc = 0
    
    for goal in goals_timeline:
        time = goal['timeMin']
        if time < min_start or time > min_end:
            if goal['is_team_goal']:
                gf += 1
            else:
                gc += 1
    
    return gf, gc
