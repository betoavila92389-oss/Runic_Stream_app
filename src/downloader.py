import yt_dlp
from PyQt6.QtCore import QThread, pyqtSignal
from utils import get_videos_dir, get_music_dir
import os
import logging
import glob
import time
import re
import urllib.request
from urllib.parse import urlparse, parse_qs
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
from mutagen.mp3 import MP3

# Configurar logging detallado
logging.basicConfig(
    filename='downloader_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a' 
)
logger = logging.getLogger(__name__)

class YDLLogger:
    def debug(self, msg):
        if msg.startswith('[debug] '):
            logger.debug(msg)
        else:
            self.info(msg)
    def info(self, msg):
        logger.info(msg)
        print(msg) 
    def warning(self, msg):
        logger.warning(msg)
        print(f"AVISO: {msg}")
    def error(self, msg):
        logger.error(msg)
        print(f"ERROR: {msg}")

class ExtractorThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, cookies_from_browser=None, username=None, password=None, proxy=None):
        super().__init__()
        self.url = self._purify_url(url)
        self.cookies_from_browser = cookies_from_browser
        self.username = username
        self.password = password
        self.proxy = proxy

    def _purify_url(self, url):
        """Purificación extrema: Extraer ID y crear URL de YouTube pura."""
        try:
            patterns = [r'(?:v=|\/v\/|youtu\.be\/|embed\/|watch\?v=)([^#\&\?]{11})']
            for p in patterns:
                match = re.search(p, url)
                if match:
                    video_id = match.group(1)
                    clean_url = f"https://www.youtube.com/watch?v={video_id}"
                    if "music.youtube.com" in url:
                        print(f"[SISTEMA] Music URL purificada -> {video_id}")
                    return clean_url
        except Exception: pass
        return url

    def run(self):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'playlist_items': '1-500',
        }
        if self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        if self.username:
            ydl_opts['username'] = self.username
        if self.password:
            ydl_opts['password'] = self.password
        if self.proxy:
            ydl_opts['proxy'] = self.proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if info:
                    self.finished.emit(info)
                else:
                    self.error.emit("No se pudo extraer la información del video. Verifique el link o sus opciones avanzadas.")
        except Exception as e:
            print(f"[ERROR] Error en el proceso: {str(e)}")
            self.error.emit(str(e))

class StreamExtractorThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        ydl_opts = {'quiet': True, 'format': 'best'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    self.error.emit("No se pudo obtener la información de streaming.")
                    return
                stream_url = info.get('url')
                if stream_url: self.finished.emit(stream_url)
                else: self.error.emit("Enlace de streaming no encontrado.")
        except Exception as e:
            print(f"[ERROR] Error en el proceso: {str(e)}")
            self.error.emit(str(e))

class DownloaderThread(QThread):
    progress = pyqtSignal(float)
    finished = pyqtSignal(str, str, str, str) 
    error = pyqtSignal(str)

    def __init__(self, url, format_id, media_type, quality=None, extension='mp4', cookies_from_browser=None, username=None, password=None, proxy=None):
        super().__init__()
        self.url = self._purify_url(url)
        self.format_id = format_id
        self.media_type = media_type
        self.quality = quality
        self.extension = extension
        self.cookies_from_browser = cookies_from_browser
        self.username = username
        self.password = password
        self.proxy = proxy

    def _purify_url(self, url):
        try:
            patterns = [r'(?:v=|\/v\/|youtu\.be\/|embed\/|watch\?v=)([^#\&\?]{11})']
            for p in patterns:
                match = re.search(p, url)
                if match:
                    return f"https://www.youtube.com/watch?v={match.group(1)}"
        except Exception: pass
        return url

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0: self.progress.emit((downloaded / total) * 100)
            except: pass
        elif d['status'] == 'finished':
            self.progress.emit(100.0)

    def run(self):
        output_dir = get_music_dir() if self.media_type == 'audio' else get_videos_dir()
        logger.debug(f"--- INICIO PROCESO MP3 --- | URL: {self.url}")
        
