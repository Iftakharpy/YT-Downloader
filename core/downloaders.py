import os
import sys
import re

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

import urllib
import json
from pytube import YouTube
import subprocess as sp
from . import exceptions
from .logger import Logger_Decorator_For_Download_Func


class Download_Thread(QThread):
    progress_updated = pyqtSignal(int) #(progress)
    download_completed = pyqtSignal(str) #(file_path)
    download_cancelled = pyqtSignal()
    error_occured = pyqtSignal(Exception)
    paused = False
    cancelled = False

    def __init__(self, yt_object, stream, video_id, file_path=None, file_name=None,parent=None):
        super().__init__(parent=parent)
        self.parent=parent
        self.yt_object = yt_object
        #setting callback function
        self.yt_object.register_on_progress_callback(self.emit_progress)
        self.yt_object.register_on_complete_callback(self.emit_completed)
        self.stream = stream
        self.video_id = video_id
        #details to save video
        self.file_name = file_name
        self.file_path = file_path
        #getting file size to calculate progress
        try:
            self.file_size = stream.filesize
        except Exception as e:
            self.error_occured.emit(e)

    def emit_completed(self, stream, file_path):
        self.download_completed.emit(file_path)

    def emit_progress(self, stream, chunk, bytes_remaining):
        while self.paused or self.cancelled:
            if self.cancelled:
                self.cancel_download()
                self.download_cancelled.emit()
                raise exceptions.Download_Cancelled
        
        progress = int(self.progress_percent(stream, chunk, bytes_remaining))
        self.progress_updated.emit(progress)
    
    def progress_percent(self, stream, chunk, bytes_remaining):
        progress = round((float(abs(bytes_remaining-self.file_size)/self.file_size))*float(100),2)
        return progress

    def run(self, *args, **kwargs):
        """
        Pass args and kwargs to stream.downloade function
        """
        self.DOWNLOADER_THREAD = QThread()
        self.downloader = Logger_Decorator_For_Download_Func(self.stream.download, self.video_id, parent=None)
        self.downloader.moveToThread(self.DOWNLOADER_THREAD)
        self.downloader.completed.connect(self.DOWNLOADER_THREAD.exit)
        try:
            self.downloader.run(*args, **kwargs)
        except Exception as e:
            self.error_occured.emit(e)
    
    def pause_download(self):
        self.paused = True
    
    def resume_download(self):
        self.paused = False

    def cancel_download(self):
        self.cancelled = True
