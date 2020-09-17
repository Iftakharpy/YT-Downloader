# builtin modules
import os
import sys
from time import sleep
import requests
from collections import namedtuple
from pytube import YouTube
from pprint import pp

from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication


# gui import
from gui.GUI import Ui_MainWindow as Window

# main functions to download videos
from core.database import Database
from core.settings import Settings
from core.yt_loaders import Load_Qualities, YT_object_Loader
from core.downloaders import Download_Thread
from core.stream_filters import  Stream_Filter
from core.pretty_file_size import File_Size_Converter
from core import checkers
from core import exceptions
from core import formatters
from core import video_ids_getter_from_playlist as playlist_loader


YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
QT_ICONS = namedtuple("qt_icons_for_alert_function",["information", "question", "warning", "critical"])


class APP(QMainWindow, Window, object):
    DB = Database()
    SETTINGS = Settings()
    ICONS = QT_ICONS(QMessageBox.Information, QMessageBox.Question, QMessageBox.Warning, QMessageBox.Critical)
    
    SLEEP_TIME = 0.0001
    #time out for status bar messages
    STATUS_TIMEOUT = 10000 
    
    #playlist_quality to download indexes are taken from playlist_qualities QComboBox
    PLAYLIST_QUALITY_INDEX = 0 #{0:"best progressive", 1:"best audio", 2:"best video", 3:"best audio+video"}

    VIDEO_TAB_STREAMS = []
    PARENT=None
    HOST_DIR = os.getcwd()

    pl_video_yt_object=None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PARENT = args[0]
        # settings up the window form gui folder
        self.setupUi(self)

        #temporaily changing default tab
        self.tabWidget.setCurrentIndex(0)

        self._set_video_tab_to_idle()
        self._set_playlist_tab_to_idle()
        #updating settings tabs placeholders from the settings.json file
        self._update_settings_fields_palceholders()
        
        self._connect_functions_to_buttons()

    def _connected_to_internet(self):
        try:
            a=requests.get("https://www.google.com")
        except Exception as e:
            a=None
        if a:
            return True
        return False

    def _check_current_api_key(self):
        if self._validate_api_key(self.SETTINGS.api_key)==False:
            self._show_alert("Invalid YouTube API key", "Currently saved api key is invalid save a valid api key to download playlists.")


    def _set_statusbar_text(self, text, timeout=STATUS_TIMEOUT):
        self.statusbar.showMessage(text, timeout)

    def _set_video_tab_to_idle(self, clear_qualities=True, disable_download=True):
        self.progress.setValue(0)
        self.currently_downloading.setText("Downloading nothing")
        self.pause_resume.setText("Pause")
        self.load_qualities.setEnabled(True)
        self.pause_resume.setDisabled(True)
        self.cancel.setDisabled(True)
        if disable_download:
            self.download_video.setDisabled(True)
        if clear_qualities:
            self.qualities.clear()

    def _set_playlist_tab_to_idle(self):
        self.currently_downloading_playlist_video.setText(
            "Downloading nothing")
        self.playlist_video_number.setText("")
        self.playlist_video_progress.setValue(0)
        self.pause_resume_playlist_video.setText("Pause")
        self.pause_resume_playlist_video.setDisabled(True)
        self.cancel_playlist_video.setDisabled(True)
        self.stop_downloading_playlist.setDisabled(True)
        self.download_playlist.setEnabled(True)

    def _connect_functions_to_buttons(self):
        ##################### VIDEO TAB ########################
        # connecting function to download button
        self.download_video.clicked.connect(self.handle_download_video_clicked)

        # connecting function to load_qualites button
        self.load_qualities.clicked.connect(self.handle_load_qualities_clicked)

        # connecting function to pause_resume button
        self.pause_resume.clicked.connect(self.handle_pause_resume_clicked)

        # connecting function to cancel button
        self.cancel.clicked.connect(self.handle_cancel_clicked)
        #################### END VIDEO TAB ######################



        #################### PLAYLIST TAB ######################
        self.download_playlist.clicked.connect(self.handle_download_playlist_clicked)

        # connecting function to playlist_qualities to get the video qualities
        self.playlist_qualities.currentIndexChanged.connect(self.handle_playlist_qualities_changed)

        self.pause_resume_playlist_video.clicked.connect(self.handle_pause_resume_playlist_video)

        self.cancel_playlist_video.clicked.connect(self.handle_cancel_playlist_video)

        self.stop_downloading_playlist.clicked.connect(self.handle_stop_downloading_playlist)
        ################## END PLAYLIST TAB ####################



        #################### SETTINGS TAB #######################
        # connecting function to videos_location_browse button
        self.videos_location_browse.clicked.connect(self.handle_videos_location_browse)

        # connecting function to playlists_location_browse button
        self.playlists_location_browse.clicked.connect(self.handle_playlists_location_browse)

        # connecting function to save_settigs button
        self.save_settings.clicked.connect(self.write_settings)
        self.api_key.editingFinished.connect(self.write_settings)
        ################## END SETTINGS TAB #####################


    def _get_text(self, name_of_qt_widget):
        text = self.__getattribute__(name_of_qt_widget).text()
        return text

    def _show_alert(self, title="", message="", icon=QMessageBox.Information):
        alert = QMessageBox(parent=self)
        alert.setWindowTitle(title)
        alert.setText(message)
        alert.setIcon(icon)
        alert.exec()

    def _validate_folder(self, folder_path):
        return os.path.exists(folder_path) and os.path.isdir(folder_path)

    def _handle_error_on_different_thread(self, error):
        try:
            title = error.title
            message = str(error)
            self._show_alert(title,message,self.ICONS.critical)
            if self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.isRunning:
                self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()
        except Exception as e:
            # raise e
            self._show_alert("Error Occured",
                            str(e)+"\nError Occured on a child Thread.\nMay be you lost internet connection.",
                            self.ICONS.critical)
            if self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.isRunning:
                self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()


