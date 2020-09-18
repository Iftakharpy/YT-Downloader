import re
import requests
# import exceptions
from . import exceptions



######################################################  VIDEO  ######################################################
# reference for video_url_regex https://regex101.com/r/OY96XI/5
video_url_regex = re.compile(r"(?<=v=)([a-zA-Z0-9-_]{11})(?:&|$)", flags=re.MULTILINE)
video_id_regex = re.compile(r"(^[a-zA-Z0-9-_]{11}$)")

def check_video_id_or_url(video_id_or_url):
    
    #assuming user passed a video_id
    if len(video_id_or_url)==11:
        video_id = video_id_regex.findall(video_id_or_url)
        if len(video_id)==1:
            return video_id[0]

        # raising exception for invalid inpt
        raise exceptions.Invalid_Video_Id()

    #assuming user passed a url for video
    video_id = video_url_regex.findall(video_id_or_url)
    if len(video_id)==1:
        return video_id[0]

    # raising exception for invalid inpt
    raise exceptions.Invalid_Video_Id()




######################################################  PLAYLIST  ######################################################
playlist_url_regex = re.compile(r"(?<=list=)[a-zA-Z0-9-_]+?(?=&|$)")
playlist_id_regex = re.compile(r"^[a-zA-Z0-9-_]+$")

def check_playlist_id_or_url(playlist_id_or_url):

    #assuming user passed a palylist_id
    if 12<=len(playlist_id_or_url)<=43:
        playlist_id= playlist_id_regex.findall(playlist_id_or_url)
        if len(playlist_id)==1:
            return playlist_id[0]

        # raising exception for invalid inpt
        raise exceptions.Invalid_Playlist_Id()

    #assuming user passed a url for playlist
    playlist_id = playlist_url_regex.findall(playlist_id_or_url)
    if len(playlist_id)==1:
        return playlist_id[0]

    # raising exception for invalid inpt
    raise exceptions.Invalid_Playlist_Id()


######################################################  API KEY  ######################################################
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/playlistItems"

def check_api_key(self, api_key):
    params = {
        "key": api_key,  # api_key to authenticate
        "part": "contentDetails",  # defining the details level
        "playlistId": "PLnrO9iqgTHN-ub7YeZw7Aheo7e0yX5JSH"  # setting the playlist id
    }
    if len(api_key) == 39:
        response = requests.get(YOUTUBE_API_URL, params=params)
        if response.status_code <= 399:
            return api_key
    raise exceptions.Invalid_API_Key()