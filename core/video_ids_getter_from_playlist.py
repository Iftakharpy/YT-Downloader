import bs4
import re # to check playlist id
import requests # to request youtubue api to get data
import os # to get api key from environment variable
import json # to parse json to python dictionary
from collections import namedtuple,Counter
from . import settings
from . import formatters
from .exceptions import API_Error
from .database import Database


SETTINGS = settings.Settings()
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/playlistItems"
VIDEO_IDS = []
DB = Database()



def extract_video_ids(json_res):
    video_ids = []
    for playlist_item in json_res["items"]:
        video_ids.append(playlist_item["contentDetails"]["videoId"])
    return video_ids



def get_playlist_name(playlist_id):
    page = requests.get(formatters.format_playlist_id_to_url(playlist_id))
    soup = bs4.BeautifulSoup(page.text,features="html.parser")

    palylist_title = soup.find("title").text.rsplit("-",1)[0].strip()

    return palylist_title



def get_video_ids(playlist_id, api_key, api=YOUTUBE_API):
    global VIDEO_IDS
    params = {
        "key":api_key,              #api_key to authenticate
        "part":"contentDetails",    #defining the details level 
        "maxResults":9999,           #result
        "playlistId":playlist_id    #playlist id to specify the playlist
    }

    #reuesting data from youtube api
    res = requests.get(api,params)
    if 400<=res.status_code<=600:
        DB.insert_error("YouTube API Error", str(res.json()))
        message = json.loads(res.text)["error"]["message"]
        raise API_Error(message)
    #parsing the response data from json format to python dictionary
    json_res = json.loads(res.text)

    #reference to the next page to get all resuslts
    next_page_token = json_res.get("nextPageToken")

    #youtube video ids
    VIDEO_IDS = []
    #adding video ids to video_ids array
    VIDEO_IDS.extend(Counter(extract_video_ids(json_res))) #using counter to remove duplicate video_ids

    #Navigating to all the pages to get all the video ids
    while next_page_token:
        params["pageToken"] = next_page_token

        #getting data from youtube api
        res = requests.get(api,params)
        #parsing the response data from json format to python dictionary
        json_res = json.loads(res.text)
        
        #adding ids to video_ids
        # video_ids.extend(get_video_ids(json_res)) #this doesn't removes duplcate video id
        VIDEO_IDS.extend(Counter(extract_video_ids(json_res)))    #not adding any duplicate ids
        
        #ref to next page
        next_page_token = json_res.get("nextPageToken")

    return VIDEO_IDS