#############################################   VIDEO TAB   #############################################
    def receive_streams(self,streams):
        self.VIDEO_TAB_STREAMS = streams
        self.download_video.setEnabled(True)
        self._set_statusbar_text("Video qualities are loaded")
        self.LOADER_THREAD.exit()

    def _load_qualities_seperate_thread(self):
        self.LOADER_THREAD = QThread()
        
        self.loader = Load_Qualities(self.yt_object)
        self.loader.moveToThread(self.LOADER_THREAD)
        self.loader.new_stream_loaded.connect(self.qualities.addItem)
        self.loader.completed.connect(self.receive_streams)
        self.loader.error_occured.connect(self._handle_error_on_different_thread)

        self.LOADER_THREAD.started.connect(self.loader.run)
        self.LOADER_THREAD.start()
        


    # def _load_qualities_same_thread(self):
    #     #cleanning up
    #     if self.qualities.count():
    #         self.qualities.clear()
    #         self.VIDEO_TAB_STREAMS.clear()
        
    #     audios = self.yt_object.streams.filter(only_audio=True, progressive=False).order_by("abr")
    #     videos = self.yt_object.streams.filter(only_video=True, progressive=False).order_by("resolution")
    #     progressive_videos = self.yt_object.streams.filter(progressive=True).order_by("resolution")

    #     #adding progressive streams into the qualities combo box
    #     for stream in progressive_videos:
    #         combo_text = f"{stream.resolution} audio+video {File_Size_Converter(stream.filesize)}"
    #         self.qualities.addItem(combo_text)
    #         self.VIDEO_TAB_STREAMS.append(stream)
    #     #adding video streams into the qualities combo box
    #     for stream in videos:
    #         combo_text = f"{stream.resolution} video only {File_Size_Converter(stream.filesize)}"
    #         self.qualities.addItem(combo_text)
    #         self.VIDEO_TAB_STREAMS.append(stream)
    #     #adding audio streams into the qualities combo box
    #     for stream in audios:
    #         combo_text = f"{stream.abr} audio only {File_Size_Converter(stream.filesize)}"
    #         self.qualities.addItem(combo_text)
    #         self.VIDEO_TAB_STREAMS.append(stream)
        
    #     if self.VIDEO_TAB_STREAMS:
    #         self.qualities.setCurrentIndex(0)



    def _get_selected_stream(self):
        return self.VIDEO_TAB_STREAMS[self.qualities.currentIndex()]

    def receive_yt_object(self, yt_object, Return=False):
        if Return == True:
            return yt_object
        self.yt_object = yt_object
        self.YT_OBJECT_LOADER_THREAD.exit()

    def load_yt_object(self, video_url):
        self.YT_OBJECT_LOADER_THREAD = QThread()
        
        self.yt_loader = YT_object_Loader(video_url)
        self.yt_loader.moveToThread(self.YT_OBJECT_LOADER_THREAD)
        self.yt_loader.completed.connect(self.receive_yt_object)

        self.YT_OBJECT_LOADER_THREAD.started.connect(self.yt_loader.run)
        self.YT_OBJECT_LOADER_THREAD.start()
        while not self.VIDEO_TAB_STREAMS:
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            sleep(self.SLEEP_TIME)

    def handle_load_qualities_clicked(self):
        if not self._connected_to_internet():
            self._show_alert("Connection Error",
                            "You are not connected to Internet.\nConnect to a network and try again",
                            self.ICONS.critical)
            self.load_qualities.setEnabled(True)
            return
        self._set_statusbar_text("Loading video Qualities")
        self.VIDEO_TAB_STREAMS.clear()
        self.qualities.clear()
        self.download_video.setDisabled(True)
        # del(self.yt_object)
        self.load_qualities.setDisabled(True)
        video_id_inpt = self._get_text("video_id")
        try:
            video_id = checkers.check_video_id_or_url(video_id_inpt)
            self.VT_VIDEO_ID = video_id

            #creating self.yt_object
            formatted_url = formatters.format_video_id_to_url(video_id)
            QApplication.sendPostedEvents() 
            QApplication.processEvents()
            self.yt_object = YouTube(formatted_url)#self.load_yt_object(formatted_url)

            #loading qualities to qualities combobox
            self._load_qualities_seperate_thread()

        except exceptions.Invalid_Video_Id as e:
            self._show_alert(e.title, e.message, self.ICONS.warning)
        except Exception as e:
            self._handle_error_on_different_thread(e)

        finally:
            self.load_qualities.setEnabled(True)
        

    def handle_pause_resume_clicked(self):
        if self.VIDEO_DOWNLOAD_THREAD.paused == True:
            self.pause_resume.setText("Pause")
            self.VIDEO_DOWNLOAD_THREAD.resume_download()
            return
        self.pause_resume.setText("Resume")
        self.VIDEO_DOWNLOAD_THREAD.pause_download()

    def handle_cancel_clicked(self):
        self._set_video_tab_to_idle()
        self.VIDEO_DOWNLOAD_THREAD.cancel_download()
        os.chdir(self.HOST_DIR)

    def handle_signal_of_video_cancellation(self):
        self._set_video_tab_to_idle()
        self.VIDEO_DOWNLOAD_THREAD.exit()
    
    def handle_error_while_downloading(self, error_obj):
        try:
            title = error_obj.title
            message = str(error_obj)
            self._show_alert(title, message, self.ICONS.critical)
        except Exception as e:
            self._show_alert("Error Occured While Downloading", str(e), self.ICONS.critical)

    def handle_download_video_clicked(self):
        self.load_qualities.setDisabled(True)
        os.makedirs(self.SETTINGS.video_dir, exist_ok=True)
        os.chdir(self.SETTINGS.video_dir)
        self.VIDEO_DOWNLOAD_THREAD = Download_Thread(self.yt_object,
                                                     self._get_selected_stream(), 
                                                     self.VT_VIDEO_ID,
                                                     parent=None
                                                     )
        self.VIDEO_DOWNLOAD_THREAD.progress_updated.connect(self.progress.setValue)
        self.VIDEO_DOWNLOAD_THREAD.download_completed.connect(self.handle_completed_download)
        self.VIDEO_DOWNLOAD_THREAD.download_cancelled.connect(self.handle_signal_of_video_cancellation)
        self.VIDEO_DOWNLOAD_THREAD.error_occured.connect(self.handle_error_while_downloading)

        self.pause_resume.setEnabled(True)
        self.cancel.setEnabled(True)
        self.download_video.setDisabled(True)
        # QApplication.processEvents()
        self.VIDEO_DOWNLOAD_THREAD.start()
        self.currently_downloading.setText(f"Downloading {self.yt_object.title}")
    
    def handle_completed_download(self, *args):
        if len(args)>=2:
            self._set_statusbar_text(f"Downloaded {args[0]} to \"{args[1]}\"")
        self._set_statusbar_text("\n".join(args))
        self.download_video.setEnabled(True)
        self._set_video_tab_to_idle(clear_qualities=False, disable_download=False)
        self.VIDEO_DOWNLOAD_THREAD.exit()
        os.chdir(self.HOST_DIR)

        
