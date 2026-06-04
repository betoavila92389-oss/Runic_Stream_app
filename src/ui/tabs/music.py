import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QSlider, QLabel, QTreeWidget, QTreeWidgetItem, 
                             QStackedWidget, QComboBox, QFrame, QTreeWidgetItemIterator, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QShortcut, QKeySequence
from PyQt6.QtMultimedia import QMediaPlayer
from utils import get_music_dir
from mutagen import File
import random

def extract_metadata(file_path):
    """
    Función de utilidad para extraer metadatos embebidos en archivos de audio (ID3/MP4 tags).
    Intenta extraer el título, artista, álbum y carátula.
    
    Args:
        file_path (str): Ruta al archivo de audio.
        
    Returns:
        dict: Diccionario que contiene las claves 'title', 'artist', 'album', 'cover', 'path'.
    """
    metadata = {
        'title': os.path.basename(file_path),
        'artist': 'Artista Desconocido',
        'album': 'Álbum Desconocido',
        'cover': None,
        'path': file_path
    }
    try:
        audio = File(file_path)
        if audio is not None and audio.tags:
            # Extracción del Título (TIT2 en ID3, ©nam en mp4/m4a)
            if 'TIT2' in audio.tags: metadata['title'] = str(audio.tags['TIT2'])
            elif '©nam' in audio.tags: metadata['title'] = str(audio.tags['©nam'][0])
                
            # Extracción del Artista (TPE1 en ID3, ©ART en mp4/m4a)
            if 'TPE1' in audio.tags: metadata['artist'] = str(audio.tags['TPE1'])
            elif '©ART' in audio.tags: metadata['artist'] = str(audio.tags['©ART'][0])
                
            # Extracción del Álbum (TALB en ID3, ©alb en mp4/m4a)
            if 'TALB' in audio.tags: metadata['album'] = str(audio.tags['TALB'])
            elif '©alb' in audio.tags: metadata['album'] = str(audio.tags['©alb'][0])
                
            # Buscar la carátula (Album Art) incrustada
            for tag in audio.tags.values():
                if tag.__class__.__name__ == 'APIC':
                    # Etiqueta estándar de imagen en ID3 (MP3)
                    metadata['cover'] = tag.data
                    break
                elif hasattr(tag, 'data') and isinstance(tag.data, bytes) and tag.data.startswith(b'\xff\xd8'):
                    # Si comienza con la firma en bytes de JPG
                    metadata['cover'] = tag.data
                    break
            # Caso para archivos de Apple (m4a)
            if not metadata['cover'] and hasattr(audio, 'tags') and 'covr' in audio.tags:
                metadata['cover'] = audio.tags['covr'][0]
    except Exception:
        # Falla silenciosamente; se usará la información por defecto generada
        pass
    return metadata

