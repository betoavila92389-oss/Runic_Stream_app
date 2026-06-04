import os
from pathlib import Path
import sys

def get_base_dir():
    """
    Devuelve el directorio base para los datos de la aplicación.
    Dependiendo del sistema operativo, determina la carpeta del usuario.
    """
    # Obtiene la ruta del directorio 'home' del usuario actual
    home = Path.home()
    if sys.platform == "win32":
        # En Windows, usamos el directorio home
        return home
    elif sys.platform == "darwin":
        # En macOS (Darwin), también usamos el directorio home
        return home
    else:
        # En Linux y otros sistemas tipo Unix
        # Podríamos usar xdg-user-dirs, pero el respaldo estándar es simple y funciona
        return home

def get_videos_dir() -> Path:
    """
    Devuelve la ruta al directorio RunicVideos, creándolo si es necesario.
    Busca carpetas de vídeos estándar dependiendo del idioma del sistema.
    """
    base = get_base_dir()
    
    # Heurística de respaldo simple para carpetas estándar
    if (base / "Videos").exists():
        # Si existe la carpeta "Videos" (en inglés), crea RunicVideos ahí
        videos_dir = base / "Videos" / "RunicVideos"
    elif (base / "Vídeos").exists(): 
        # Si existe la carpeta "Vídeos" (localización en español), úsala
        videos_dir = base / "Vídeos" / "RunicVideos"
    else:
        # Si no se encuentra ninguna, crea la carpeta en el directorio base
        videos_dir = base / "RunicVideos"
        
    # Crea el directorio y todos los directorios padres si no existen
    videos_dir.mkdir(parents=True, exist_ok=True)
    return videos_dir

def get_music_dir() -> Path:
    """
    Devuelve la ruta al directorio RunicMusic, creándolo si es necesario.
    Busca carpetas de música estándar dependiendo del idioma del sistema.
    """
    base = get_base_dir()
    
    # Heurística de respaldo simple para carpetas estándar
    if (base / "Music").exists():
        # Si existe la carpeta "Music" (en inglés), crea RunicMusic ahí
        music_dir = base / "Music" / "RunicMusic"
    elif (base / "Música").exists(): 
        # Si existe la carpeta "Música" (localización en español), úsala
        music_dir = base / "Música" / "RunicMusic"
    else:
        # Si no se encuentra ninguna, crea la carpeta en el directorio base
        music_dir = base / "RunicMusic"
        
    # Crea el directorio y todos los directorios padres si no existen
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir
