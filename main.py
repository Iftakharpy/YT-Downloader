import logging

logger = logging.getLogger("yt_downloader")
logging.basicConfig(filename = "yt_downloader.log",
                    filemode = "w",
                    format = "[%(asctime)s] - Line No: %(lineno)d - File Path: %(pathname)s \n%(message)s",
                    level = logging.ERROR
                    )

# builtin modules
import os
import sys
import http
from time import sleep
import requests
from collections import namedtuple
import pytube
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

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Close Window confirmation",
                                            "Are you sure you want to close the application?",
                                            QMessageBox.Yes | QMessageBox.No)
        
        
        #closing all the threads and quitting
        if reply == 16384:
            try:
                self.handle_cancel_clicked()
            except Exception:
                pass
            try:
                self.handle_cancel_playlist_video_clicked()
            except Exception:
                pass
            try:
                self.handle_stop_downloading_playlist()
            except Exception:
                pass
            event.accept()
        #ignoring
        elif reply == 65536:
            event.ignore()
        else:
            print("don't know what to do")

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
        self.playlist_qualities.setEnabled(True)



    def _connect_functions_to_buttons(self):
        ##################### VIDEO TAB ########################
        # connecting functions video_tab
        self._functions_to_video_tab_buttons()
        #################### END VIDEO TAB ######################

        #################### PLAYLIST TAB ######################
        # connecting function to playlist tab
        self._connect_functions_to_plalist_tab()
        ################## END PLAYLIST TAB ####################

        #################### SETTINGS TAB #######################
        # connecting function to settings tab
        self._connect_functions_to_settings_tab_buttons()
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
        """
        checks if the provided folder_path exists and if this is a directory or not
        >>> self._validate_folder("C:\\") #if the os is windows
        True
        >>> self._validate_folder("/root") #it the os is linux
        False
        """
        return os.path.exists(folder_path) and os.path.isdir(folder_path)

    def _handle_error_on_different_thread(self, error):
        logger.exception(error)
        
        try:
            title = error.title
            message = str(error)
            self._show_alert(title,message,self.ICONS.critical)
        except Exception as e:
            if str(error) == "'formats'":
                self._show_alert("Live video Error",
                                "\nMay be you are trying to download a live straming video which is not possible right now.",
                                self.ICONS.critical)
                self.DB.insert_error(f"Live video download error","User tried to download a live stream."+str(error))
                return
            self._show_alert("Error Occured",
                            str(e)+"\nError Occured on a child Thread.\nMay be you lost internet connection.",
                            self.ICONS.critical)
            self.DB.insert_error(f"_handle_error_on_different_thread",str(error))


#############################################   VIDEO TAB   #############################################
    def _functions_to_video_tab_buttons(self):
        # connecting function to download button
        self.download_video.clicked.connect(self.handle_download_video_clicked)

        # connecting function to load_qualites button
        self.load_qualities.clicked.connect(self.handle_load_qualities_clicked)

        # connecting function to pause_resume button
        self.pause_resume.clicked.connect(self.handle_pause_resume_clicked)

        # connecting function to cancel button
        self.cancel.clicked.connect(self.handle_cancel_clicked)


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
            self.yt_object = self.load_playlist_yt_object(formatted_url) #YouTube(formatted_url)#self.load_yt_object(formatted_url)
            if self.yt_object == formatted_url:
                self._show_alert("Error", "Can't download this video. YouTube didn't respond in time.")
                self._set_video_tab_to_idle()
                return

            #loading qualities to qualities combobox
            self._load_qualities_seperate_thread()

        except exceptions.Invalid_Video_Id as e:
            try:
                self._show_alert(e.title, e.message, self.ICONS.warning)
            except KeyError:
                self._handle_error_on_different_thread(e)
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
            # traceback_object = error_obj.__traceback__
            raise error_obj
            title = error_obj.title
            message = str(error_obj)
            self._show_alert(title, message, self.ICONS.critical)
        except Exception as e:
            logger.exception(e)
            print(e)
            self._show_alert("Error Occured While Downloading", str(e), self.ICONS.critical)

    def handle_download_video_clicked(self):

        if not self._connected_to_internet():
            self._show_alert("Connection Error","You are not connected to internt.\nConnect to internet and try again.")
            return

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
    
    def handle_completed_download(self, file_path):
        self._set_statusbar_text(file_path)
        self.download_video.setEnabled(True)
        self._set_video_tab_to_idle(clear_qualities=False, disable_download=False)
        self.VIDEO_DOWNLOAD_THREAD.exit()
        os.chdir(self.HOST_DIR)

        
#############################################   END VIDEO TAB   #############################################


