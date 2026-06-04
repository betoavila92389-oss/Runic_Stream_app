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

# Configurar logging detallado para propósitos de depuración del proceso de descarga
logging.basicConfig(
    filename='downloader_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a' 
)
logger = logging.getLogger(__name__)

class YDLLogger:
    """
    Clase de registro personalizada para yt-dlp.
    Captura y redirige los mensajes de debug, información, advertencias y errores
    generados por yt-dlp hacia el sistema de logging estándar de Python.
    """
    def debug(self, msg):
        # Filtramos los mensajes de depuración reales y evitamos ruido excesivo
        if msg.startswith('[debug] '):
            logger.debug(msg)
        else:
            self.info(msg)
            
    def info(self, msg):
        # Registramos mensajes de información general
        logger.info(msg)
        print(msg) 
        
    def warning(self, msg):
        # Registramos advertencias
        logger.warning(msg)
        print(f"AVISO: {msg}")
        
    def error(self, msg):
        # Registramos errores críticos
        logger.error(msg)
        print(f"ERROR: {msg}")

class ExtractorThread(QThread):
    """
    Hilo asíncrono para extraer la información de un enlace multimedia.
    Utiliza QThread de PyQt para no bloquear la interfaz de usuario mientras
    yt-dlp consulta la información de la URL.
    """
    # Señales para comunicar resultados al hilo principal (UI)
    finished = pyqtSignal(dict)  # Emite el diccionario con la información si tiene éxito
    error = pyqtSignal(str)      # Emite un mensaje de error en caso de fallo

    def __init__(self, url, cookies_from_browser=None, username=None, password=None, proxy=None):
        """
        Inicializa el hilo de extracción.
        
        Args:
            url (str): Enlace del video/audio.
            cookies_from_browser (str, opcional): Navegador del cual extraer cookies.
            username (str, opcional): Nombre de usuario para autenticación.
            password (str, opcional): Contraseña para autenticación.
            proxy (str, opcional): Proxy a utilizar para la conexión.
        """
        super().__init__()
        # Purificamos la URL antes de procesarla para evitar errores comunes
        self.url = self._purify_url(url)
        self.cookies_from_browser = cookies_from_browser
        self.username = username
        self.password = password
        self.proxy = proxy

    def _purify_url(self, url):
        """
        Limpia y estandariza la URL de YouTube.
        Extrae el ID del video y crea una URL canónica para evitar problemas con
        listas de reproducción, marcas de tiempo u otros parámetros de seguimiento.
        """
        try:
            # Patrones regulares para capturar el ID de video de YouTube (11 caracteres)
            patterns = [r'(?:v=|\/v\/|youtu\.be\/|embed\/|watch\?v=)([^#\&\?]{11})']
            for p in patterns:
                match = re.search(p, url)
                if match:
                    video_id = match.group(1)
                    clean_url = f"https://www.youtube.com/watch?v={video_id}"
                    # Informar si se purificó un enlace de YouTube Music
                    if "music.youtube.com" in url:
                        print(f"[SISTEMA] Music URL purificada -> {video_id}")
                    return clean_url
        except Exception: 
            pass
        # Si no coincide con ningún patrón o falla, devuelve la URL original
        return url

    def run(self):
        """
        Método principal ejecutado en el hilo asíncrono.
        Configura yt-dlp e intenta extraer metadatos sin descargar el archivo.
        """
        # Opciones para yt-dlp: no descargar, ignorar errores menores, limitar listas de reproducción
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'playlist_items': '1-500',
        }
        
        # Agregamos parámetros de autenticación si se proporcionaron
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
                # download=False asegura que solo extraemos información (metadatos)
                info = ydl.extract_info(self.url, download=False)
                if info:
                    self.finished.emit(info)
                else:
                    self.error.emit("No se pudo extraer la información del video. Verifique el link o sus opciones avanzadas.")
        except Exception as e:
            print(f"[ERROR] Error en el proceso: {str(e)}")
            self.error.emit(str(e))


