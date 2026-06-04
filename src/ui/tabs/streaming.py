from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt

class StreamingTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.stream_input = QLineEdit()
        self.stream_input.setPlaceholderText("Link...")
        
        self.btn_stream = QPushButton("Ver Streaming")
        self.btn_stream.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stream.clicked.connect(self.main_window.on_stream_clicked)
        
        self.stream_video_widget = QVideoWidget()
        
        layout.addWidget(self.stream_input)
        layout.addWidget(self.btn_stream)
        layout.addWidget(self.stream_video_widget, 1)
