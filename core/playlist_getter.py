import bs4
import re # to check playlist id
import requests # to request youtubue api to get data
import os # to get api key from environment variable
import json # to parse json to python dictionary
from collections import namedtuple,Counter
from . import settings


SETTINGS = settings.Settings()
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/playlistItems"


def format_playlist_url(playlist_id):
    return f"https://www.youtube.com/playlist?list={playlist_id}"