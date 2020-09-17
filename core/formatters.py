import re
import random


def format_video_id_to_url(id):
    return f"https://www.youtube.com/watch?v={id}"

def format_playlist_id_to_url(id):
    return f"https://www.youtube.com/playlist?list={id}"










def _string_generator(length=10):
    string = " "
    for i in range(length):
        string += chr(random.randint(65,91))
    return string


patt = re.compile(r"[\x00-\x1F<>/?|*\":/\\\ue063]",flags=re.MULTILINE) #all invalid characters detector regex for windows dir name

RESERVED_WORDS = ["CON", "PRN", "AUX", "NUL" "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]

def make_valid_dir_name(directory_name):
    if len(directory_name) in set([len(words) for words in RESERVED_WORDS]):
        if directory_name.upper() in RESERVED_WORDS:
            return directory_name + _string_generator()
    valid_name = re.sub(patt,"",directory_name)
    return valid_name