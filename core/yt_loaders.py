from core.pretty_file_size import File_Size_Converter
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from time import sleep

from pytube import Stream,YouTube
import urllib


class YT_object_Loader(QObject):
    completed = pyqtSignal(YouTube) #emits an pytube.YouTube object when finished
    def __init__(self, video_url):
        super().__init__()
        self.video_url = video_url
    
    def run(self):
        self.completed.emit(YouTube(self.video_url))




class Load_Qualities(QObject):
    completed = pyqtSignal(list)
    new_stream_loaded = pyqtSignal(str)
    error_occured = pyqtSignal(Exception)
    streams = []

    def __init__(self, yt_object):
        super().__init__()
        self.yt_object = yt_object
        self.default_file_size = None
    
    def run(self):
        #cleanning up
        self.streams.clear()
        

        audios = self.yt_object.streams.filter(only_audio=True, progressive=False).order_by("abr")
        videos = self.yt_object.streams.filter(only_video=True, progressive=False).order_by("resolution")
        progressive_videos = self.yt_object.streams.filter(progressive=True).order_by("resolution")


        #adding progressive streams into the qualities combo box
        for stream in progressive_videos:
            try:
                size = stream.filesize
            except urllib.error.HTTPError:
                size = self.default_file_size
            except Exception as e:
                self.error_occured.emit(e)
            
            combo_text = f"{stream.resolution} audio+video {File_Size_Converter(size)}"
            #to not block other processes
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            #emiting signal
            self.new_stream_loaded.emit(combo_text)
            #adding the stream to collections to emit later
            self.streams.append(stream)
        #adding video streams into the qualities combo box
        for stream in videos:
            try:
                size = stream.filesize
            except urllib.error.HTTPError:
                size = self.default_file_size
            except Exception as e:
                self.error_occured.emit(e)

            combo_text = f"{stream.resolution} video only {File_Size_Converter(size)}"
            #to not block other processes
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            #emiting signal
            self.new_stream_loaded.emit(combo_text)
            #adding the stream to collections to emit later
            self.streams.append(stream)
        #adding audio streams into the qualities combo box
        for stream in audios:
            try:
                size = stream.filesize
            except urllib.error.HTTPError:
                size = self.default_file_size
            except Exception as e:
                self.error_occured.emit(e)
            
            combo_text = f"{stream.abr} audio only {File_Size_Converter(size)}"
            #to not block other processes
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            #emiting signal
            self.new_stream_loaded.emit(combo_text)
            #adding the stream to collections to emit later
            self.streams.append(stream)
        
        #to not block other processes
        # QApplication.processEvents()
        QApplication.sendPostedEvents()
        self.completed.emit(self.streams)







#for reference how these calsses shoud be ran
if __name__=="__main__":
    #creating loader thread
    Loader_Thread = QThread()

    #creating loader object and moving it to Loader_Thread
    loader = Load_Qualities(YouTube("https://www.youtube.com/watch?v=cKPlPJyQrt4"))
    loader.moveToThread(Loader_Thread)

    #printing the signal when a new stream loads
    loader.new_stream_loaded.connect(print)
    
    def handle_completed_loading(streams):
        for i in streams:
            print(i)
        Loader_Thread.quit()

    #when completed signal emits reciving the list of streams and closing the Loader_Thread
    loader.completed.connect(handle_completed_loading)
    
    #starting the Thread
    Loader_Thread.started.connect(loader.run)
    Loader_Thread.start()

    while Loader_Thread.isRunning():
        QApplication.sendPostedEvents()
        QApplication.processEvents()
        sleep(.001)