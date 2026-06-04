import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QSlider
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from db import db

class VideosTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.video_list = QListWidget()
        self.video_list.itemDoubleClicked.connect(self.play_selected_video)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(280)
        
        cl, self.v_slider, btn_d = self.main_window._create_player_controls(self.play_selected_video)
        btn_d.clicked.connect(lambda: self.main_window.delete_media('video'))
        
        layout.addWidget(self.video_list, 1)
        layout.addWidget(self.video_widget, 2)
        layout.addLayout(cl)

    def load_library(self):
        self.video_list.clear()
        for v in db.get_all_media('video'):
            item = QListWidgetItem(f"{v['title']} ({v['quality']})")
            item.setData(Qt.ItemDataRole.UserRole, v['file_path'])
            item.setData(Qt.ItemDataRole.UserRole + 1, v['id'])
            self.video_list.addItem(item)

    def play_selected_video(self):
        if self.video_list.currentItem():
            path = self.video_list.currentItem().data(Qt.ItemDataRole.UserRole)
            self.main_window.play_media_file(path)
