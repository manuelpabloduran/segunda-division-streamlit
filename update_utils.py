"""
Utilidades para actualización automática de datos desde Streamlit.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from download_all_matches import download_all_matches


def needs_update(
    data_file: str = "segunda_division_2025_2026_matches.json",
    max_hours: int = 24
) -> bool:
    """
    Verifica si los datos necesitan actualización.
    
    Args:
        data_file: Archivo de datos a verificar
        max_hours: Horas máximas sin actualizar (default 24h)
        
    Returns:
        True si necesita actualización, False si no
    """
    data_path = Path(data_file)
    
    # Si no existe el archivo, necesita actualización
    if not data_path.exists():
        return True
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Verificar metadata de última actualización
        if 'metadata' not in data or 'lastUpdate' not in data['metadata']:
            return True
        
        last_update_str = data['metadata']['lastUpdate']
        last_update = datetime.fromisoformat(last_update_str)
        
        # Calcular diferencia de tiempo
        now = datetime.now()
        hours_since_update = (now - last_update).total_seconds() / 3600
        
        return hours_since_update >= max_hours
        
    except Exception as e:
        print(f"Error verificando actualización: {e}")
        return True


def get_last_update_info(data_file: str = "segunda_division_2025_2026_matches.json") -> dict:
    """
    Obtiene información sobre la última actualización.
    
    Returns:
        Diccionario con información de última actualización
    """
    data_path = Path(data_file)
    
    if not data_path.exists():
        return {
            "exists": False,
            "lastUpdate": None,
            "totalMatches": 0,
            "needsUpdate": True
        }
    
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        last_update_str = metadata.get('lastUpdate')
        
        last_update = None
        hours_ago = None
        
        if last_update_str:
            last_update = datetime.fromisoformat(last_update_str)
            hours_ago = (datetime.now() - last_update).total_seconds() / 3600
        
        return {
            "exists": True,
            "lastUpdate": last_update,
            "hoursAgo": hours_ago,
            "totalMatches": metadata.get('totalMatches', 0),
            "downloadMode": metadata.get('downloadMode', 'unknown'),
            "needsUpdate": needs_update(data_file)
        }
        
    except Exception as e:
        return {
            "exists": True,
            "error": str(e),
            "needsUpdate": True
        }


def auto_update_if_needed(
    max_hours: int = 24,
    force: bool = False,
    verbose: bool = True
) -> dict:
    """
    Actualiza automáticamente si es necesario (modo incremental).
    Ideal para llamar al inicio de Streamlit.
    
    Args:
        max_hours: Horas máximas sin actualizar antes de forzar actualización
        force: Si True, fuerza actualización sin importar cuándo fue la última
        verbose: Si True, imprime mensajes de progreso
        
    Returns:
        Diccionario con resultado de la actualización
    """
    if verbose:
        print("🔍 Verificando si hay datos nuevos...")
    
    # Verificar si necesita actualización
    if not force and not needs_update(max_hours=max_hours):
        info = get_last_update_info()
        if verbose:
            print(f"✅ Datos actualizados (última actualización hace {info['hoursAgo']:.1f} horas)")
        return {
            "updated": False,
            "reason": "not_needed",
            "info": info
        }
    
    # Ejecutar actualización incremental
    if verbose:
        print("📥 Descargando partidos nuevos...")
    
    try:
        result = download_all_matches(
            incremental=True,
            only_played=True
        )
        
        if result is None:
            # No había partidos nuevos
            if verbose:
                print("✅ No hay partidos nuevos")
            return {
                "updated": False,
                "reason": "no_new_matches",
                "info": get_last_update_info()
            }
        
        # Actualización exitosa
        if verbose:
            total = result['metadata']['totalMatches']
            new = result['metadata']['newDownloads']
            print(f"✅ Actualización completada: {new} partidos nuevos (total: {total})")
        
        return {
            "updated": True,
            "newMatches": result['metadata']['newDownloads'],
            "totalMatches": result['metadata']['totalMatches'],
            "info": get_last_update_info()
        }
        
    except Exception as e:
        if verbose:
            print(f"❌ Error en actualización: {e}")
        return {
            "updated": False,
            "reason": "error",
            "error": str(e)
        }


def format_last_update_message(info: dict) -> str:
    """
    Formatea un mensaje legible sobre la última actualización.
    
    Args:
        info: Diccionario con información de última actualización
        
    Returns:
        String formateado para mostrar en UI
    """
    if not info.get('exists'):
        return "⚠️ No hay datos descargados. Ejecuta la primera descarga."
    
    if 'error' in info:
        return f"⚠️ Error leyendo datos: {info['error']}"
    
    last_update = info.get('lastUpdate')
    hours_ago = info.get('hoursAgo', 0)
    total_matches = info.get('totalMatches', 0)
    
    if last_update is None:
        return f"📊 {total_matches} partidos en base de datos"
    
    # Formatear tiempo transcurrido
    if hours_ago < 1:
        time_str = f"{int(hours_ago * 60)} minutos"
    elif hours_ago < 24:
        time_str = f"{int(hours_ago)} horas"
    else:
        days = int(hours_ago / 24)
        time_str = f"{days} día{'s' if days > 1 else ''}"
    
    # Emoji según antigüedad
    if hours_ago < 2:
        emoji = "🟢"
    elif hours_ago < 24:
        emoji = "🟡"
    else:
        emoji = "🔴"
    
    return f"{emoji} {total_matches} partidos | Última actualización: hace {time_str}"


# Ejemplo de uso para Streamlit
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST DE UTILIDADES DE ACTUALIZACIÓN")
    print("="*80)
    
    # Verificar estado actual
    print("\n1. Estado actual:")
    info = get_last_update_info()
    print(format_last_update_message(info))
    
    # Verificar si necesita actualización
    print(f"\n2. ¿Necesita actualización? {needs_update(max_hours=24)}")
    
    # Probar actualización automática
    print("\n3. Intentando actualización automática...")
    result = auto_update_if_needed(max_hours=24, verbose=True)
    print(f"\nResultado: {json.dumps(result, indent=2, default=str)}")
