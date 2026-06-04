import sys
from PyQt6.QtWidgets import QApplication
from ui import MainWindow
from utils import get_music_dir, get_videos_dir
from db import db

def main():
    """
    Punto de entrada principal para la aplicación Runic Stream.
    Inicializa los directorios requeridos, configura la interfaz gráfica de usuario
    y aplica los estilos globales (QSS).
    """
    # Verificamos y creamos los directorios del SO al iniciar
    # Esto asegura que las carpetas existan antes de que el usuario intente descargar algo
    _ = get_music_dir()
    _ = get_videos_dir()
    
    # Inicializamos la aplicación de PyQt
    app = QApplication(sys.argv)
    
    # Aplicamos un tema oscuro moderno usando QSS (Qt Style Sheets)
    # Define la apariencia general de la aplicación, como colores y bordes
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QTabWidget::pane {
            border: 1px solid #333;
            background-color: #1e1e1e;
        }
        QTabBar::tab {
            background: #2d2d2d;
            color: #b1b1b1;
            padding: 10px 20px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #3d3d3d;
            color: #ffffff;
            border-bottom: 2px solid #3498db;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:disabled {
            background-color: #555;
            color: #888;
        }
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 8px;
            color: white;
        }
        QListWidget {
            background-color: #252525;
            border: 1px solid #333;
            color: #eee;
            border-radius: 4px;
        }
        QLabel {
            color: #eee;
        }
        QProgressBar {
            border: none;
            background-color: #333;
            height: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #3498db;
        }
        QComboBox {
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 5px;
        }
    """)
    
    # Creamos e iniciamos la ventana principal
    window = MainWindow()
    window.show()
    
    # Entramos en el bucle principal de eventos de la aplicación
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