#############################################   END VIDEO TAB   #############################################


#############################################   PLAYLIST TAB   ##############################################
    def handle_playlist_qualities_changed(self):
        self.PLAYLIST_QUALITY_INDEX = self.playlist_qualities.currentIndex()
    
    # def receive_playlist_yt_object(self, yt_object):
    #     self.PLAYLIST_YT_OBJECT_LOADER_THREAD.exit()
    #     self.playlist_yt_object = yt_object

    # def load_playlist_yt_object(self, video_url):
    #     self.PLAYLIST_YT_OBJECT_LOADER_THREAD = QThread()
        
    #     self.yt_loader = YT_object_Loader(video_url)
    #     self.yt_loader.moveToThread(self.PLAYLIST_YT_OBJECT_LOADER_THREAD)
    #     self.yt_loader.completed.connect(self.receive_yt_object)

    #     self.PLAYLIST_YT_OBJECT_LOADER_THREAD.started.connect(self.yt_loader.run)
    #     self.PLAYLIST_YT_OBJECT_LOADER_THREAD.start()
    #     while not self.VIDEO_TAB_STREAMS:
    #         QApplication.sendPostedEvents()
    #         QApplication.processEvents()
    #         sleep(self.SLEEP_TIME)

    def handle_pause_resume_playlist_video(self):
        if self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.paused == True:
            self.pause_resume_playlist_video.setText("Pause")
            self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.resume_download()
            return
        self.pause_resume_playlist_video.setText("Resume")
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.pause_download()

    def handle_cancel_playlist_video(self):
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.cancel_download()

    def handle_stop_downloading_playlist(self):
        self.STOP_DOWNLOADING_PLAYLIST=True
        self._set_playlist_tab_to_idle()

    def handle_signal_of_playlist_video_cancellation(self):
        self._set_playlist_tab_to_idle()
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()



    def filter_playlist_video_stream(self, yt_object=pl_video_yt_object, quality_index=PLAYLIST_QUALITY_INDEX):
        if not yt_object:
            yt_object = self.pl_video_yt_object
        if quality_index == 0:
            self.playlist_video_stream = Stream_Filter(yt_object).get_highest_quality_progressive_stream()
            return
        elif quality_index == 1:
            self.playlist_video_stream = Stream_Filter(yt_object).get_highest_quality_video_stream()
            return
        elif quality_index == 2:
            self.playlist_video_stream = Stream_Filter(yt_object).get_highest_quality_audio_stream()
        print(self.playlist_video_stream)
        raise ValueError("Caller function should have handelled this error.")


    def handle_playlist_video_downloaded(self, path):
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()
        self._set_statusbar_text(path)
        self.downloaded_playlist_video = True
        # self._set_playlist_tab_to_idle()


    def start_downloading_playlist_video_on_different_thread(self, pl_video_yt_object, playlist_video_stream, video_id, parent=None, file_name=None):
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD = Download_Thread(self.pl_video_yt_object,
                                                            self.playlist_video_stream, 
                                                            video_id,
                                                            parent=None
                                                            )
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.progress_updated.connect(self.playlist_video_progress.setValue)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_completed.connect(self.handle_playlist_video_downloaded)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_cancelled.connect(self.handle_signal_of_playlist_video_cancellation)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.error_occured.connect(self._handle_error_on_different_thread)

        self.pause_resume_playlist_video.setEnabled(True)
        self.cancel_playlist_video.setEnabled(True)
        self.stop_downloading_playlist.setEnabled(True)
        
        if file_name:
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.run(file_name=file_name)
        else:
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.run()
            

        self.currently_downloading_playlist_video.setText(f"Downloading {self.pl_video_yt_object.title}")
        while self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.isRunning:
            # print("running thread")
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            sleep(self.SLEEP_TIME)
            if self.STOP_DOWNLOADING_PLAYLIST or self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.cancelled==True or self.downloaded_playlist_video:
                QApplication.sendPostedEvents()
                QApplication.processEvents()
                self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.cancel_download()
                self.downloaded_playlist_video=False
                return


    def handle_download_playlist_clicked(self):
        self.PL_VIDEO_IDS = []
        playlist_id_inpt = self._get_text("playlist_id")
        try:
            playlist_id = checkers.check_playlist_id_or_url(playlist_id_inpt)
        except exceptions.Invalid_Playlist_Id as e:
            self._show_alert(e.title, e.message)
            return
        self._set_statusbar_text("Loading video ids from YouTube Data API v3.")

        QApplication.sendPostedEvents()
        QApplication.processEvents()
        try:
            self.PL_VIDEO_IDS = playlist_loader.get_video_ids(playlist_id,self.SETTINGS.api_key)
        except exceptions.API_Error as e:
            self._show_alert(e.title, str(e), self.ICONS.critical)
        except Exception as e:
            self.DB.insert_error("Playlist error", str(e))
            self._show_alert("Error Occured", str(e))

        QApplication.sendPostedEvents()
        QApplication.processEvents()
        self.playlist_name = playlist_loader.get_playlist_name(playlist_id)

        self.valid_dir_name_for_playlist = formatters.make_valid_dir_name(self.playlist_name)
        self.palylist_dir = os.path.join(self.SETTINGS.playlist_dir, self.valid_dir_name_for_playlist)
        os.makedirs(self.palylist_dir, exist_ok=True)
        os.chdir(self.palylist_dir)
        while not self.PL_VIDEO_IDS:
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            continue
        
        self.download_playlist.setDisabled(True)
        self.stop_downloading_playlist.setEnabled(True)
        self.pause_resume_playlist_video.setEnabled(True)

        self.STOP_DOWNLOADING_PLAYLIST = False
        for index,video_id in enumerate(self.PL_VIDEO_IDS):
            self.playlist_video_number.setText(f"Downloading {index+1}/{len(self.PL_VIDEO_IDS)} of \"{self.playlist_name}\"")
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            self._load_playlist_video_yt_object(formatters.format_video_id_to_url(video_id))
            self.currently_downloading.setText(self.pl_video_yt_object.title)

            if self.PLAYLIST_QUALITY_INDEX<=2:
                QApplication.sendPostedEvents()
                QApplication.processEvents()
                self.start_downloading_playlist_video_on_different_thread(self.pl_video_yt_object,
                                                                        self.filter_playlist_video_stream(), 
                                                                        video_id,
                                                                        parent=None)
                self._set_playlist_tab_to_idle()
                
            
            elif self.PLAYLIST_QUALITY_INDEX==3:
                QApplication.sendPostedEvents()
                QApplication.processEvents()
                self.start_downloading_playlist_video_on_different_thread(self.pl_video_yt_object,
                                                                        self.filter_playlist_video_stream(quality_index=1), 
                                                                        video_id,
                                                                        parent=None,
                                                                        file_name=self.pl_video_yt_object.title+"video")
                self._set_playlist_tab_to_idle()
                
                QApplication.sendPostedEvents()
                QApplication.processEvents()
                self.start_downloading_playlist_video_on_different_thread(self.pl_video_yt_object,
                                                                        self.filter_playlist_video_stream(quality_index=2), 
                                                                        video_id,
                                                                        parent=None,
                                                                        file_name=self.pl_video_yt_object.title+"audio")
                self._set_playlist_tab_to_idle()
                

            if self.STOP_DOWNLOADING_PLAYLIST:
                self.STOP_DOWNLOADING_PLAYLIST = False
            self._set_playlist_tab_to_idle()
        self._set_playlist_tab_to_idle()
            # self.PLAYLIST_VIDEO_DOWNLOAD_THREAD = Download_Thread(self.pl_video_yt_object,
            #                                             self.playlist_video_stream, 
            #                                             video_id,
            #                                             parent=None
            #                                             )
            # self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.progress_updated.connect(self.playlist_video_progress.setValue)
            # self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_completed.connect(self.handle_completed_download)
            # self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_cancelled.connect(self.handle_signal_of_playlist_video_cancellation)
            # self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.error_occured.connect(self.handle_error_while_downloading)

            # self.pause_resume_playlist_video.setEnabled(True)
            # self.cancel_playlist_video.setEnabled(True)
            # self.stop_downloading_playlist.setEnabled(True)

            # self.VIDEO_DOWNLOAD_THREAD.start()
            # self.currently_downloading.setText(f"Downloading {self.yt_object.title}")
            # while self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.isRunning:
            #     QApplication.sendPostedEvents()
            #     QApplication.processEvents()
            #     sleep(self.SLEEP_TIME)
            #     if self.STOP_DOWNLOADING_PLAYLIST:
            #         QApplication.sendPostedEvents()
            #         QApplication.processEvents()
            #         self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.cancel_download()


    def receive_playlist_video_yt_object(self, pl_yt_object):
        self.pl_video_yt_object = pl_yt_object
        self.PLAYLIST_YT_OBJECT_LOADER_THREAD.exit()

    def _load_playlist_video_yt_object(self, video_url):
        self.pl_video_yt_object = None
        self.PLAYLIST_YT_OBJECT_LOADER_THREAD = QThread()

        self.playlist_video_yt_loader = YT_object_Loader(video_url)
        self.playlist_video_yt_loader.moveToThread(self.PLAYLIST_YT_OBJECT_LOADER_THREAD)
        self.playlist_video_yt_loader.completed.connect(self.receive_playlist_video_yt_object) #reciving the yt object
        self.playlist_video_yt_loader.error_occured.connect(self.handle_error_while_downloading)

        self.PLAYLIST_YT_OBJECT_LOADER_THREAD.started.connect(self.playlist_video_yt_loader.run)
        self.PLAYLIST_YT_OBJECT_LOADER_THREAD.start()
        while not self.pl_video_yt_object:
            QApplication.sendPostedEvents()
            QApplication.processEvents()
            sleep(self.SLEEP_TIME)
        

