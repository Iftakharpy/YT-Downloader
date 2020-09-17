import pytube
import urllib
import json

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from .database import Database
from .checkers import check_video_id_or_url
from . import exceptions

DB = Database()


class Logger_Decorator_For_Download_Func(QObject):
    completed = pyqtSignal()
    MAX_RECURSIVE_CALLS = 700
    def __init__(self, download_func, video_id, parent=None):
        super().__init__(parent=parent)
        self.f = download_func
        self.video_id = video_id

    def run(self, *args, **kwargs):
        """
        Always provide video_id in the first argument otherwise this function will break.
        """
        try:
            return_value = self.f(*args, **kwargs)
            self.completed.emit()
            return return_value
        
        except exceptions.Download_Cancelled as e:
            return e.message
        except exceptions.Connection_Lost as e:
            return str(e)
    
        except ConnectionAbortedError as e:
            DB.insert_error(self.video_id, error_description=str(e)+"\nVideo is not accessible.")
            return exceptions.Connection_Lost.message

        #pytube.exceptions.RegexMatchError occurs when youtube video is private or deleted by the owner
        except pytube.exceptions.RegexMatchError as e:
            
            DB.insert_error(self.video_id, error_description=str(e)+"\nVideo is not accessible.")
            raise exceptions.Connection_Lost


        #RECURSION
        #json.decoder.JSONDecodeError occurs when TCP packes doesn't arive in time
        except json.decoder.JSONDecodeError as e:
            
            DB.insert_error(self.video_id, error_description=str(e)+"\njson.decoder.JSONDecodeError raised trying again.\nInternet connection lost")
            
            #recursing
            self.f(*args, **kwargs)


        #RECURSION
        #TimeoutError occurs when reply from server doesn't arives in time
        #If the internet connection is available and other error dosn't occurs.
        except TimeoutError as e:
            
            DB.insert_error(self.video_id, error_description=str(e)+"\nTimeoutError raised trying again.\nInternet connection lost")
            
            #recursing
            self.f(*args, **kwargs)


        #RECURSION But not pure recursion (it's a mixed bag)
        #urllib.error.URLError occurs randomly I don't know why but if you keep trying again it it will work.
        #If the internet connection is available and other error dosn't occurs.
        except urllib.error.URLError as e:
            
            DB.insert_error(self.video_id, error_description=str(e)+"\nurllib.error.URLError raised trying again.\nInternet connection lost")
            
            #recursing for until MAX_RECURSIVE_CALLS limit is reached 
            for i in range(self.MAX_RECURSIVE_CALLS):
                try:
                    #recrusing
                    res = self.f(*args, **kwargs)
                    return res
                #if the same error raises trying again
                except urllib.error.URLError as e:
                    continue

                #if a different error occurs then recursing to let the same function handle the error
                except Exception:
                    #recursing
                    self.f(*args, **kwargs)
            else:
                
                DB.insert_error(self.video_id, error_description=str(e)+"\nYou have lost internet connection. Check your network connection.\nInternet connection lost.")

                #raising internet connection lost error because he hit the limit and assuming host lost network connection
                raise exceptions.Connection_Lost


        #RECURSION
        #KeyError occurs randomly I don't know why but if you keep trying again it it will work.
        #If the internet connection is available and other error dosn't occurs.
        except KeyError as e:
            print('KeyError raised trying again.')
            
            DB.insert_error(self.video_id, error_description=str(e)+"\nKeyError raised trying again.\nInternet connection lost")
            
            #recursing
            self.f(*args, **kwargs)


        #if all of the above recursive error catching fails and raises RecursionError then host must have lost network connection
        except RecursionError:
            raise exceptions.Connection_Lost


        #this error occurs when internet connection is lost
        except Exception as e:
            try:
                
                if e.errno == e.winerror == 10051:
                    DB.insert_error(self.video_id, error_description=str(e)+"\nInternet connection lost")
                    raise exceptions.Connection_Lost
                else:
                    DB.insert_error(self.video_id, error_description=str(e)+"\nDon't know what happend try again a few moments later.")
                    raise exceptions.Unknown_Error


            #this error occurs when Exception "e" doesn't have errno or winerror attribute
            except Exception as e:
                    DB.insert_error(self.video_id, error_description=str(e)+"\nDon't know what happend new error.")
                    raise e
                    # raise exceptions.Unknown_Error
