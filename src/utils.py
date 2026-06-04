import os
from pathlib import Path
import sys

def get_base_dir():
    """Returns the base directory for the application data."""
    home = Path.home()
    if sys.platform == "win32":
        return home
    elif sys.platform == "darwin":
        return home
    else:
        # Linux and other Unix-like systems
        # Could use xdg-user-dirs, but standard fallback is simple
        return home

def get_videos_dir() -> Path:
    """Returns the path to the RunicVideos directory, creating it if necessary."""
    base = get_base_dir()
    
    # Simple fallback heuristic for standard folders
    if (base / "Videos").exists():
        videos_dir = base / "Videos" / "RunicVideos"
    elif (base / "Vídeos").exists(): # Spanish localization
        videos_dir = base / "Vídeos" / "RunicVideos"
    else:
        videos_dir = base / "RunicVideos"
        
    videos_dir.mkdir(parents=True, exist_ok=True)
    return videos_dir

def get_music_dir() -> Path:
    """Returns the path to the RunicMusic directory, creating it if necessary."""
    base = get_base_dir()
    
    # Simple fallback heuristic for standard folders
    if (base / "Music").exists():
        music_dir = base / "Music" / "RunicMusic"
    elif (base / "Música").exists(): # Spanish localization
        music_dir = base / "Música" / "RunicMusic"
    else:
        music_dir = base / "RunicMusic"
        
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir
