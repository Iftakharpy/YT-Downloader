#base module for custom exceptions

class Invalid_API_Key(Exception):
    title = "Invalid YouTube API key"
    message = "Currently saved api key is invalid"
    def __init__(self, message=None):
        if message:
            self.message = message
    
    def __str__(self):
        return {self.message}

class API_Error(Exception):
    title = "YouTube DATA API Error"
    message = "this should be updated"
    def __init__(self, message):
        self.message = message
    
    def __str__(self):
        return self.message


class Invalid_Video_Id(Exception):
    title = "Invalid Video URL/ID"
    message = "You entered an invalid video URL/ID"
    def __init__(self, message = None):
        if message:
            self.message = message

    def __str__(self):
        return self.message


class Invalid_Playlist_Id(Exception):
    title = "Invalid Playlist URL/ID"
    message = "You entered an invlaid playlist URL/ID"
    def __init__(self, message = None):
        if message:
            self.message = message

    def __str__(self):
        return self.message


class Video_Is_Not_Avalilabe(Exception):
    title = "Unavailable video"
    message = "This Video is not availabe"
    details = "Video is private or deleted by the owner."

    def __str__(self):
        return f"{self.message}\n{self.details}"


class Download_Cancelled(Exception):
    title = "Download cancelled"
    message = "You have cancelled downloading the video"
    def __init__(self, message = None):
        if message:
            self.message = message

    def __str__(self):
        return self.message


class Connection_Lost(Exception):
    title = "Connection Lost"
    message = "You have lost your network connection. Connect to a network and try again."
    def __init__(self, message=None):
        if message:
            self.message = message
    
    def __str__(self):
        return self.message


class Unknown_Error(Exception):
    title = "Unknown Error Occoured"
    message = "A new error occured inform the developers about this."
    def __init__(self, message=None):
        if message:
            self.message = message
    
    def __str__(self):
        return self.message