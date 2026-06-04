from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import urllib.request
import ssl

# Global SSL context for thumbnails to bypass certificate issues
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class ImageLoader(QThread):
    """Asynchronous image loader to prevent UI freezes."""
    finished = pyqtSignal(QPixmap)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        if not self.url: return
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                data = response.read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    self.finished.emit(pixmap)
                else:
                    print(f"DEBUG: Pixmap is null for {self.url}")
        except Exception as e:
            print(f"DEBUG: Image loader error for {self.url}: {str(e)}")

class PlaylistWidgetItem(QWidget):
    """Custom widget for showing individual playlist items in the side panel."""
    def __init__(self, title, artist, album, thumb_url, parent=None):
        super().__init__(parent)
        self.setFixedHeight(75)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setFixedSize(100, 56)
        self.lbl_thumb.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px;")
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumb.setText("...")

        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 11px;")
        self.lbl_title.setWordWrap(False)

        self.lbl_artist = QLabel(artist)
        self.lbl_artist.setStyleSheet("color: #3498db; font-size: 10px;")

        self.lbl_album = QLabel(album)
        self.lbl_album.setStyleSheet("color: #999999; font-size: 9px; font-style: italic;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_artist)
        info_layout.addWidget(self.lbl_album)

        layout.addWidget(self.lbl_thumb)
        layout.addLayout(info_layout)

        if thumb_url:
            self.loader = ImageLoader(thumb_url)
            self.loader.finished.connect(self.on_image_loaded)
            self.loader.start()

    def on_image_loaded(self, pixmap):
        self.lbl_thumb.setPixmap(pixmap.scaled(self.lbl_thumb.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
