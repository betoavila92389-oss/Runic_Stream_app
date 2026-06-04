from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import urllib.request
import ssl

# Contexto SSL global para las miniaturas.
# Esto evita problemas de certificados caducados o entornos con restricciones de red (bypass).
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class ImageLoader(QThread):
    """
    Cargador de imágenes asíncrono para evitar congelar la interfaz de usuario (UI).
    Hereda de QThread para descargar imágenes de red en segundo plano.
    """
    # Señal emitida cuando la imagen (QPixmap) se ha cargado correctamente
    finished = pyqtSignal(QPixmap)

    def __init__(self, url):
        """
        Inicializa el hilo con la URL de la imagen a descargar.
        """
        super().__init__()
        self.url = url

    def run(self):
        """
        Inicia la descarga de la imagen. 
        Se simula un navegador estándar mediante el User-Agent para evitar bloqueos por bot.
        """
        if not self.url: 
            return
        try:
            # Cabeceras para simular un navegador web común
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            req = urllib.request.Request(self.url, headers=headers)
            
            # Abrimos la conexión con un timeout de 10 segundos
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                data = response.read()
                pixmap = QPixmap()
                # Cargamos los datos crudos en el objeto QPixmap
                pixmap.loadFromData(data)
                
                # Si la imagen se cargó correctamente, emitimos la señal
                if not pixmap.isNull():
                    self.finished.emit(pixmap)
                else:
                    print(f"DEBUG: El Pixmap es nulo (vacío) para {self.url}")
        except Exception as e:
            # Capturamos cualquier error de conexión o procesamiento
            print(f"DEBUG: Error del cargador de imágenes para {self.url}: {str(e)}")

class PlaylistWidgetItem(QWidget):
    """
    Widget personalizado (Custom Widget) para mostrar elementos individuales de la lista de reproducción
    en el panel lateral de la aplicación.
    """
    def __init__(self, title, artist, album, thumb_url, parent=None):
        """
        Inicializa el widget visual de la lista de reproducción.
        
        Args:
            title (str): Título de la pista.
            artist (str): Nombre del artista o canal.
            album (str): Nombre del álbum o fecha.
            thumb_url (str): URL de la miniatura/carátula a cargar.
            parent (QWidget, opcional): Widget padre.
        """
        super().__init__(parent)
        # Altura fija para cada elemento de la lista
        self.setFixedHeight(75)
        
        # Diseño principal horizontal (imagen a la izquierda, texto a la derecha)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Etiqueta para la miniatura de la pista
        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(100, 56)
        # Estilo inicial oscuro mientras carga la imagen
        self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px;")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setText("...")

        # Layout vertical para la información (Título, Artista, Álbum)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        
        # Etiqueta del título (Blanco, negrita)
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 11px;")
        self.lbl_title.setWordWrap(False) # No permite saltos de línea para mantener el layout

        # Etiqueta del artista (Azul claro)
        self.lbl_artist = QLabel(artist)
        self.lbl_artist.setStyleSheet("color: #3498db; font-size: 10px;")

        # Etiqueta del álbum (Gris, cursiva)
        self.lbl_album = QLabel(album)
        self.lbl_album.setStyleSheet("color: #999999; font-size: 9px; font-style: italic;")

        # Añadir etiquetas de texto al layout vertical
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_artist)
        info_layout.addWidget(self.lbl_album)

        # Añadir miniatura e info al layout principal horizontal
        layout.addWidget(self.lbl_thumb)
        layout.addLayout(info_layout)

        # Si se proporcionó una URL para la miniatura, iniciar carga asíncrona
        if thumb_url:
            self.loader = ImageLoader(thumb_url)
            self.loader.finished.connect(self.on_image_loaded)
            self.loader.start()

    def on_image_loaded(self, pixmap):
        """
        Callback ejecutado cuando la imagen termina de descargarse.
        Escala la imagen manteniendo la relación de aspecto y la asigna a la etiqueta.
        """
        self.lbl_thumb.setPixmap(pixmap.scaled(
            self.lbl_thumb.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))
