import sys
from PyQt6.QtWidgets import QApplication
from ui import MainWindow
from utils import get_music_dir, get_videos_dir
from db import db

def main():
    # Verify OS paths and init DB on startup
    _ = get_music_dir()
    _ = get_videos_dir()
    
    app = QApplication(sys.argv)
    
    # Modern Dark Theme QSS
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
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