class ClickableSlider(QSlider):
    """
    Slider extendido (barra de progreso) que permite cliquear en cualquier parte 
    de la pista para avanzar o retroceder (seek) instantáneamente.
    """
    seekRequested = pyqtSignal(int)
    
    def mousePressEvent(self, event):
        """Maneja el evento de click primario, saltando directamente a la posición."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            val = int(self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / self.width())
            val = max(self.minimum(), min(self.maximum(), val))
            self.setValue(val)
            self.seekRequested.emit(val)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Maneja el arrastre del slider."""
        if self.isSliderDown():
            val = int(self.minimum() + (self.maximum() - self.minimum()) * event.position().x() / self.width())
            val = max(self.minimum(), min(self.maximum(), val))
            self.setValue(val)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Libera el slider y finaliza el seek."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(False)
            self.seekRequested.emit(self.value())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Soporte para teclado (Flecha izquierda/derecha para saltar tiempo)."""
        super().keyPressEvent(event)
        # Emite señal de seek cuando se manipula mediante teclado
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.seekRequested.emit(self.value())

class MusicTab(QWidget):
    """
    Pestaña especializada en el escaneo, categorización y reproducción
    completa de contenido de Audio descargado. Es el equivalente a un
    reproductor de MP3 completo interno.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        # Control del estado de la playlist activa
        self.current_playlist = []
        self.current_index = -1
        # Opciones de reproducción continua
        self.repeat_mode = 0 # 0: Nada, 1: Toda la lista, 2: Solo una pista
        self.shuffle_mode = False # Modo aleatorio
        self.all_songs = []
        
        self.init_ui()
        
        # Suscripción a eventos del reproductor central
        self.main_window.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.main_window.player.playingChanged.connect(self.on_playing_changed)

    def init_ui(self):
        """Distribuye la interfaz dividiendo entre Panel de Reproducción (Izq) y Biblioteca (Der)."""
        main_layout = QHBoxLayout(self)
        
        # --- PANEL IZQUIERDO (Reproductor y controles) ---
        left_pane = QFrame()
        left_pane.setFixedWidth(320)
        left_pane.setStyleSheet("background-color: #181818; border-radius: 10px;")
        left_layout = QVBoxLayout(left_pane)
        
        # Carátula del álbum
        self.cover_label = QLabel()
        self.cover_label.setFixedHeight(280)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #282828; border-radius: 10px;")
        left_layout.addWidget(self.cover_label)
        
        # Metadata del reproductor
        self.lbl_title = QLabel("Título de la canción")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 16px; color: white;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setWordWrap(True)
        left_layout.addWidget(self.lbl_title)
        
        self.lbl_artist = QLabel("Artista - Álbum")
        self.lbl_artist.setStyleSheet("color: #b3b3b3;")
        self.lbl_artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_artist.setWordWrap(True)
        left_layout.addWidget(self.lbl_artist)
        
        # Espaciador empujará los controles a la base y la carátula hacia arriba, 
        # impidiendo que se muevan cuando el texto cambia o hace un wrap.
        left_layout.addStretch()
        
        # Barra de progreso principal
        self.a_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.a_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.a_slider.seekRequested.connect(self.main_window.set_position)
        left_layout.addWidget(self.a_slider)
        
        # Botonera de control
        controls_layout = QHBoxLayout()
        
        self.btn_shuffle = QPushButton("🔀")
        self.btn_shuffle.setToolTip("Aleatorio: Desactivado")
        self.btn_shuffle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_shuffle.clicked.connect(self.toggle_shuffle)
        
        self.btn_repeat = QPushButton("🔁")
        self.btn_repeat.setToolTip("Repetir: Desactivado")
        self.btn_repeat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_repeat.clicked.connect(self.toggle_repeat)
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self.play_previous)
        
        self.btn_play = QPushButton("▶️")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self.main_window.toggle_play)
        
        self.btn_next = QPushButton("⏭")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.play_next)
        
        controls_layout.addWidget(self.btn_shuffle)
        controls_layout.addWidget(self.btn_repeat)
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_next)
        left_layout.addLayout(controls_layout)
        
        # Control de Volumen (con icono simulado)
        vol_layout = QHBoxLayout()
        vol_lbl = QLabel("🔊")
        vol_lbl.setStyleSheet("color: white;")
        vol_layout.addWidget(vol_lbl)
        self.vol_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(self.main_window.audio_output.volume() * 100))
        self.vol_slider.valueChanged.connect(lambda v: self.main_window.audio_output.setVolume(v / 100.0))
        vol_layout.addWidget(self.vol_slider)
        left_layout.addLayout(vol_layout)
        
        # --- PANEL DERECHO (Biblioteca explorador local) ---
        right_pane = QWidget()
        right_layout = QVBoxLayout(right_pane)
        
        # Barra de búsqueda
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por canción o artista...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.build_tree)
        right_layout.addWidget(self.search_input)
        
        # Selector de ordenamiento visual
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Ordenar y Agrupar por:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Artista y Álbum", "Nombre", "Álbum"])
        self.sort_combo.currentIndexChanged.connect(self.build_tree)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        right_layout.addLayout(sort_layout)
        
        # Componente TreeView para agrupar jerárquicamente canciones
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Biblioteca de Música Descargada"])
        self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        right_layout.addWidget(self.tree_widget)
        
        main_layout.addWidget(left_pane)
        main_layout.addWidget(right_pane, 1)
        
        # Configurar aspecto inicial
        self.set_default_cover()

        # Configurar atajo de teclado para Pause/Play con barra espaciadora
        self.shortcut_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.shortcut_space.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.shortcut_space.activated.connect(self.main_window.toggle_play)

    def toggle_shuffle(self):
        """Alterna el modo de reproducción aleatorio y ajusta estilos del botón."""
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.btn_shuffle.setStyleSheet("background-color: #1db954; color: black;")
            self.btn_shuffle.setToolTip("Aleatorio: Activado")
        else:
            self.btn_shuffle.setStyleSheet("")
            self.btn_shuffle.setToolTip("Aleatorio: Desactivado")

    def toggle_repeat(self):
        """Cicla los modos de repetición: Ninguno(0), Toda la lista(1), Bucle una canción(2)."""
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setStyleSheet("")
            self.btn_repeat.setToolTip("Repetir: Desactivado")
        elif self.repeat_mode == 1:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setStyleSheet("background-color: #3498db; color: white;")
            self.btn_repeat.setToolTip("Repetir: Toda la Lista")
        else:
            self.btn_repeat.setText("🔂")
            self.btn_repeat.setStyleSheet("background-color: #1db954; color: black;")
            self.btn_repeat.setToolTip("Repetir: Una Canción")

    def set_default_cover(self):
        """Asigna una imagen oscura vacía cuando la canción no trae carátula incrustada."""
        pixmap = QPixmap(280, 280)
        pixmap.fill(QColor("#282828"))
        self.cover_label.setPixmap(pixmap)
        
    def load_library(self):
        """
        Escanea recursivamente el directorio raíz de música asignado al sistema,
        y lee metadatos crudos del archivo, poblando la lista base (self.all_songs).
        Esta función se prefiere ante la BD para el audio porque captura cambios de archivos offline.
        """
        self.all_songs = []
        music_dir = get_music_dir()
        
        # Buscamos de forma profunda todos los archivos compatibles en local
        for root, dirs, files in os.walk(music_dir):
            for file in files:
                if file.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.ogg')):
                    path = os.path.join(root, file)
                    self.all_songs.append(extract_metadata(path))
                    
        self.build_tree()

    def build_tree(self):
        """
        Filtra y renderiza la estructura de árbol visible (QTreeWidget)
        basándose en el término buscado y en el criterio de ordenación (combobox).
        """
        self.tree_widget.clear()
        sort_mode = self.sort_combo.currentText()
        search_query = self.search_input.text().strip().lower()
        
        filtered_songs = self.all_songs
        if search_query:
            # Filtro básico por título o nombre de artista ignorando capitalización
            filtered_songs = [s for s in self.all_songs if search_query in s['title'].lower() or search_query in s['artist'].lower()]
            # Sobrescribe modo de orden para facilitar vista de listas cuando se está buscando
            sort_mode = "Nombre"
        
        if sort_mode == "Artista y Álbum":
            # Estructura de anidamiento complejo: [Artista] -> [Album] -> Pista
            artists = {}
            for song in filtered_songs:
                art = song['artist']
                alb = song['album']
                if art not in artists: artists[art] = {}
                if alb not in artists[art]: artists[art][alb] = []
                artists[art][alb].append(song)
                
            for art in sorted(artists.keys()):
                art_item = QTreeWidgetItem(self.tree_widget, [art])
                for alb in sorted(artists[art].keys()):
                    alb_item = QTreeWidgetItem(art_item, [alb])
                    for song in sorted(artists[art][alb], key=lambda x: x['title']):
                        song_item = QTreeWidgetItem(alb_item, [song['title']])
                        song_item.setData(0, Qt.ItemDataRole.UserRole, song['path'])
                        song_item.setData(0, Qt.ItemDataRole.UserRole + 1, song)
                        
        elif sort_mode == "Álbum":
            # Estructura: [Album] -> Pista
            albums = {}
            for song in filtered_songs:
                alb = song['album']
                if alb not in albums: albums[alb] = []
                albums[alb].append(song)
                
            for alb in sorted(albums.keys()):
                alb_item = QTreeWidgetItem(self.tree_widget, [alb])
                for song in sorted(albums[alb], key=lambda x: x['title']):
                    song_item = QTreeWidgetItem(alb_item, [song['title']])
                    song_item.setData(0, Qt.ItemDataRole.UserRole, song['path'])
                    song_item.setData(0, Qt.ItemDataRole.UserRole + 1, song)
                    
        else:
            # Estructura plana: Lista de nombres directos
            for song in sorted(filtered_songs, key=lambda x: x['title']):
                song_item = QTreeWidgetItem(self.tree_widget, [song['title']])
                song_item.setData(0, Qt.ItemDataRole.UserRole, song['path'])
                song_item.setData(0, Qt.ItemDataRole.UserRole + 1, song)
                
        # Expandir los nodos por defecto para ver todo el contenido
        self.tree_widget.expandAll()
        self.update_current_playlist()
        
        # Intenta re-destacar visualmente en la lista la canción que está sonando
        if self.current_index >= 0 and self.current_index < len(self.current_playlist):
            self.highlight_current_song(self.current_playlist[self.current_index][0])

    def update_current_playlist(self):
        """Sincroniza la lista de reproducción interna (lógica) con los elementos actualmente filtrados en la vista (UI)."""
        self.current_playlist = []
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            item = iterator.value()
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if path:
                self.current_playlist.append((path, item.data(0, Qt.ItemDataRole.UserRole + 1)))
            iterator += 1

    def highlight_current_song(self, path):
        """Busca el archivo en la lista, lo selecciona visualmente y desplaza (scrolls) hasta él."""
        iterator = QTreeWidgetItemIterator(self.tree_widget)
        while iterator.value():
            item = iterator.value()
            if item.data(0, Qt.ItemDataRole.UserRole) == path:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(item)
                break
            iterator += 1

    def on_item_double_clicked(self, item, column):
        """Manejador para cuando el usuario hace doble clic sobre un elemento del árbol."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.play_audio(path)

    def play_audio(self, path):
        """Inicia la reproducción, actualiza los metadatos visuales y le dice a MainWindow que inicie el stream."""
        self.update_current_playlist()
        for i, (p, meta) in enumerate(self.current_playlist):
            if p == path:
                self.current_index = i
                self.update_ui_for_song(meta)
                self.highlight_current_song(path)
                break
        self.main_window.play_media_file(path)

    def update_ui_for_song(self, metadata):
        """Asigna etiquetas de la UI (Título, Artista, Álbum) con base en la metadata del diccionario pasado."""
        self.lbl_title.setText(metadata['title'])
        self.lbl_artist.setText(f"{metadata['artist']} - {metadata['album']}")
        
        # Refresca la carátula si el archivo tenía datos embebidos
        if metadata['cover']:
            img = QImage()
            img.loadFromData(metadata['cover'])
            pixmap = QPixmap.fromImage(img).scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pixmap)
        else:
            self.set_default_cover()

    def play_next(self):
        """Pasa a la siguiente canción en base al modo seleccionado: Lineal, Aleatorio, Fin o Repetir lista."""
        if not self.current_playlist: return
        
        if self.shuffle_mode and len(self.current_playlist) > 1:
            next_idx = self.current_index
            while next_idx == self.current_index:
                next_idx = random.randint(0, len(self.current_playlist) - 1)
            self.current_index = next_idx
        else:
            if self.current_index < len(self.current_playlist) - 1:
                self.current_index += 1
            else:
                if self.repeat_mode == 1: # Repeat all
                    self.current_index = 0
                else: # Fin de playlist
                    return
                    
        path, meta = self.current_playlist[self.current_index]
        self.update_ui_for_song(meta)
        self.highlight_current_song(path)
        self.main_window.play_media_file(path)

    def play_previous(self):
        """Pasa a la canción anterior (o final si Repetir Todo está activo)."""
        if not self.current_playlist: return
        if self.current_index > 0:
            self.current_index -= 1
        else:
            if self.repeat_mode == 1:
                self.current_index = len(self.current_playlist) - 1
            else:
                return
        path, meta = self.current_playlist[self.current_index]
        self.update_ui_for_song(meta)
        self.highlight_current_song(path)
        self.main_window.play_media_file(path)

    def on_media_status_changed(self, status):
        """
        Manejador de evento interno de QMediaPlayer emitido cuando cambia su estado.
        Especialmente útil para capturar el fin natural del audio (EndOfMedia) y accionar el autoplay continuo.
        Nota: Esto se procesa incluso en segundo plano.
        """
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repeat_mode == 2: # Repeat One
                if self.current_index != -1 and self.current_index < len(self.current_playlist):
                    path, meta = self.current_playlist[self.current_index]
                    self.main_window.play_media_file(path) # Volver a dispararlo
            else:
                self.play_next() # Siguiente normal

    def on_playing_changed(self, playing):
        """
        Lanzado cada vez que el sistema se pausa o reanuda. 
        Sincroniza el botón de Play/Pausa.
        """
        self.btn_play.setText("⏸" if playing else "▶️")
