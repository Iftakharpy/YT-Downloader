import os
import sqlite3


def connection_decorator(fn):
    def inner(*args, **kwargs):
        connection = sqlite3.connect(Database.DB_NAME)
        cursor = connection.cursor()

        return_value = fn(*args, **kwargs, cursor=cursor)

        connection.commit()
        connection.close()
        return return_value
    return inner

BASE_DIR = os.path.dirname(__file__)


class Database:
    DB_NAME = os.path.join(BASE_DIR, "data.db")
    def __init__(self, db_name=None):
        f"""
        db_name is database file name.
        if db_name is not specified the default name will be "{self.DB_NAME}"
        """
        if db_name and type(db_name)==str:
            if db_name.endswith(".db"):
                self.DB_NAME = os.path.join(BASE_DIR, db_name)
            else:
                self.DB_NAME = os.path.join(BASE_DIR, db_name+".db")
        
        #making sure the database exists
        self.__create_database_if_it_does_not_exists()


    def __create_database_if_it_does_not_exists(self):
        if not os.path.exists(Database.DB_NAME) or os.path.getsize(Database.DB_NAME)==0:
            self.create_database()


    TABLES = {  #identifiers:table names
                "API_Keys":"api_keys",
                "Playlists":"playlists",
                "Videos":"videos",
                "Errors":"errors"
                }

    ###########################################################################################################################
    #SCHEMAS FOR THE TALBES
    API_Keys_schema = f"""CREATE TABLE {TABLES["API_Keys"]}(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT
    );
    """

    Playlists_schema = f"""CREATE TABLE {TABLES["Playlists"]}(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id TEXT,
        download_path TEXT,
        name TEXT,
        is_downloaded TINYINT(1) DEFAULT 0
    );
    """

    Videos_schema = f"""CREATE TABLE {TABLES["Videos"]}(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        playlist_id TEXT,
        is_downloaded TINYINT(1) DEFAULT 0,

        FOREIGN KEY(playlist_id) REFERENCES {TABLES["Playlists"]}(playlist_id)
    );
    """

    Errors_schema = f"""CREATE TABLE {TABLES["Errors"]}(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        error_description TEXT,
        dt time default current_timestamp,

        FOREIGN KEY(video_id) REFERENCES {TABLES["Videos"]}(video_id)
    );
    """

    ###########################################################################################################################
    #insert statements
    INSERT_API_Key = f"""INSERT INTO {TABLES["API_Keys"]}("key") VALUES(?);"""
    INSERT_Playlist = f"""INSERT INTO {TABLES["Playlists"]}("playlist_id", "download_path", "name") VALUES(?, ?, ?);"""
    INSERT_Video = f"""INSERT INTO {TABLES["Videos"]}("video_id", "playlist_id") VALUES(?, ?);"""
    INSERT_Error = f"""INSERT INTO {TABLES["Errors"]}("video_id", "error_description") VALUES(?, ?);"""

    ###########################################################################################################################
    #select statemets
    SELECT_API_Keys = f"""SELECT * FROM {TABLES["API_Keys"]};"""
    SELECT_Playlists = f"""SELECT * FROM {TABLES["Playlists"]};"""
    SELECT_Playlist_id = f"""SELECT playlist_id FROM {TABLES["Playlists"]} WHERE id=(?);"""
    SELECT_Playlist_info = f"""SELECT * FROM {TABLES["Playlists"]} WHERE playlist_id=(?) OR id=(?);"""
    SELECT_Playlist_name_by_playlist_id = f"""SELECT name FROM {TABLES["Playlists"]} WHERE playlist_id=(?);"""
    SELECT_Videos = f"""SELECT * FROM {TABLES["Videos"]};"""
    SELECT_Videos_by_playlist_id = f"""SELECT video_id FROM {TABLES["Videos"]} WHERE playlist_id=(?);"""
    SELECT_Video_info = f"""SELECT * FROM {TABLES["Videos"]} WHERE video_id=(?) OR id=(?);"""
    SELECT_Errors = f"""SELECT * FROM {TABLES["Errors"]};"""

    ###########################################################################################################################
    #update statements
    UPDATE_API_Key = f"""UPDATE {TABLES["API_Keys"]} SET key=(?) WHERE id=(?) OR key=(?);"""
    UPDATE_Playlist_download_status = f"""UPDATE {TABLES["Playlists"]} SET is_downloaded=(?) WHERE id=(?) OR playlist_id=(?);"""
    UPDATE_Playlist_download_path = f"""UPDATE {TABLES["Playlists"]} SET download_path=(?) WHERE id=(?) OR playlsit_id=(?);"""
    UPDATE_Video_download_status = f"""UPDATE {TABLES["Videos"]} SET is_downloaded=(?) WHERE id=(?) OR video_id=(?) OR playlist_id=(?);"""

    ###########################################################################################################################
    #delete statements
    DELETE_API_Key = f"""DELETE FROM {TABLES["API_Keys"]} WHERE id=(?) OR key=(?);"""
    DELETE_Playlist = f"""DELETE FROM {TABLES["Playlists"]} WHERE id=(?) OR playlist_id=(?);"""
    DELETE_Videos_by_playlist_id = f"""DELETE FROM {TABLES["Videos"]} WHERE playlist_id=(?);"""
    DELETE_Video = f"""DELETE FROM {TABLES["Videos"]} WHERE video_id=(?) or id=(?);"""


    ###########################################################################################################################
    @connection_decorator
    def create_database(self, cursor="Don't provide value for this"):
        for table in self.TABLES:
            sql_command = getattr(self, f"{table}_schema")
            # print(sql_command)
            cursor.execute(sql_command)


    ###########################################################################################################################
    #api_keys
    @connection_decorator
    def get_api_keys(self, cursor="Don't provide value for this"):
        results = cursor.execute(self.SELECT_API_Keys).fetchall()
        return results

    @connection_decorator
    def insert_api_key(self, api_key, cursor="Don't provide value for this"):
        cursor.execute(self.INSERT_API_Key, (api_key,))

    @connection_decorator
    def update_api_key(self, new_api_key, old_api_key=None, id=None, cursor="Don't provide value for this"):
        """
        Will search by id and old_api_key perameter.\n
        If any record matches with (id==id) OR (key==old_api_key)\n
        the record will be replaced with new_api_key perameter.
        """
        cursor.execute(self.UPDATE_API_Key, (new_api_key, id, old_api_key))

    @connection_decorator
    def delete_api_key(self, api_key=None, id=None, cursor="Don't provide value for this"):
        """
        Will search by id and old_api_key perameter.\n
        If any record matches with (id==id) OR (key==api_key)\n
        the record will be deleted.
        """
        cursor.execute(self.DELETE_API_Key, (id, api_key))


    ###########################################################################################################################
    #playlists
    @connection_decorator
    def get_playlists(self, cursor="Don't provide value for this"):
        results = cursor.execute(self.SELECT_Playlists).fetchall()
        return results
    
    @connection_decorator
    def get_playlist_name(self,playlist_id, cursor="Don't provide value for thi"):
        return cursor.execute(self.SELECT_Playlist_name_by_playlist_id, (playlist_id,)).fetchone()

    @connection_decorator
    def get_playlist_info(self, playlist_id=None, id=None, cursor="Don't provide value for this"):
        pl_info = cursor.execute(self.SELECT_Playlist_info, (playlist_id, id)).fetchone()
        return pl_info

    @connection_decorator
    def get_playlist_id(self, id, cursor="Don't provide value for this"):
        playlist_id = cursor.execute(self.SELECT_Playlist_id, (id,)).fetchone()
        return playlist_id

    @connection_decorator
    def insert_playlist(self, playlist_id, download_path, playlist_name, cursor="Don't provide value for this"):
        cursor.execute(self.INSERT_Playlist, (playlist_id, download_path, playlist_name))
    
    @connection_decorator
    def update_playlist_download_status(self, is_downloaded=0, playlist_id=None, id=None, cursor="Don't provide value for this"):
        """
        If the value of is_downloaded is set to 1 then the playlist will be treated as downloaded.
        Else is_downloaded is set to 0 the playlist will be treated as not downloaded.
        """
        cursor.execute(self.UPDATE_Playlist_download_status, (is_downloaded, id, playlist_id))
    
    @connection_decorator
    def update_playlist_download_path(self, download_path, playlist_id=None, id=None, cursor="Don't provide value for this"):
        cursor.execute(self.UPDATE_Playlist_download_path, (download_path, id, playlist_id))

    @connection_decorator
    def delete_playlist(self, playlist_id=None, id=None, cursor="Don't provide value for this"):
        if playlist_id:
            cursor.execute(self.DELETE_Playlist, (id, playlist_id))
            self.delete_videos_by_playlist_id(playlist_id)
        elif id:
            playlist_id = self.get_playlist_id(id)
            self.delete_videos_by_playlist_id(playlist_id)
            cursor.execute(self.DELETE_Playlist, (id, playlist_id))


    ###########################################################################################################################
    #videos
    @connection_decorator
    def get_all_videos(self, cursor="Don't provide value for this"):
        results = cursor.execute(self.SELECT_Videos).fetchall()
        return results
    
    @connection_decorator
    def get_videos_by_playlist_id(self, playlist_id, cursor="Don't provide value for this"):
        videos = cursor.execute(self.SELECT_Videos_by_playlist_id, (playlist_id,)).fetchall()
        return videos

    @connection_decorator
    def get_video_info(self, video_id=None, id=None, cursor="Don't provide value for this"):
        vid_info = cursor.execute(self.SELECT_Video_info, (video_id, id)).fetchone()
        return vid_info

    @connection_decorator
    def insert_video(self, video_id, playlist_id, cursor="Don't provide value for this"):
        cursor.execute(self.INSERT_Video, (video_id, playlist_id))
    
    @connection_decorator
    def insert_videos(self, videos, cursor="Don't provide value for this"):
        """
        videos should contain tuples in (video_id, playlist_id) format as an iterable.
        """
        cursor.executemany(self.INSERT_Video, videos)
    
    @connection_decorator
    def update_video_download_status(self, is_downloaded=0, video_id=None, playlist_id=None, id=None, cursor="Don't provide value for this"):
        cursor.execute(self.UPDATE_Video_download_status, (is_downloaded, id, video_id, playlist_id))
    
    @connection_decorator
    def delete_video(self, video_id=None, id=None, cursor="Don't provide value for this"):
        cursor.execute(self.DELETE_Video, (video_id, id))

    @connection_decorator
    def delete_videos_by_playlist_id(self, playlist_id=None, cursor="Don't provide value for this"):
        cursor.execute(self.DELETE_Videos_by_playlist_id, (playlist_id,))


    ###########################################################################################################################
    #errors
    @connection_decorator
    def insert_error(self, video_id, error_description, cursor="Don't provide value for this"):
        cursor.execute(self.INSERT_Error, (video_id, error_description))

    @connection_decorator
    def get_errors(self, cursor="Don't provide value for this"):
        results = cursor.execute(self.SELECT_Errors).fetchall()
        return results
