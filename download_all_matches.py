"""
Script para descargar todos los partidos de la Segunda División 2025/2026.
Itera sobre el schedule y descarga detalles de cada partido.
Soporta modo incremental (delta) y filtrado por fecha.
"""
import json
import time
from pathlib import Path
from datetime import datetime, date
from stats_perform_client import StatsPerformClient
from config import (
    OUTLET_KEY,
    SECRET_KEY,
    BASE_URL,
    OAUTH_URL,
    SPORT,
    TIMEOUT,
    MAX_RETRIES,
    BACKOFF_SECONDS,
    SEGUNDA_DIVISION_ESPAÑA_TMCL_ID
)


def load_existing_matches(output_file: str) -> dict:
    """
    Carga los partidos existentes del archivo de salida.
    
    Args:
        output_file: Archivo con datos existentes
        
    Returns:
        Diccionario con match_ids existentes y sus datos
    """
    output_path = Path(output_file)
    if not output_path.exists():
        return {}
    
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Crear índice de partidos existentes
        existing = {}
        if 'matches' in data and data['matches']:
            for match in data['matches']:
                if isinstance(match, dict) and 'matchInfo' in match:
                    match_id = match['matchInfo'].get('id')
                    if match_id:
                        existing[match_id] = match
        
        return existing
    except Exception as e:
        print(f"   ⚠️  Error cargando archivo existente: {e}")
        return {}


