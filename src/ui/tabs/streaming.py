from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt

class StreamingTab(QWidget):
    """
    Pestaña para la reproducción de contenido multimedia en streaming (en vivo).
    Permite pegar un enlace y reproducirlo directamente usando yt-dlp como 
    extractor de la URL directa del stream y QMediaPlayer para la visualización.
    """
    def __init__(self, main_window):
        """
        Inicializa la pestaña de streaming.
        
        Args:
            main_window: Referencia a la ventana principal para interactuar con el reproductor global.
        """
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        """Construye y configura la interfaz de usuario de la pestaña."""
        # Layout vertical principal
        layout = QVBoxLayout(self)
        
        # Campo de entrada para la URL del stream
        self.stream_input = QLineEdit()
        self.stream_input.setPlaceholderText("Link del stream (Ej. Twitch, YouTube Live)...")
        
        # Botón para iniciar el proceso de extracción y visualización
        self.btn_stream = QPushButton("Ver Streaming")
        self.btn_stream.setCursor(Qt.CursorShape.PointingHandCursor)
        # Conecta la acción de clic con el manejador en MainWindow
        self.btn_stream.clicked.connect(self.main_window.on_stream_clicked)
        
        # Widget dedicado a renderizar el video en pantalla
        self.stream_video_widget = QVideoWidget()
        
        # Agregar todos los componentes al layout principal
        layout.addWidget(self.stream_input)
        layout.addWidget(self.btn_stream)
        # El QVideoWidget ocupa el espacio restante (stretch_factor=1)
        layout.addWidget(self.stream_video_widget, 1)
