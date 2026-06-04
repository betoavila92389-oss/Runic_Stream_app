import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QSlider
from PyQt6.QtCore import Qt
from db import db

class MusicTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.music_list = QListWidget()
        self.music_list.itemDoubleClicked.connect(self.play_selected_audio)
        
        cl, self.a_slider, btn_d = self.main_window._create_player_controls(self.play_selected_audio)
        btn_d.clicked.connect(lambda: self.main_window.delete_media('audio'))
        
        layout.addWidget(self.music_list, 1)
        layout.addLayout(cl)

    def load_library(self):
        self.music_list.clear()
        for a in db.get_all_media('audio'):
            item = QListWidgetItem(a['title'])
            item.setData(Qt.ItemDataRole.UserRole, a['file_path'])
            item.setData(Qt.ItemDataRole.UserRole + 1, a['id'])
            self.music_list.addItem(item)

    def play_selected_audio(self):
        if self.music_list.currentItem():
            path = self.music_list.currentItem().data(Qt.ItemDataRole.UserRole)
            self.main_window.play_media_file(path)