def download_all_matches(
    output_file: str = "segunda_division_2025_2026_matches.json",
    cache_dir: str = "match_cache",
    only_played: bool = True,
    incremental: bool = True
):
    """
    Descarga todos los partidos de la Segunda División temporada 2025/2026.
    
    Args:
        output_file: Archivo de salida con todos los partidos consolidados
        cache_dir: Directorio para cachear partidos individuales
        only_played: Si True, solo descarga partidos hasta hoy (ya jugados)
        incremental: Si True, solo descarga partidos nuevos (delta)
    """
    print("="*80)
    print("DESCARGANDO PARTIDOS - SEGUNDA DIVISIÓN 2025/2026")
    print("="*80)
    print(f"\nModo: {'Incremental (delta)' if incremental else 'Completo'}")
    print(f"Filtro: {'Solo partidos jugados hasta hoy' if only_played else 'Todos los partidos'}")
    
    # Fecha de hoy para filtrado
    today = date.today()
    print(f"Fecha actual: {today.isoformat()}")
    
    # Cargar partidos existentes si es incremental
    existing_matches = {}
    if incremental:
        print(f"\n📂 Cargando partidos existentes de {output_file}...")
        existing_matches = load_existing_matches(output_file)
        print(f"   ✓ Encontrados {len(existing_matches)} partidos en base de datos")
    
    # Crear directorio de cache
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)
    
    # Inicializar cliente
    print("\n1. Inicializando cliente...")
    client = StatsPerformClient(
        outlet_key=OUTLET_KEY,
        secret_key=SECRET_KEY,
        base_url=BASE_URL,
        oauth_url=OAUTH_URL,
        sport=SPORT,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES,
        backoff_seconds=BACKOFF_SECONDS,
        use_oauth=True
    )
    print("   ✓ Cliente inicializado")
    
    # Obtener schedule con todos los match IDs
    print(f"\n2. Obteniendo schedule de la temporada...")
    try:
        schedule_data = client.get_tournament_schedule(
            SEGUNDA_DIVISION_ESPAÑA_TMCL_ID,
            extra_params={"_fmt": "json"}
        )
        
        # Guardar schedule
        schedule_file = "tournament_schedule_full.json"
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        print(f"   ✓ Schedule guardado en: {schedule_file}")
        
    except Exception as e:
        print(f"   ✗ Error obteniendo schedule: {e}")
        return
    
    # Extraer todos los match IDs
    print("\n3. Extrayendo IDs de partidos...")
    match_ids = []
    
    if 'matchDate' in schedule_data:
        match_dates = schedule_data['matchDate']
        if not isinstance(match_dates, list):
            match_dates = [match_dates]
        
        for match_date in match_dates:
            match_date_str = match_date.get('date')
            
            # Filtrar por fecha si only_played está activado
            if only_played and match_date_str:
                try:
                    # Convertir fecha del partido a date object (formato: YYYY-MM-DDZ)
                    match_date_obj = datetime.strptime(match_date_str.replace('Z', ''), '%Y-%m-%d').date()
                    
                    # Saltar partidos futuros
                    if match_date_obj > today:
                        continue
                except Exception as e:
                    print(f"   ⚠️  Error parseando fecha {match_date_str}: {e}")
            
            if 'match' in match_date:
                matches = match_date['match']
                if not isinstance(matches, list):
                    matches = [matches]
                
                for match in matches:
                    match_id = match.get('id')
                    if match_id:
                        match_ids.append({
                            'id': match_id,
                            'date': match_date_str,
                            'home': match.get('homeContestantName'),
                            'away': match.get('awayContestantName')
                        })
    
    total_matches = len(match_ids)
    print(f"   ✓ Encontrados {total_matches} partidos")
    if only_played:
        print(f"   📅 Filtrados hasta {today.isoformat()}")
    
    # Filtrar partidos nuevos si es incremental
    if incremental and existing_matches:
        new_match_ids = [m for m in match_ids if m['id'] not in existing_matches]
        print(f"\n   🔄 Modo incremental:")
        print(f"      Total en schedule: {total_matches}")
        print(f"      Ya en base datos:  {len(existing_matches)}")
        print(f"      Nuevos a descargar: {len(new_match_ids)}")
        match_ids = new_match_ids
        
        if not match_ids:
            print(f"\n   ✅ No hay partidos nuevos para descargar")
            print(f"   📊 Base de datos actualizada con {len(existing_matches)} partidos")
            return None
    
    # Descargar detalles de cada partido
    num_to_download = len(match_ids)
    print(f"\n4. Descargando detalles de {num_to_download} partidos...")
    if num_to_download > 0:
        print(f"   Esto puede tomar varios minutos...\n")
    
    all_matches_data = list(existing_matches.values()) if incremental else []
    successful = 0
    errors = 0
    skipped = 0
    
    for idx, match_info in enumerate(match_ids, 1):
        match_id = match_info['id']
        cache_file = cache_path / f"{match_id}.json"
        
        # Verificar si ya existe en cache
        if cache_file.exists():
            print(f"   [{idx}/{num_to_download}] ⏭️  {match_info['home']} vs {match_info['away']} (cached)")
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    match_data = json.load(f)
                all_matches_data.append(match_data)
                skipped += 1
            except Exception as e:
                print(f"      ⚠️  Error leyendo cache: {e}")
            continue
        
        # Descargar partido
        try:
            print(f"   [{idx}/{num_to_download}] 📥 {match_info['home']} vs {match_info['away']}...", end=" ")
            
            match_data = client.get_match_stats_by_id(match_id)
            
            # Verificar si hay error
            if isinstance(match_data, dict) and 'errorCode' in match_data:
                print(f"❌ Error {match_data['errorCode']}")
                errors += 1
                continue
            
            # Guardar en cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(match_data, f, indent=2, ensure_ascii=False)
            
            all_matches_data.append(match_data)
            successful += 1
            print("✓")
            
            # Pequeña pausa para no saturar la API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1
            continue
    
    # Guardar archivo consolidado
    print(f"\n5. Guardando archivo consolidado...")
    
    total_in_file = len(all_matches_data)
    
    consolidated_data = {
        "metadata": {
            "competition": "Segunda División España",
            "season": "2025/2026",
            "tournamentCalendarId": SEGUNDA_DIVISION_ESPAÑA_TMCL_ID,
            "lastUpdate": datetime.now().isoformat(),
            "downloadMode": "incremental" if incremental else "full",
            "totalMatches": total_in_file,
            "newDownloads": successful,
            "errors": errors,
            "fromCache": skipped,
            "onlyPlayed": only_played,
            "filterDate": today.isoformat() if only_played else None
        },
        "matches": all_matches_data
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(consolidated_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Datos guardados en: {output_file}")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE DESCARGA")
    print("="*80)
    print(f"  Total de partidos en archivo:  {total_in_file}")
    print(f"  ✓ Descargados nuevos:          {successful}")
    print(f"  ⏭️  Desde cache:                 {skipped}")
    print(f"  ❌ Errores:                     {errors}")
    if incremental and existing_matches:
        print(f"  📂 Partidos previos:            {len(existing_matches)}")
    print("="*80)
    
    # Mostrar tamaño del archivo
    file_size = Path(output_file).stat().st_size / (1024 * 1024)  # MB
    print(f"\nTamaño del archivo: {file_size:.2f} MB")
    
    return consolidated_data


if __name__ == "__main__":
    print("\n🏆 SEGUNDA DIVISIÓN ESPAÑA - DESCARGA DE DATOS\n")
    
    import argparse
    parser = argparse.ArgumentParser(description='Descarga partidos de la Segunda División')
    parser.add_argument('--full', action='store_true', help='Descarga completa (ignora base existente)')
    parser.add_argument('--all-dates', action='store_true', help='Incluir partidos futuros')
    args = parser.parse_args()
    
    incremental = not args.full
    only_played = not args.all_dates
    
    try:
        data = download_all_matches(
            incremental=incremental,
            only_played=only_played
        )
        
        if data is None:
            print("\n✅ Base de datos ya está actualizada")
        elif data and data['matches']:
            print("\n✅ ¡DESCARGA COMPLETADA EXITOSAMENTE!")
            print(f"\nArchivo generado: 'segunda_division_2025_2026_matches.json'")
            print(f"Total de partidos: {len(data['matches'])}")
        else:
            print("\n⚠️  No se pudieron descargar datos")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Descarga interrumpida por el usuario")
        print("Los partidos descargados están guardados en 'match_cache/'")
        print("Puedes volver a ejecutar el script para continuar")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
