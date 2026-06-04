import os
import re
import time
import random
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QProgressBar, QMessageBox, QListWidgetItem, 
    QSlider, QStyle, QApplication, QFrame, QScrollArea, QPushButton
)
from PyQt6.QtCore import Qt, QUrl, QSize, QEvent
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from .common import PlaylistWidgetItem
from .tabs.downloads import DownloadsTab
from .tabs.videos import VideosTab
from .tabs.music import MusicTab
from .tabs.streaming import StreamingTab
from downloader import StreamExtractorThread, DownloaderThread
from db import db

class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación Runic Stream.
    Orquesta las diferentes pestañas, la lista de reproducción lateral,
    y actúa como mediador para el reproductor multimedia integrado.
    """
    def __init__(self):
        # 1. Definir dimensiones base de la ventana
        self.base_width = 700
        self.playlist_width = 350
        self._playlist_is_visible = False
        self._internal_resize_lock = False
        
        super().__init__()
        self.setWindowTitle("Runic Stream App")
        
        # 2. Configurar política de tamaño estrictamente fija para evitar redimensiones manuales
        self._enforce_fixed_size()
        
        # 3. Estado interno para descargas en lote (batch)
        self.current_info = None          # Info de la URL actual extraída
        self.batch_queue = []             # Cola de descargas de listas de reproducción
        self.batch_skipped = []           # Elementos saltados (ya existentes o error)
        self.is_batch_downloading = False # Bandera de estado del proceso batch
        self.stop_batch_requested = False # Bandera para detener el lote
        self.batch_total = 0              # Total de elementos en el lote inicial

        # Configuración del reproductor de medios (Video/Audio)
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Conectar señales del reproductor para actualizar los sliders de la UI
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)

        # Inicialización de la interfaz
        self.init_ui()
        # Auto-detectar URLs de YouTube en el portapapeles
        self.check_clipboard_for_url()
        # Cargar los datos desde la base de datos al inicio
        self.load_media_library()
        
        # Señal cuando se cambia de pestaña
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # 4. Instalar filtro de eventos para capturar cualquier intento de redimensión
        self.installEventFilter(self)

    def init_ui(self):
        """Construye y configura todos los widgets de la interfaz principal."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout horizontal principal: [ Pestañas | Panel de Playlist (Oculto por defecto) ]
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        # Bloquear cualquier redimensión automática desde el layout
        self.main_layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetFixedSize)

        # Contenedor principal de pestañas (Tabs Container)
        self.tabs_container = QFrame()
        self.tabs_container.setFixedWidth(self.base_width)
        self.tabs_container.setFixedHeight(600)
        tabs_layout = QVBoxLayout(self.tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)

        # Instanciar las pestañas personalizadas de la aplicación
        self.tabs = QTabWidget()
        self.tab_downloads_widget = DownloadsTab(self)
        self.tab_videos_widget = VideosTab(self)
        self.tab_music_widget = MusicTab(self)
        self.tab_streaming_widget = StreamingTab(self)

        self.tabs.addTab(self.tab_downloads_widget, "Descargas")
        self.tabs.addTab(self.tab_videos_widget, "Mis Videos")
        self.tabs.addTab(self.tab_music_widget, "Mi música") # Corrección de tilde
        self.tabs.addTab(self.tab_streaming_widget, "Streaming")

        tabs_layout.addWidget(self.tabs)
        self.main_layout.addWidget(self.tabs_container)

        # Panel lateral para la Lista de Reproducción (Playlist)
        self.playlist_panel = QFrame()
        self.playlist_panel.setFixedWidth(self.playlist_width)
        self.playlist_panel.setFixedHeight(600)
        self.playlist_panel.setStyleSheet("background-color: #1e1e1e; border-left: 1px solid #333;")
        self.playlist_panel.setVisible(False) # Oculto por defecto

        playlist_layout = QVBoxLayout(self.playlist_panel)
        playlist_title = QLabel("LISTA DE REPRODUCCIÓN")
        playlist_title.setStyleSheet("font-weight: bold; color: #3498db; padding: 10px;")
        playlist_layout.addWidget(playlist_title)

        # Área de scroll para alojar los elementos de la lista de reproducción
        self.playlist_scroll = QScrollArea()
        self.playlist_scroll.setWidgetResizable(True)
        self.playlist_scroll.setStyleSheet("border: none; background: transparent;")
        self.playlist_content = QWidget()
        self.playlist_vbox = QVBoxLayout(self.playlist_content)
        self.playlist_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.playlist_scroll.setWidget(self.playlist_content)

        playlist_layout.addWidget(self.playlist_scroll)
        self.main_layout.addWidget(self.playlist_panel)

    def set_playlist_visible(self, visible):
        """
        Punto de entrada único para cambiar la visibilidad del panel de la playlist
        y redimensionar la ventana completa acordemente.
        """
        if self._playlist_is_visible == visible:
            return
            
        self._playlist_is_visible = visible
        self.playlist_panel.setVisible(visible)
        
        # Bloquear redimensiones externas mientras ajustamos nosotros
        self._internal_resize_lock = True
        self._enforce_fixed_size()
        self._internal_resize_lock = False

    def _enforce_fixed_size(self):
        """Aplica y bloquea el tamaño estático de la ventana dependiendo de los paneles visibles."""
        target_width = self.base_width + (self.playlist_width if self._playlist_is_visible else 0)
        
        # Usamos tanto setFixedSize como los límites individuales para máxima restricción de la UI
        self.setMinimumSize(target_width, 600)
        self.setMaximumSize(target_width, 600)
        self.setFixedSize(target_width, 600)

    def eventFilter(self, obj, event):
        """Filtro de eventos para capturar y anular cualquier redimensión no autorizada por el usuario o SO."""
        if obj is self:
            # Si el evento es un cambio de estado de ventana o redimensión
            if event.type() in [QEvent.Type.Resize, QEvent.Type.WindowStateChange, QEvent.Type.LayoutRequest]:
                # Si no es nuestra propia lógica interna la que lo pide, forzamos el tamaño de nuevo
                if not self._internal_resize_lock:
                    target_width = self.base_width + (self.playlist_width if self._playlist_is_visible else 0)
                    if self.width() != target_width or self.height() != 600:
                        self._enforce_fixed_size()
                        return True # Indicar que hemos manejado el evento
        return super().eventFilter(obj, event)

    def changeEvent(self, event):
        """Captura cambios de foco y estado para re-aplicar el tamaño fijo de forma insistente."""
        super().changeEvent(event)
        if event.type() in [QEvent.Type.ActivationChange, QEvent.Type.FocusOut, QEvent.Type.WindowStateChange]:
            self._enforce_fixed_size()

    # --- Resto de métodos (sin cambios en lógica funcional) ---

    def add_playlist_item(self, title, artist, album, thumb_url):
        """Añade visualmente un elemento al panel lateral de la lista de reproducción."""
        self.playlist_vbox.addWidget(PlaylistWidgetItem(title, artist, album, thumb_url))

    def clear_playlist(self):
        """Limpia todos los elementos de la lista de reproducción del panel lateral."""
        for i in reversed(range(self.playlist_vbox.count())):
            it = self.playlist_vbox.itemAt(i)
            if it and it.widget():
                it.widget().setParent(None)

    def _create_player_controls(self, callback):
        """Crea el conjunto estándar de controles para el reproductor (Play, Barra de progreso, Borrar)."""
        layout = QHBoxLayout()
        
        btn_p = QPushButton("Play/Pause")
        btn_p.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_p.clicked.connect(self.toggle_play)
        
        btn_d = QPushButton("Borrar")
        btn_d.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_d.setStyleSheet("background: #c0392b; color: white;")
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.sliderMoved.connect(self.set_position)
        
        layout.addWidget(btn_p)
        layout.addWidget(slider)
        layout.addWidget(btn_d)
        
        return layout, slider, btn_d

    def check_clipboard_for_url(self):
        """Verifica si en el portapapeles hay una URL válida de YouTube y la pre-carga en la pestaña de descargas."""
        text = QApplication.clipboard().text()
        if text and re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/.*", text) and len(text) < 200:
            self.tab_downloads_widget.url_input.setText(text)

    def on_tab_changed(self, idx):
        """
        Se dispara cuando el usuario cambia de pestaña. 
        Asigna el reproductor de video a la vista correspondiente de la pestaña activa.
        """
        self.load_media_library()
        # Si es la pestaña 1 (Mis Videos) usa su reproductor, si es la 3 (Streaming) usa el de stream, sino Null
        self.player.setVideoOutput(self.tab_videos_widget.video_widget if idx == 1 else (self.tab_streaming_widget.stream_video_widget if idx == 3 else None))

    def set_position(self, p): 
        """Cambia la posición del reproductor multimedia (seek) en ms."""
        self.player.setPosition(p)
    
    def position_changed(self, p):
        """Actualiza la barra de progreso (slider) cuando la posición de reproducción cambia."""
        if self.tabs.currentIndex() == 1:
            if not self.tab_videos_widget.v_slider.isSliderDown():
                self.tab_videos_widget.v_slider.setValue(p)
        elif self.tabs.currentIndex() == 2:
            if not self.tab_music_widget.a_slider.isSliderDown():
                self.tab_music_widget.a_slider.setValue(p)
    
    def duration_changed(self, d):
        """Ajusta el rango de la barra de progreso (slider) basado en la duración total del medio."""
        if self.tabs.currentIndex() == 1: self.tab_videos_widget.v_slider.setRange(0, d)
        elif self.tabs.currentIndex() == 2: self.tab_music_widget.a_slider.setRange(0, d)

    def play_media_file(self, path):
        """Carga y reproduce un archivo multimedia local por su ruta."""
        if path and os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()

    def toggle_play(self):
        """Alterna entre pausa y reproducción."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def load_media_library(self):
        """Sincroniza la BD y recarga las listas locales de Audio y Video."""
        db.sync_library()
        self.tab_videos_widget.load_library()
        self.tab_music_widget.load_library()

    def delete_media(self, mt):
        """
        Borra un elemento de la biblioteca y físicamente (si existe).
        Args:
            mt (str): Tipo de medio ('video' o 'audio').
        """
        tab = self.tab_videos_widget if mt == 'video' else self.tab_music_widget
        listw = tab.video_list if mt == 'video' else tab.music_list
        if listw.currentItem():
            # Extrae el ID guardado en los datos del ítem de la lista
            mid = listw.currentItem().data(Qt.ItemDataRole.UserRole + 1)
            # Confirmación del usuario antes de borrar
            if QMessageBox.question(self, "Confirmar", "¿Borrar este archivo?") == QMessageBox.StandardButton.Yes:
                db.delete_media(mid)
                self.load_media_library()

    def start_batch_download(self, mt, q, e, info, **advanced_opts):
        """
        Inicia el proceso secuencial de descarga en lote (ej. listas de reproducción).
        Configura la cola y comienza el primer elemento.
        """
        self.is_batch_downloading = True
        # Extraer entradas limpiando valores nulos
        self.batch_queue = [x for x in info.get('entries', []) if x]
        self.batch_skipped = []
        self.batch_total = len(self.batch_queue)
        self.advanced_opts = advanced_opts
        
        # Procesar el primer elemento
        self.process_next_batch_item(mt, q, e)

    def process_next_batch_item(self, mt, q, e):
        """
        Lógica iterativa para las descargas por lote. 
        Extrae un elemento de la cola, verifica si ya existe, y dispara su descarga.
        """
        # Si la cola se agotó o se solicitó parar
        if not self.batch_queue or self.stop_batch_requested:
            self.finish_batch_download()
            return
            
        entry = self.batch_queue.pop(0)
        # Buscar URL en las opciones disponibles del diccionario yt-dlp
        url = entry.get('url') or entry.get('webpage_url') or f"https://www.youtube.com/watch?v={entry.get('id','')}"
        
        # Verificar si la URL ya existe en la base de datos
        existing = db.get_media_by_url(url)
        
        # Verificación profunda: comprobamos también si el archivo existe físicamente (normalizando nombres)
        from utils import get_music_dir, get_videos_dir
        base_dir = get_music_dir() if mt == 'audio' else get_videos_dir()
        def normalize(t): return "".join([c for c in t if c.isalnum()]).lower()
        target = normalize(entry.get('title', '???'))
        phys_exists = False
        if target:
            # Caminar por los subdirectorios para buscar coincidencias
            for r, d, fs in os.walk(base_dir):
                if any(target in normalize(f) for f in fs):
                    phys_exists = True
                    break
        
        # Prevenir repeticiones verificando en DB o sistema de archivos
        if (mt == 'video' and (any(i['quality'] == q for i in existing) or phys_exists)) or (mt == 'audio' and (any(i['type'] == 'audio' for i in existing) or phys_exists)):
            self.batch_skipped.append((entry.get('title', '...'), "Ya se encuentra en la biblioteca o disco"))
            # Saltar al siguiente ítem inmediatamente
            self.process_next_batch_item(mt, q, e)
            return
        
        # Actualizar vista previa en la UI para el ítem actual del lote
        self.tab_downloads_widget.set_preview_info(entry)
        
        # Actualizar estado de descarga (x de Y elementos)
        self.tab_downloads_widget.lbl_status.setText(f"Descargando {self.batch_total - len(self.batch_queue)}/{self.batch_total}: {entry.get('title','...')}")
        self.tab_downloads_widget.progress_bar.setVisible(True)
        self.tab_downloads_widget.progress_bar.setValue(0)
        
        # Construir ID del formato para yt-dlp 
        height = q[:-1] if q.endswith('p') else q
        f_id = f"bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/best[height={height}][ext=mp4]" if mt == 'video' else 'bestaudio'
        
        # Iniciar el hilo del descargador para el ítem individual
        self.downloader_thread = DownloaderThread(url, f_id, mt, q, e, **self.advanced_opts)
        self.downloader_thread.progress.connect(lambda v: self.tab_downloads_widget.progress_bar.setValue(int(v)))
        self.downloader_thread.finished.connect(lambda t, f, m, q: self.on_batch_item_finished(t, f, m, q, url, mt, q, e))
        self.downloader_thread.error.connect(lambda err: self.on_batch_item_error(entry.get('title', '...'), mt, q, e, err))
        self.downloader_thread.start()

    def on_batch_item_error(self, title, mt, q, e, error):
        """Callback cuando falla un elemento de la descarga en lote."""
        self.batch_skipped.append((title, f"Error de descarga: {error}"))
        self.process_next_batch_item(mt, q, e)

    def on_batch_item_finished(self, t, fp, m, q, url, om, oq, oe):
        """Callback cuando finaliza exitosamente un elemento de la descarga en lote."""
        if fp: 
            # Guardamos el registro en base de datos
            db.add_media(t, m, fp, url, q)
        # Pequeña pausa artificial para no saturar y ser banneado
        time.sleep(random.uniform(0.5, 1.2))
        self.process_next_batch_item(om, oq, oe)

    def finish_batch_download(self):
        """Finaliza el ciclo completo de descargas en lote y muestra un resumen si es necesario."""
        self.is_batch_downloading = False
        self.tab_downloads_widget.btn_stop_batch.setVisible(False)
        self.load_media_library()
        
        # Muestra resultados de elementos que fallaron o se saltaron
        if self.batch_skipped:
            msg = "Resumen de la descarga:\n\n"
            for title, reason in self.batch_skipped:
                msg += f"• {title}: {reason}\n"
            QMessageBox.information(self, "Terminado", msg)
            
        # Restablece la UI de la pestaña de descargas
        self.tab_downloads_widget.on_download_finished(None, None, None, None, None)

    def on_stream_clicked(self):
        """Inicia el proceso para extraer y reproducir un stream de video en directo."""
        url = self.tab_streaming_widget.stream_input.text().strip()
        if not url: return
        
        self.tab_streaming_widget.btn_stream.setEnabled(False)
        # Hilo independiente para extraer la URL directa
        self.stream_extractor_thread = StreamExtractorThread(url)
        self.stream_extractor_thread.finished.connect(self.on_stream_extraction_finished)
        self.stream_extractor_thread.error.connect(self.on_stream_extraction_error)
        self.stream_extractor_thread.start()

    def on_stream_extraction_finished(self, url):
        """Callback cuando se extrae la URL directa del stream, lo pasa al reproductor."""
        self.tab_streaming_widget.btn_stream.setEnabled(True)
        self.player.setVideoOutput(self.tab_streaming_widget.stream_video_widget)
        self.player.setSource(QUrl(url))
        self.player.play()

    def on_stream_extraction_error(self, e):
        """Callback cuando ocurre un error extrayendo la URL del stream."""
        self.tab_streaming_widget.btn_stream.setEnabled(True)
        QMessageBox.critical(self, "Error", str(e))