        prefix = f"({self.quality})_" if (self.quality and self.media_type == 'video') else ""

        # Opciones base para yt-dlp
        ydl_opts = {
            'outtmpl': os.path.join(output_dir, f'{prefix}%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'logger': YDLLogger(), 
            'writethumbnail': self.media_type == 'video', 
            'keepvideo': False,
            'nopostoverwrites': False,
            'no_cache_dir': True,
            'restrictfilenames': True,
        }

        if self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        if self.username:
            ydl_opts['username'] = self.username
        if self.password:
            ydl_opts['password'] = self.password
        if self.proxy:
            ydl_opts['proxy'] = self.proxy

        # Configuración específica según tipo de medio
        if self.media_type == 'video':
            ydl_opts['format'] = self.format_id or 'best'
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegVideoConvertor', 'preferedformat': self.extension},
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
                {'key': 'FFmpegMetadata', 'add_metadata': True},
                {'key': 'EmbedThumbnail'}, 
            ]
        else:
            # PARA AUDIO: MP3 con inyección manual vía mutagen para evitar fallos de FFmpeg
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                },
                {'key': 'FFmpegMetadata', 'add_metadata': True},
            ]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if not info:
                    self.error.emit("No se pudo descargar el video. Verifique el link o sus opciones avanzadas.")
                    return
                
                title = info.get('title', 'Unknown')
                video_id = info.get('id')
                
                file_path = None
                if 'requested_downloads' in info and info['requested_downloads']:
                    file_path = info['requested_downloads'][0]['filepath']
                else:
                    # Fallback si falla la detección automática
                    ext = self.extension if self.media_type == 'video' else 'mp3'
                    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                    file_path = os.path.join(output_dir, f"{prefix}{clean_title}.{ext}")

                # Inyección manual de carátula y metadatos para Audio
                if self.media_type == 'audio' and video_id:
                    try:
                        logger.debug(f"Iniciando inyección manual de metadatos y carátula para ID: {video_id}")
                        url_img = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                        temp_img = os.path.join(output_dir, f"temp_thumb_{video_id}.jpg")
                        
                        # Descargar imagen
                        urllib.request.urlretrieve(url_img, temp_img)
                        
                        # Inyectar con Mutagen
                        audio = MP3(file_path, ID3=ID3)
                        if audio.tags is None:
                            audio.add_tags()
                        
                        # Metadatos principales
                        artist = info.get('uploader') or info.get('artist') or 'Unknown Artist'
                        album = info.get('album')
                        if not album:
                            album = str(info.get('release_year') or (info.get('upload_date')[:4] if info.get('upload_date') else 'Unknown Album'))
                        
                        audio.tags.add(TIT2(encoding=3, text=title))
                        audio.tags.add(TPE1(encoding=3, text=artist))
                        audio.tags.add(TALB(encoding=3, text=album))
                        
                        with open(temp_img, 'rb') as img:
                            audio.tags.add(
                                APIC(
                                    encoding=3,
                                    mime='image/jpeg',
                                    type=3,
                                    desc=u'Cover',
                                    data=img.read()
                                )
                            )
                        audio.save(v2_version=3)
                        
                        # Limpiar
                        if os.path.exists(temp_img):
                            os.remove(temp_img)
                        logger.info("Inyección manual de metadatos y carátula completada con éxito.")
                    except Exception as e_img:
                        logger.error(f"Error en inyección manual de metadatos/carátula: {str(e_img)}")

                # Formato MP3 con metadatos y carátula compatible
                msg_final = f"Audio guardado en formato MP3 con carátula manual: {os.path.basename(file_path)}"
                logger.info(msg_final)
                print(f"[ÉXITO] {msg_final}")

                self.finished.emit(title, file_path, self.media_type, self.quality or "N/A")
        except Exception as e:
            logger.error(f"Error en la descarga: {str(e)}", exc_info=True)
            print(f"[ERROR] Descarga fallida: {str(e)}")
            self.error.emit(str(e))
