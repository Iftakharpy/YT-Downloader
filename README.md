# To compile/convert gui.ui file to python file use command
> pyuic5 -x gui.ui -o gui.py

# To compile/convert resources.qrc file to python use command
> pyrcc5 resources.qrc -o resources_rc.py

## Syntax for resource files(resources.qrc)
```qrc
<!DOCTYPE RCC>
<RCC version="1.0">
    <qresource>
        <file>icons/download.svg</file>
        <file>icons/youtube.svg</file>
        <file>relative file path from resources.qrc</file>
    </qresource>
</RCC>
```


# To import the class from "gui.py" file in some other python file use the following boiler plate
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