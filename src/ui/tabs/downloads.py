import os
import time
import random
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QComboBox, QGroupBox, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..common import ImageLoader, PlaylistWidgetItem
from downloader import ExtractorThread, DownloaderThread
from db import db

class DownloadsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_info = None
        self.extractor_thread = None
        self.downloader_thread = None
        self.central_loader = None
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 0, 20, 10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Pega el link de YouTube aquí...")
        self.url_input.setClearButtonEnabled(True)
        self.url_input.returnPressed.connect(self.on_search_clicked)
        content_layout.addWidget(self.url_input)

        self.btn_search = QPushButton("Buscar")
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.clicked.connect(self.on_search_clicked)
        content_layout.addWidget(self.btn_search)

        # Advanced Options
        self.btn_advanced = QPushButton("Opciones Avanzadas ▼")
        self.btn_advanced.setFlat(True)
        self.btn_advanced.setStyleSheet("color: #888; text-align: left;")
        self.btn_advanced.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_advanced.clicked.connect(self.toggle_advanced)
        content_layout.addWidget(self.btn_advanced)

        self.advanced_panel = QGroupBox("Avanzado")
        self.advanced_panel.setVisible(False)
        self.advanced_panel.setStyleSheet("QGroupBox { color: #888; border: 1px solid #333; margin-top: 10px; }")
        adv_layout = QVBoxLayout(self.advanced_panel)
        
        # Cookies
        h_cookies = QHBoxLayout()
        h_cookies.addWidget(QLabel("Cookies del navegador:"))
        self.combo_cookies = QComboBox()
        self.combo_cookies.addItems(["None", "chrome", "firefox", "edge", "safari", "opera", "vivaldi", "brave"])
        h_cookies.addWidget(self.combo_cookies)
        adv_layout.addLayout(h_cookies)

        # Proxy
        h_proxy = QHBoxLayout()
        h_proxy.addWidget(QLabel("Proxy:"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("http://user:pass@host:port")
        h_proxy.addWidget(self.proxy_input)
        adv_layout.addLayout(h_proxy)

        # Auth
        h_auth = QHBoxLayout()
        h_auth.addWidget(QLabel("Usuario:"))
        self.user_input = QLineEdit()
        h_auth.addWidget(self.user_input)
        h_auth.addWidget(QLabel("Contraseña:"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        h_auth.addWidget(self.pass_input)
        adv_layout.addLayout(h_auth)

        content_layout.addWidget(self.advanced_panel)

        self.btn_stop_batch = QPushButton("Detener Descarga de Lote")
        self.btn_stop_batch.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop_batch.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        self.btn_stop_batch.setVisible(False)
        self.btn_stop_batch.clicked.connect(self.on_stop_batch_clicked)
        content_layout.addWidget(self.btn_stop_batch)

        preview = QWidget()
        pv_layout = QVBoxLayout(preview)
        pv_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title = QLabel("")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setWordWrap(True)
        self.lbl_author = QLabel("")
        self.lbl_author.setStyleSheet("color: #3498db;")
        self.lbl_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_album = QLabel("")
        self.lbl_album.setStyleSheet("font-style: italic; color: #888;")
        self.lbl_album.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_thumbnail = QLabel()
        self.lbl_thumbnail.setFixedSize(280, 157)
        self.lbl_thumbnail.setStyleSheet("border: 2px solid #333; background: #222; border-radius: 8px;")
        self.lbl_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pv_layout.addWidget(self.lbl_title)
        pv_layout.addWidget(self.lbl_author)
        pv_layout.addWidget(self.lbl_album)
        pv_layout.addWidget(self.lbl_thumbnail, alignment=Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(preview)
        content_layout.addSpacing(10)

        options = QHBoxLayout()
        self.v_group = QGroupBox("Video")
        self.v_group.setStyleSheet("QGroupBox { color: #3498db; font-weight: bold; border: 1px solid #333; }")
        vv = QVBoxLayout(self.v_group)
        vh = QHBoxLayout()
        self.combo_format = QComboBox(); self.combo_format.setEnabled(False)
        self.combo_format.currentIndexChanged.connect(self.update_selected_size_info)
        self.combo_ext = QComboBox(); self.combo_ext.addItems(["mp4", "mkv"]); self.combo_ext.setEnabled(False)
        self.combo_ext.currentIndexChanged.connect(self.update_selected_size_info)
        vh.addWidget(QLabel("Calidad:")); vh.addWidget(self.combo_format)
        vh.addWidget(QLabel("Formato:")); vh.addWidget(self.combo_ext)

        self.btn_v = QPushButton("Descargar Video"); self.btn_v.setEnabled(False)
        self.btn_v.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_v.clicked.connect(lambda: self.on_download_clicked('video'))
        self.lbl_size = QLabel(""); self.lbl_size.setStyleSheet("font-size: 10px; color: #3498db;")

        vv.addLayout(vh)
        vv.addWidget(self.lbl_size, alignment=Qt.AlignmentFlag.AlignCenter)
        vv.addWidget(self.btn_v)

        self.m_group = QGroupBox("Música")
        self.m_group.setStyleSheet("QGroupBox { color: #2ecc71; font-weight: bold; border: 1px solid #333; }")
        mv = QVBoxLayout(self.m_group)
        
        self.lbl_music_size = QLabel("")
        self.lbl_music_size.setStyleSheet("font-size: 10px; color: #2ecc71;")
        self.lbl_music_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_m = QPushButton("Descargar Música"); self.btn_m.setEnabled(False)
        self.btn_m.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_m.clicked.connect(lambda: self.on_download_clicked('audio'))
        self.btn_m.setStyleSheet("background-color: #27ae60;")
        mv.addStretch()
        mv.addWidget(self.lbl_music_size)
        mv.addWidget(self.btn_m)

        options.addWidget(self.v_group); options.addWidget(self.m_group)
        content_layout.addLayout(options)
        content_layout.addStretch()

        self.lbl_status = QLabel(""); self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.lbl_status)
        layout.addWidget(content)

        self.progress_bar = QProgressBar(); self.progress_bar.setFixedHeight(4); self.progress_bar.setTextVisible(False); self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def toggle_advanced(self):
        visible = not self.advanced_panel.isVisible()
        self.advanced_panel.setVisible(visible)
        self.btn_advanced.setText("Opciones Avanzadas ▲" if visible else "Opciones Avanzadas ▼")

    def get_advanced_options(self):
        browser = self.combo_cookies.currentText()
        return {
            'cookies_from_browser': browser if browser != "None" else None,
            'proxy': self.proxy_input.text().strip() or None,
            'username': self.user_input.text().strip() or None,
            'password': self.pass_input.text().strip() or None
        }

    def on_search_clicked(self):
        url = self.url_input.text().strip()
        if not url: return
        
        search_url = url
        self.reset_search_ui()
        self.url_input.setText(search_url)
        
        self.btn_search.setEnabled(False)
        self.lbl_status.setText("Buscando información...")
        self.lbl_thumbnail.setText("Cargando...")
        
        opts = self.get_advanced_options()
        self.extractor_thread = ExtractorThread(
            search_url, 
            cookies_from_browser=opts['cookies_from_browser'],
            username=opts['username'],
            password=opts['password'],
            proxy=opts['proxy']
        )
        self.extractor_thread.finished.connect(self.on_extraction_finished)
        self.extractor_thread.error.connect(self.on_extraction_error)
        self.extractor_thread.start()

    def on_extraction_finished(self, info):
        self.current_info = info; self.btn_search.setEnabled(True)
        self.set_preview_info(info)

        if info.get('_type') == 'playlist' or 'entries' in info:
            self.main_window.set_playlist_visible(True)
            for entry in info.get('entries', []):
                if entry:
                    thumb = entry.get('thumbnail') or (entry.get('thumbnails')[-1]['url'] if entry.get('thumbnails') else None)
                    p_title = entry.get('title', '...')
                    p_artist = entry.get('uploader') or entry.get('artist') or 'Unknown'
                    p_album = entry.get('album')
                    if not p_album:
                        p_album = str(entry.get('release_year') or (entry.get('upload_date')[:4] if entry.get('upload_date') else ''))
                    self.main_window.add_playlist_item(p_title, p_artist, p_album, thumb)

        is_music = 'Music' in info.get('categories', []) or (info.get('uploader') or '').endswith(' - Topic')
        from utils import get_music_dir
        existing = db.get_media_by_url(self.url_input.text().strip())
        audio_item = next((item for item in existing if item['type'] == 'audio'), None)
        # Búsqueda física recursiva normalizada en carpetas y subcarpetas para verificar si ya existe
        def normalize(t): return "".join([c for c in t if c.isalnum()]).lower()
        target = normalize(info.get('title', '_____'))
        phys_exists = False
        if target:
            for r, d, files in os.walk(get_music_dir()):
                if any(target in normalize(f) for f in files):
                    phys_exists = True
                    break
        has_audio = audio_item is not None or phys_exists
        
        # Actualizar información de tamaño de música
        if audio_item and os.path.exists(audio_item['file_path']):
            size_mb = os.path.getsize(audio_item['file_path']) / 1e6
            self.lbl_music_size.setText(f"✓ Disco: {size_mb:.1f} MB")
        else:
            best_a = next((f for f in info.get('formats', []) if f.get('vcodec') == 'none'), None)
            a_size = (best_a.get('filesize') or best_a.get('filesize_approx') or 0) if best_a else 0
            if a_size > 0:
                self.lbl_music_size.setText(f"Estimado: {a_size/1e6:.1f} MB")
            else:
                self.lbl_music_size.clear()
        
        # Get all video formats to collect unique heights
        v_formats = sorted([f for f in info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height')], key=lambda k: k.get('height', 0), reverse=True)
        
        self.combo_format.clear(); res_added = set()
        for f in v_formats:
            h = f.get('height')
            if h and h not in res_added:
                res_added.add(h)
                self.combo_format.addItem(f"{h}p", f"{h}p")
        
        self.v_group.setEnabled(not is_music)
        self.combo_format.setEnabled(not is_music and self.combo_format.count() > 0)
        self.combo_ext.setEnabled(not is_music and self.combo_format.count() > 0)
        
        if not is_music and self.combo_format.count() > 0:
            self.update_selected_size_info()
            # Mostrar resumen de calidades ya descargadas
            downloaded_quals = sorted(list(set(item['quality'] for item in existing if item['type'] == 'video' and item['quality'])))
            if downloaded_quals:
                self.lbl_status.setText(f"Video descargado en las calidades: {', '.join(downloaded_quals)}")
            else:
                self.lbl_status.setText("Listo")
        else:
            self.btn_v.setEnabled(False)
            if is_music and has_audio:
                self.lbl_status.setText("La cancion ya se encuentra en tus descargas")
            else:
                self.lbl_status.setText(f"{'Música' if is_music else 'Listo'}")
            
        self.btn_m.setEnabled(not has_audio)

    def set_preview_info(self, info):
        self.lbl_title.setText(info.get('title', ''))
        self.lbl_author.setText(info.get('uploader') or info.get('artist') or '')
        # Si el album esta vacio, traer el año
        album = info.get('album')
        if not album:
            album = str(info.get('release_year') or (info.get('upload_date')[:4] if info.get('upload_date') else ''))
        self.lbl_album.setText(album)

        t_url = info.get('thumbnail') or (info.get('thumbnails')[-1]['url'] if info.get('thumbnails') else None)
        if t_url:
            self.central_loader = ImageLoader(t_url)
            self.central_loader.finished.connect(lambda px: self.lbl_thumbnail.setPixmap(px.scaled(self.lbl_thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            self.central_loader.start()

    def update_selected_size_info(self):
        if not self.combo_format.currentData() or not self.current_info: 
            self.lbl_size.clear()
            self.btn_v.setEnabled(False)
            return
            
        q = self.combo_format.currentData() # "1080p"
        ext = self.combo_ext.currentText() # "mp4" or "mkv"
        url = self.url_input.text().strip()
        
        # Check if already downloaded (by quality in DB)
        existing = db.get_media_by_url(url)
        lp = next((i['file_path'] for i in existing if i['quality'] == q), None)
        
        if lp and os.path.exists(lp):
            self.lbl_size.setText(f"✓ Disco: {os.path.getsize(lp)/1e6:.1f} MB")
            self.btn_v.setEnabled(False)
            self.lbl_status.setText(f"Calidad {q} ya disponible en biblioteca")
        else:
            self.btn_v.setEnabled(True)
            # Volver a mostrar el resumen general si no es la calidad seleccionada la que existe
            existing = db.get_media_by_url(url)
            downloaded_quals = sorted(list(set(item['quality'] for item in existing if item['type'] == 'video' and item['quality'])))
            if downloaded_quals:
                self.lbl_status.setText(f"Video descargado en las calidades: {', '.join(downloaded_quals)}")
            else:
                self.lbl_status.setText("Listo")
            
            # Estimate size based on selected quality and format
            height = int(q[:-1])
            
            # Find best video format for this height and extension preference
            # First try to match extension
            v_f = next((f for f in self.current_info.get('formats', []) 
                        if f.get('height') == height and f.get('vcodec') != 'none' and f.get('ext') == ext), None)
            
            # Fallback to any extension for this height
            if not v_f:
                v_f = next((f for f in self.current_info.get('formats', []) 
                            if f.get('height') == height and f.get('vcodec') != 'none'), None)
            
            # Best audio
            best_a = next((f for f in self.current_info.get('formats', []) if f.get('vcodec') == 'none'), None)
            
            v_size = (v_f.get('filesize') or v_f.get('filesize_approx') or 0) if v_f else 0
            a_size = (best_a.get('filesize') or best_a.get('filesize_approx') or 0) if best_a else 0
            
            total_mb = (v_size + a_size) / 1e6
            if total_mb > 0:
                self.lbl_size.setText(f"⬇ Estimado({ext.lower()}): {total_mb:.1f} MB")
            else:
                self.lbl_size.setText(f"⬇ Estimado({ext.lower()})")

    def on_extraction_error(self, e): 
        print(f"[ERROR] Error de búsqueda/extracción: {str(e)}")
        self.btn_search.setEnabled(True)
        QMessageBox.critical(self, "Error", str(e))
    
    def on_stop_batch_clicked(self): 
        self.main_window.stop_batch_requested = True
        self.btn_stop_batch.setEnabled(False)
        self.btn_stop_batch.setText("Deteniendo...")

    def on_download_clicked(self, mt):
        url = self.url_input.text().strip(); qual = self.combo_format.currentData() if mt == 'video' else "MP3"
        ext = self.combo_ext.currentText() if mt == 'video' else "mp3"
        
        opts = self.get_advanced_options()

        if self.current_info and 'entries' in self.current_info:
            self.main_window.stop_batch_requested = False
            self.btn_stop_batch.setVisible(True)
            self.btn_stop_batch.setEnabled(True)
            self.btn_stop_batch.setText("Detener Descarga de Lote")
            self.main_window.start_batch_download(mt, qual, ext, self.current_info, **opts)
            return

        self.btn_v.setEnabled(False); self.btn_m.setEnabled(False); self.progress_bar.setVisible(True)
        height = qual[:-1] if qual.endswith('p') else qual
        f_id = f"bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/best[height={height}][ext=mp4]" if mt == 'video' else 'bestaudio'
        
        self.downloader_thread = DownloaderThread(url, f_id, mt, qual, ext, **opts)
        self.downloader_thread.progress.connect(lambda v: self.progress_bar.setValue(int(v)))
        self.downloader_thread.finished.connect(lambda t, f, m, q: self.on_download_finished(t, f, m, q, url))
        self.downloader_thread.error.connect(self.on_download_error)
        self.downloader_thread.start()

    def reset_search_ui(self):
        self.url_input.clear()
        self.lbl_title.clear()
        self.lbl_author.clear()
        self.lbl_album.clear()
        self.lbl_thumbnail.clear()
        self.combo_format.clear()
        self.combo_format.setEnabled(False)
        self.combo_ext.setEnabled(False)
        self.btn_v.setEnabled(False)
        self.btn_m.setEnabled(False)
        self.lbl_size.clear()
        self.lbl_music_size.clear()
        self.lbl_status.setText("Listo")
        self.progress_bar.setVisible(False)
        self.main_window.set_playlist_visible(False)
        self.main_window.clear_playlist()

    def on_download_finished(self, t, fp, m, q, url):
        if self.main_window.is_batch_downloading: return
        if fp: 
            db.add_media(t, m, fp, url, q)
            self.main_window.load_media_library()
        self.reset_search_ui()

    def on_download_error(self, e): 
        self.progress_bar.setVisible(False)
        self.btn_v.setEnabled(True)
        self.btn_m.setEnabled(True)
        QMessageBox.critical(self, "Error", str(e))