#############################################   PLAYLIST TAB   ##############################################
    def load_playlist_yt_object(self, video_url):
        yt_obj = None
        try:
            yt_obj = YouTube(video_url)
        except KeyError as e:
            logger.exception("KeyError in load_playlist_yt_object "+str(e))
            print("KeyError in load_playlist_yt_object "+str(e))
            if str(e) == "'streamingData'":
                return video_url
            elif str(e):
                # print("recursing")
                yt_obj = self.load_playlist_yt_object(video_url)
                return yt_obj
            else:
                raise e
        except http.client.RemoteDisconnected as e:
            logger.exception("http.client.RemoteDisconnected in load_playlist_yt_object "+str(e))
            print("http.client.RemoteDisconnected in load_playlist_yt_object "+str(e))
            yt_obj = self.load_playlist_yt_object(video_url)
            return yt_obj
        # except 
        except RecursionError:
            raise exceptions.Connection_Lost
        except pytube.exceptions.RegexMatchError as e:
            logger.exception(e)
            print(e,"recursing")
            yt_obj = self.load_playlist_yt_object(video_url)
            return yt_obj
            raise e
        except Exception as e:
            print(e)
            raise e
        return yt_obj


    def _connect_functions_to_plalist_tab(self):
        # connecting function to download_playlist button
        self.download_playlist.clicked.connect(self.handle_download_playlist_clicked)

        # connecting function to playlist_qualities to get the video qualities
        self.playlist_qualities.currentIndexChanged.connect(self.handle_playlist_qualities_changed)

        self.pause_resume_playlist_video.clicked.connect(self.handle_pause_resume_playlist_video_clicked)

        self.cancel_playlist_video.clicked.connect(self.handle_cancel_playlist_video_clicked)

        self.stop_downloading_playlist.clicked.connect(self.handle_stop_downloading_playlist)



    def _download_video_with_playlist_quality_index(self, playlist_quality_index = 0):
        filter_obj = Stream_Filter(self.playlist_yt_object)
        file_name = self.playlist_yt_object.title
        if self.PLAYLIST_QUALITY_INDEX == 0:
            selected_stream = filter_obj.get_highest_quality_progressive_stream()
            file_name += " audio+video"
        elif self.PLAYLIST_QUALITY_INDEX == 1:
            selected_stream = filter_obj.get_highest_quality_audio_stream()
            file_name += " audio"
        elif self.PLAYLIST_QUALITY_INDEX == 2:
            selected_stream = filter_obj.get_highest_quality_video_stream()
            file_name += " video"
        else:
            raise ValueError("Caller should have handled this")
        
        self.currently_downloading_playlist_video.setText(self.playlist_yt_object.title)

        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD = Download_Thread(self.playlist_yt_object,
                                                    selected_stream, 
                                                    self.DOWNLOADING_PLAYLIST_VIDEO_ID,
                                                    file_name = file_name,
                                                    parent=None
                                                    )
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.progress_updated.connect(self.playlist_video_progress.setValue)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_completed.connect(self.handle_playlist_video_downloaded)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.download_cancelled.connect(self.handle_signal_of_playlist_video_cancellation)
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.error_occured.connect(self.handle_error_while_downloading_playlist_video)

        self.pause_resume_playlist_video.setEnabled(True)
        self.cancel_playlist_video.setEnabled(True)
        self.download_playlist.setDisabled(True)
        # QApplication.processEvents()
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.start()
        self.currently_downloading.setText(f"Downloading {self.playlist_yt_object.title}")



    def handle_error_while_downloading_playlist_video(self, error):
        self.DB.insert_error(f"error while downloading {self.DOWNLOADING_PLAYLIST_VIDEO_ID} playlist_video",str(error))
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()
        self.DOWNLOADED_PLAYLIST_VIDEO_ID = self.DOWNLOADING_PLAYLIST_VIDEO_ID
        self.handle_error_while_downloading(error)
    
    def handle_cancel_playlist_video_clicked(self):
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.cancel_download()
    
    def handle_pause_resume_playlist_video_clicked(self):
        if self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.paused == True:
            self.pause_resume_playlist_video.setText("Pause")
            self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.resume_download()
            return
        self.pause_resume_playlist_video.setText("Resume")
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.pause_download()
    
    def handle_signal_of_playlist_video_cancellation(self):
        # self._set_playlist_tab_to_idle()
        self.CANCELLED_PLAYLIST_VIDEO_ID = self.DOWNLOADING_PLAYLIST_VIDEO_ID
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()

    def handle_playlist_video_downloaded(self, file_path):
        self._set_statusbar_text(file_path)
        # self._set_playlist_tab_to_idle()
        self.DOWNLOADED_PLAYLIST_VIDEO_ID = self.DOWNLOADING_PLAYLIST_VIDEO_ID
        self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()

    def handle_stop_downloading_playlist(self):
        self.SKIP_DOWNLOADING_PLALIST = True

    def handle_playlist_qualities_changed(self):
        self.PLAYLIST_QUALITY_INDEX = self.playlist_qualities.currentIndex()

    def handle_download_playlist_clicked(self):
        self.SKIP_DOWNLOADING_PLALIST = False

        if not self._connected_to_internet():
            self._show_alert("Connection Error","You are not connected to internt.\nConnect to internet and try again.")
            return            

        playlist_id_inpt = self._get_text("playlist_id")
        
        try:
            playlist_id = checkers.check_playlist_id_or_url(playlist_id_inpt)
        except exceptions.Invalid_Playlist_Id as e:
            self._show_alert(e.title, e.message)
            return

        try:
            self.PLAYLIST_VIDEO_IDS,self.PLAYLIST_NAME = playlist_loader.get_video_ids(playlist_id, self.SETTINGS.api_key)
        except exceptions.API_Error as e:
            self._show_alert(e.title, e.message, self.ICONS.critical)
            return

        valid_directory_name_for_playlist = formatters.make_valid_dir_name(self.PLAYLIST_NAME)    
        
        playlist_dir = os.path.join(self.SETTINGS.playlist_dir, valid_directory_name_for_playlist)
        os.makedirs(playlist_dir, exist_ok=True)
        os.chdir(playlist_dir)

        for index, video_id in enumerate(self.PLAYLIST_VIDEO_IDS):
            # print(video_id)
            self.DOWNLOADED_PLAYLIST_VIDEO_ID = None
            self.CANCELLED_PLAYLIST_VIDEO_ID = None
            self.DOWNLOADING_PLAYLIST_VIDEO_ID = video_id

            self.download_playlist.setDisabled(True)
            self.playlist_qualities.setDisabled(True)
            self.pause_resume_playlist_video.setText("Pause")
            self.pause_resume_playlist_video.setDisabled(True)
            self.cancel_playlist_video.setEnabled(True)
            self.stop_downloading_playlist.setEnabled(True)
            
            try:
                #creating self.playlist_yt_object
                formatted_url = formatters.format_video_id_to_url(video_id)
                # QApplication.sendPostedEvents() 
                # QApplication.processEvents()
                self.playlist_yt_object = self.load_playlist_yt_object(formatted_url)
                # print(self.playlist_yt_object,formatted_url)
                # self.playlist_yt_object = YouTube(formatted_url) #self.load_yt_object(formatted_url)
            except exceptions.Invalid_Video_Id as e:
                try:
                    self._show_alert(e.title, e.message, self.ICONS.warning)
                except KeyError:
                    self._handle_error_on_different_thread(e)
            except Exception as e:
                self._handle_error_on_different_thread(e)

            finally:
                if self.playlist_yt_object == formatted_url:
                    continue
                self._set_statusbar_text(f"Loaded {self.playlist_yt_object.title}")

            if self.PLAYLIST_QUALITY_INDEX <= 2:
                self._download_video_with_playlist_quality_index(self.PLAYLIST_QUALITY_INDEX)
            elif self.PLAYLIST_QUALITY_INDEX == 3:
                self._download_video_with_playlist_quality_index(1)
                self._download_video_with_playlist_quality_index(2)
            
            self.playlist_video_number.setText(f"Downloading {index+1}/{len(self.PLAYLIST_VIDEO_IDS)} of {self.PLAYLIST_NAME}")
            
            while not self.DOWNLOADED_PLAYLIST_VIDEO_ID==video_id and not self.CANCELLED_PLAYLIST_VIDEO_ID==video_id and not self.SKIP_DOWNLOADING_PLALIST:
                QApplication.sendPostedEvents() 
                QApplication.processEvents()
                sleep(self.SLEEP_TIME)
                if self.SKIP_DOWNLOADING_PLALIST==True:
                    self.DOWNLOADED_PLAYLIST_VIDEO_ID=video_id
                    break
        
            if self.SKIP_DOWNLOADING_PLALIST==True:
                break
        if self.SKIP_DOWNLOADING_PLALIST:
            #stoping download of the current video
            self.handle_cancel_playlist_video_clicked()
            self.PLAYLIST_VIDEO_DOWNLOAD_THREAD.exit()
        self._set_playlist_tab_to_idle()
        if index+1==len(self.PLAYLIST_VIDEO_IDS):
            self._show_alert("Downloaded Playlist",
                             f"Successfully downloaded the palylist.\nSaved to: {playlist_dir}")


        # self.playlist_video_progress.setValue(0)

        # self.download_playlist.setEnabled(True)
        # self.playlist_qualities.setEnabled(True)

    

###########################################   END PLAYLIST TAB   ############################################




#############################################   SETTINGS TAB   #############################################
    def _connect_functions_to_settings_tab_buttons(self):
        # connecting function to videos_location_browse button
        self.videos_location_browse.clicked.connect(self.handle_videos_location_browse)

        # connecting function to playlists_location_browse button
        self.playlists_location_browse.clicked.connect(self.handle_playlists_location_browse)

        # connecting function to save_settigs button
        self.save_settings.clicked.connect(self.write_settings)
        
        self.api_key.editingFinished.connect(self.write_settings)



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
#     sys.exit(app.exec_())

def main():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = APP(MainWindow)
    ui.show()
    exit_code = app.exec_()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
