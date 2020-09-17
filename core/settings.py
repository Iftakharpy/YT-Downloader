import os
import json
from .database import Database


file_name = "settings.json"

class Settings:
    #to log errors
    DB = Database()
    HOME_DIR = os.path.expanduser("~")

    DEFAULT_SETTINGS = {
        "YOUTUBE_API_KEY": "Your YouTube API key",
        "VIDEO_DOWNLOAD_DIR": os.path.join(HOME_DIR, "Downloads/YouTube/Videos"),
        "PLAYLIST_DOWNLOAD_DIR": os.path.join(HOME_DIR, "Downloads/YouTube/Playlists")
    }

    settings_file_path = os.path.join(os.path.dirname(__file__), file_name)

    def __init__(self):
        self.api_key = None
        self.video_dir = None
        self.playlist_dir = None

        #loading settings
        self.load_settings()

    def __str__(self):
        text = "\n"
        for key,values in self._get_settings_as_dict().items():
            text += f"{key.ljust(21,' ')} = {values}\n"
        text+="\n"
        return text
        

    def _get_settings_as_dict(self):
        if not all([self.api_key, self.video_dir, self.playlist_dir]):
            return self.DEFAULT_SETTINGS
        settings_dict = {}
        settings_dict["YOUTUBE_API_KEY"] = self.api_key
        settings_dict["VIDEO_DOWNLOAD_DIR"] = self.video_dir
        settings_dict["PLAYLIST_DOWNLOAD_DIR"] = self.playlist_dir
        return settings_dict

    def _format_settings_dict_to_json(self):
        return json.dumps(self._get_settings_as_dict(), indent=4)

    def _load_json_file(self, file_name=settings_file_path):
        try:
            with open(file_name, "r") as settings:
                loaded = json.loads(settings.read())
            return loaded
    
        except Exception as e:
            self.DB.insert_error("Settings Error from settings.py", str(e))
            raise e


    def load_settings(self):
        if os.path.exists(self.settings_file_path) and os.path.isfile(self.settings_file_path):
            settings = self._load_json_file()
            self.api_key = settings["YOUTUBE_API_KEY"]
            self.video_dir = settings["VIDEO_DOWNLOAD_DIR"]
            self.playlist_dir = settings["PLAYLIST_DOWNLOAD_DIR"]
        else:
            self.save_settings()
            self.load_settings()

    def save_settings(self):
        with open(self.settings_file_path, "w") as settings:
            settings.write(self._format_settings_dict_to_json())

    ###################### SETTERS AND GETTERS ######################
    @property
    def get_api_key(self):
        return self.api_key

    @get_api_key.setter
    def set_api_key(self, youtube_api_key):
        self.api_key = youtube_api_key
        self.save_settings()
    
    @property
    def get_video_dir(self):
        return self.video_dir

    @get_video_dir.setter
    def set_video_dir(self, directory_path):
        self.video_dir = directory_path
        self.save_settings()
    
    @property
    def get_playlist_dir(self):
        return self.playlist_dir

    @get_playlist_dir.setter
    def set_playlist_dir(self, directory_path):
        self.playlist_dir = directory_path
        self.save_settings()


def main():
    settings = Settings()
    for key,values in settings._get_settings_as_dict().items():
        print(key.ljust(21," "), "=", values)

if __name__ == "__main__":
    main()