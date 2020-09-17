# YT Downloader downloads video and playlist from YouTube
>YT Downloader uses the video url/id to download videos
>To download playlists it requires an api key of Youtube Data API v3
>It uses the api key to get video ids from playlist to get an api key visit [the link](https://rapidapi.com/blog/how-to-get-youtube-api-key/).

<br>
<br>

## To compile/convert final_gui.ui file to GUI.py python file use command
> pyuic5 -x final_gui.ui -o GUI.py

<br>

## To compile/convert resource.qrc file to python use command
> pyrcc5 resource.qrc -o resource_rc.py

<br>

## Syntax for resource files(resource.qrc)
```qrc
<!DOCTYPE RCC>
<RCC version="1.0">
    <qresource>
        <file>icons/download.svg</file>
        <file>icons/youtube.svg</file>
        <file>relative file path from resource.qrc</file>
    </qresource>
</RCC>
```

<br>

## To import the class from "gui.py" file in some other python file use the following boiler plate
```python
from PyQt5.QtWidgets import QMainWindow
#importing gui class from pyuic5 auto genereated python code
from generated_file import generated_class as Window

class Class_Name(QMainWindow, Window, object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #settings up the window form gui folder
        self.setupUi(self)
        
        # initialize anything
    
    # make required methods for your application


def main():
    import sys
    #defining the main thread
    app = QtWidgets.QApplication(sys.argv)

    #making the window
    window = Class_Name()
    #rendering the window
    window.show()

    #running main loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
```