###########################################   END PLAYLIST TAB   ############################################




#############################################   SETTINGS TAB   #############################################
    def _update_settings_fields_palceholders(self):
        self.api_key.setPlaceholderText(self.SETTINGS.api_key)
        self.videos_location.setPlaceholderText(self.SETTINGS.video_dir)
        self.playlists_location.setPlaceholderText(self.SETTINGS.playlist_dir)


    def handle_videos_location_browse(self):
        location = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption="Select a folder to save downloaded videos."
        )
        self.videos_location.setText(location)

    def handle_playlists_location_browse(self):
        location = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption="Select a folder to save downloaded playlists."
        )
        self.playlists_location.setText(location)

    def _validate_api_key(self, api_key):
        params = {
            "key": api_key,  # api_key to authenticate
            "part": "contentDetails",  # defining the details level
            "playlistId": "PLnrO9iqgTHN-ub7YeZw7Aheo7e0yX5JSH"  # setting the playlist id
        }
        if len(api_key) == 39:
            if not self._connected_to_internet():
                self._show_alert("Connection Error",
                                "Can't validate saved youtube api key.\nYou aren't connected to Internet.")
                return 404
            response = requests.get(YOUTUBE_API_URL, params=params)
            if response.status_code>=400:
                return 404 #connection error
            if response.status_code <= 399:
                return True
        return False

    def validate_settings_fields(self):
        api_key = self._get_text("api_key").strip()
        video_dir = self._get_text("videos_location").strip()
        playlist_dir = self._get_text("playlists_location").strip()
        return api_key, video_dir, playlist_dir

    def write_settings(self):
        api_key, video_dir, playlist_dir = self.validate_settings_fields()
        # to know if anythig changed
        changed = []
        if api_key:
            if self._validate_api_key(api_key)==True:
                self.SETTINGS.api_key = api_key
                changed.append(True)
            else:
                self._show_alert(
                    "Invalid YouTube API key",
                    """You entered a wrong YouTube API key.

You won't be able to download any playlsits if you don't set a valid YouTube API key. \
To get an api key just visit the link and follow the guides.
"""
                )

        if video_dir:
            if self._validate_folder(video_dir):
                self.SETTINGS.video_dir = os.path.join(video_dir, "Videos")
                changed.append(True)
            else:
                self._show_alert(
                    "Invalid path for videos",
                    """
You entered a wrong path to save downloaded videos.
"""
                )

        if playlist_dir:
            if self._validate_folder(playlist_dir):
                self.SETTINGS.playlist_dir = os.path.join(playlist_dir, "Playlists")
                changed.append(True)
            else:
                self._show_alert(
                    "Invalid path for playlists",
                    """
You entered a wrong path to save downloaded playlists.
"""
                )

        if any(changed):
            self.SETTINGS.save_settings()
            self.statusbar.showMessage("Saved Settings", self.STATUS_TIMEOUT)
            self._update_settings_fields_palceholders()
#############################################   END SETTINGS TAB   #############################################


# def main():
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     window = APP()
#     window.show()
#     window._check_current_api_key()
    # sys.exit(app.exec_())

def main():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = APP(MainWindow)
    ui.show()
    # ui._check_current_api_key()
    exit_code = app.exec_()

    try:
        app.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()
    except Exception:
        pass
    
    try:
        app.LOADER_THREAD.exit()
    except Exception:
        pass
    
    try:
        app.YT_OBJECT_LOADER_THREAD.exit()
    except Exception:
        pass
    
    try:
        app.VIDEO_DOWNLOAD_THREAD.exit()
    except Exception:
        pass
    
    try:
        app.YT_OBJECT_LOADER_THREAD.exit()
    except Exception:
        pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
