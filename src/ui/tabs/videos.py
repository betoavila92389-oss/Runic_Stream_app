import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QSlider
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from db import db

class VideosTab(QWidget):
    """
    Pestaña que gestiona la biblioteca de videos descargados localmente.
    Permite listar, reproducir y eliminar videos de la base de datos y del disco duro.
    """
    def __init__(self, main_window):
        """
        Inicializa la pestaña de videos.
        
        Args:
            main_window: Referencia a la ventana principal (MainWindow) que orquesta los controles globales.
        """
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        """Construye los widgets y establece la disposición de la pestaña de videos."""
        # Layout principal vertical
        layout = QVBoxLayout(self)
        
        # Lista visual de los videos descargados
        self.video_list = QListWidget()
        # Conectamos doble clic en la lista para iniciar la reproducción
        self.video_list.itemDoubleClicked.connect(self.play_selected_video)
        
        # Superficie de renderizado para el reproductor de video interno
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(280) # Garantizamos una altura mínima para ver la imagen
        
        # Obtenemos un panel de controles de reproducción prefabricado desde la ventana principal
        cl, self.v_slider, btn_d = self.main_window._create_player_controls(self.play_selected_video)
        # Conectamos el botón de borrar (btn_d) con la función de borrado de base de datos
        btn_d.clicked.connect(lambda: self.main_window.delete_media('video'))
        
        # Agregamos la lista (ocupa factor 1), el reproductor (factor 2, más grande) y los controles
        layout.addWidget(self.video_list, 1)
        layout.addWidget(self.video_widget, 2)
        layout.addLayout(cl)

    def load_library(self):
        """
        Carga o recarga la biblioteca de videos desde la base de datos (SQLite)
        y puebla el widget de lista en pantalla.
        """
        # Limpiamos elementos anteriores para evitar duplicados
        self.video_list.clear()
        
        # Obtenemos todos los registros de tipo 'video' de la DB
        for v in db.get_all_media('video'):
            # Creamos un item visual que muestra el título y la calidad guardada
            item = QListWidgetItem(f"{v['title']} ({v['quality']})")
            # Guardamos datos invisibles útiles en el item (ruta y ID de DB)
            item.setData(Qt.ItemDataRole.UserRole, v['file_path'])
            item.setData(Qt.ItemDataRole.UserRole + 1, v['id'])
            
            # Lo añadimos al panel visible
            self.video_list.addItem(item)

    def play_selected_video(self):
        """
        Inicia la reproducción del video seleccionado en la lista.
        Extrae la ruta almacenada y le delega el trabajo de reproducción a MainWindow.
        """
        if self.video_list.currentItem():
            # Extrae la ruta local usando el UserRole donde la guardamos al cargar
            path = self.video_list.currentItem().data(Qt.ItemDataRole.UserRole)
            # Reproduce utilizando el mediador global
            self.main_window.play_media_file(path)