class StreamExtractorThread(QThread):
    """
    Hilo asíncrono dedicado exclusivamente a obtener el enlace directo
    (URL del stream) necesario para reproducir contenido en la aplicación.
    """
    finished = pyqtSignal(str)   # Emite la URL directa para streaming
    error = pyqtSignal(str)      # Emite un mensaje de error si falla

    def __init__(self, url):
        """
        Inicializa el hilo de extracción de stream.
        
        Args:
            url (str): Enlace original de la plataforma multimedia.
        """
        super().__init__()
        self.url = url

    def run(self):
        """
        Obtiene el enlace directo de mayor calidad posible para streaming.
        """
        # 'format': 'best' intenta obtener el mejor stream combinado de audio y video
        ydl_opts = {'quiet': True, 'format': 'best'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    self.error.emit("No se pudo obtener la información de streaming.")
                    return
                stream_url = info.get('url')
                if stream_url: 
                    self.finished.emit(stream_url)
                else: 
                    self.error.emit("Enlace de streaming no encontrado.")
        except Exception as e:
            print(f"[ERROR] Error en el proceso: {str(e)}")
            self.error.emit(str(e))


class DownloaderThread(QThread):
    """
    Hilo asíncrono responsable de descargar y procesar archivos multimedia.
    Maneja el seguimiento del progreso de la descarga, la conversión de formatos
    utilizando FFmpeg y la inyección manual de metadatos (especialmente en MP3).
    """
    # Señales para actualizar la UI durante y después del proceso
    progress = pyqtSignal(float)                     # Emite el progreso (0-100)
    finished = pyqtSignal(str, str, str, str)        # Emite: título, ruta_archivo, tipo_medio, calidad
    error = pyqtSignal(str)                          # Emite mensaje de error

    def __init__(self, url, format_id, media_type, quality=None, extension='mp4', cookies_from_browser=None, username=None, password=None, proxy=None):
        """
        Inicializa el hilo de descarga.
        
        Args:
            url (str): URL del contenido a descargar.
            format_id (str): ID del formato específico a solicitar a yt-dlp.
            media_type (str): Tipo de archivo ('video' o 'audio').
            quality (str, opcional): Cadena descriptiva de la calidad (ej: '1080p').
            extension (str): Extensión de archivo deseada para video (por defecto 'mp4').
            cookies_from_browser (str, opcional): Navegador del cual extraer cookies.
            username (str, opcional): Nombre de usuario para autenticación.
            password (str, opcional): Contraseña para autenticación.
            proxy (str, opcional): Proxy a utilizar para la conexión.
        """
        super().__init__()
        # Estandarizamos la URL antes de iniciar
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
        """
        Limpia y estandariza la URL (ver lógica idéntica en ExtractorThread).
        """
        try:
            patterns = [r'(?:v=|\/v\/|youtu\.be\/|embed\/|watch\?v=)([^#\&\?]{11})']
            for p in patterns:
                match = re.search(p, url)
                if match:
                    return f"https://www.youtube.com/watch?v={match.group(1)}"
        except Exception: pass
        return url

    def progress_hook(self, d):
        """
        Función callback invocada por yt-dlp para informar el estado de descarga.
        Calcula el porcentaje de progreso y lo emite para actualizar la UI.
        
        Args:
            d (dict): Diccionario con el estado actual de la descarga.
        """
        if d['status'] == 'downloading':
            try:
                # Intenta obtener los bytes descargados y totales
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0: 
                    # Emite el progreso en formato de porcentaje (0.0 a 100.0)
                    self.progress.emit((downloaded / total) * 100)
            except: 
                pass
        elif d['status'] == 'finished':
            # Asegura que la barra de progreso llegue al 100% al finalizar
            self.progress.emit(100.0)

    def run(self):
        """
        Ejecuta la lógica de descarga y post-procesamiento.
        Define rutas, configuraciones de FFmpeg y realiza la descarga con yt-dlp.
        """
        # Selecciona el directorio destino según el tipo de medio
        output_dir = get_music_dir() if self.media_type == 'audio' else get_videos_dir()
        logger.debug(f"--- INICIO PROCESO MP3 --- | URL: {self.url}")
        
        # Añade la calidad como prefijo para archivos de video si está disponible
        prefix = f"({self.quality})_" if (self.quality and self.media_type == 'video') else ""

        # Opciones base requeridas para todas las descargas mediante yt-dlp
        ydl_opts = {
            # Plantilla para el nombre del archivo final
            'outtmpl': os.path.join(output_dir, f'{prefix}%(title)s.%(ext)s'),
            # Hook para monitorear el progreso
            'progress_hooks': [self.progress_hook],
            'logger': YDLLogger(), 
            # Escribimos miniatura para los videos
            'writethumbnail': self.media_type == 'video', 
            'keepvideo': False,
            'nopostoverwrites': False,
            'no_cache_dir': True,
            # Restringe los nombres a caracteres compatibles
            'restrictfilenames': True,
        }

        # Aplica configuraciones opcionales de autenticación o conexión
        if self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        if self.username:
            ydl_opts['username'] = self.username
        if self.password:
            ydl_opts['password'] = self.password
        if self.proxy:
            ydl_opts['proxy'] = self.proxy

        # Configuración específica para post-procesamiento según tipo de medio
        if self.media_type == 'video':
            # Para video: descargar formato solicitado y usar FFmpeg para asegurar compatibilidad
            ydl_opts['format'] = self.format_id or 'best'
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegVideoConvertor', 'preferedformat': self.extension}, # Conversión a mp4/mkv
                {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},             # Conversión de carátula a JPG
                {'key': 'FFmpegMetadata', 'add_metadata': True},                   # Metadatos del video
                {'key': 'EmbedThumbnail'},                                         # Incrustar miniatura
            ]
        else:
            # Para audio: solicitar mejor calidad de audio, extraer a MP3 y añadir metadatos
            # IMPORTANTE: Se inyecta la carátula manualmente vía mutagen para evitar fallos comunes de FFmpeg
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
                # Iniciamos la descarga (download=True)
                info = ydl.extract_info(self.url, download=True)
                if not info:
                    self.error.emit("No se pudo descargar el video. Verifique el link o sus opciones avanzadas.")
                    return
                
                # Obtenemos información vital para nombrar y etiquetar el archivo
                title = info.get('title', 'Unknown')
                video_id = info.get('id')
                
                # Determinamos la ruta del archivo final
                file_path = None
                if 'requested_downloads' in info and info['requested_downloads']:
                    # Generalmente la ruta exacta viene informada aquí
                    file_path = info['requested_downloads'][0]['filepath']
                else:
                    # En caso contrario, creamos un nombre de archivo purificado (fallback)
                    ext = self.extension if self.media_type == 'video' else 'mp3'
                    clean_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                    file_path = os.path.join(output_dir, f"{prefix}{clean_title}.{ext}")

                # Inyección manual de carátula y metadatos para archivos de Audio (MP3)
                if self.media_type == 'audio' and video_id:
                    try:
                        logger.debug(f"Iniciando inyección manual de metadatos y carátula para ID: {video_id}")
                        # Intentamos obtener la miniatura de alta calidad (hqdefault) de YouTube
                        url_img = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                        temp_img = os.path.join(output_dir, f"temp_thumb_{video_id}.jpg")
                        
                        # Descargamos la imagen de forma temporal
                        urllib.request.urlretrieve(url_img, temp_img)
                        
                        # Cargamos el archivo MP3 con Mutagen
                        audio = MP3(file_path, ID3=ID3)
                        if audio.tags is None:
                            audio.add_tags()
                        
                        # Extracción de metadatos básicos (artista y álbum)
                        artist = info.get('uploader') or info.get('artist') or 'Unknown Artist'
                        album = info.get('album')
                        if not album:
                            # Si no hay álbum, intentar usar el año o fecha de subida
                            album = str(info.get('release_year') or (info.get('upload_date')[:4] if info.get('upload_date') else 'Unknown Album'))
                        
                        # Añadimos Título, Artista y Álbum usando etiquetas ID3 (TIT2, TPE1, TALB)
                        audio.tags.add(TIT2(encoding=3, text=title))
                        audio.tags.add(TPE1(encoding=3, text=artist))
                        audio.tags.add(TALB(encoding=3, text=album))
                        
                        # Incrustamos la carátula descargada
                        with open(temp_img, 'rb') as img:
                            audio.tags.add(
                                APIC(
                                    encoding=3,            # UTF-8
                                    mime='image/jpeg',     # Formato de imagen
                                    type=3,                # Tipo 'Cover (front)'
                                    desc=u'Cover',
                                    data=img.read()
                                )
                            )
                        # Guardamos los cambios forzando compatibilidad de ID3v2.3 (más soportada)
                        audio.save(v2_version=3)
                        
                        # Eliminamos la imagen temporal
                        if os.path.exists(temp_img):
                            os.remove(temp_img)
                        logger.info("Inyección manual de metadatos y carátula completada con éxito.")
                    except Exception as e_img:
                        # Un fallo en la inyección no debería interrumpir o fallar toda la descarga
                        logger.error(f"Error en inyección manual de metadatos/carátula: {str(e_img)}")

                msg_final = f"Archivo guardado correctamente: {os.path.basename(file_path)}"
                logger.info(msg_final)
                print(f"[ÉXITO] {msg_final}")

                # Emitimos la señal de finalización con los detalles de la descarga exitosa
                self.finished.emit(title, file_path, self.media_type, self.quality or "N/A")
        except Exception as e:
            # Capturamos y emitimos cualquier error durante la inicialización o descarga
            logger.error(f"Error en la descarga: {str(e)}", exc_info=True)
            print(f"[ERROR] Descarga fallida: {str(e)}")
            self.error.emit(str(e))
