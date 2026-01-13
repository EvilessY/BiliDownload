import sys
import os

os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    font = QFont('Microsoft YaHei', 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
