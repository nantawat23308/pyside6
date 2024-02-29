import logging
import time
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, Qt, QObject, Signal, Slot, QRunnable, QThreadPool, QTime, QThread, QReadWriteLock
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget, \
    QGridLayout, QLineEdit, QFrame, QTextEdit, QFormLayout, QProgressBar, QCheckBox, QComboBox, QDialogButtonBox, \
    QMessageBox, QGroupBox, QScrollArea, QScrollerProperties, QDialog, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QImage
import cv2
from PIL import ImageFont, ImageDraw, Image
import numpy as np

ROOT_DIR = Path(__file__).parent.parent
IMG_PATH = ROOT_DIR.joinpath('image')

logging = logging.getLogger(__name__)


class askQuestion(QWidget):
    def __init__(self, question, picture=None, **kwargs):
        super().__init__(**kwargs)
        self.layoutV = QVBoxLayout()
        self.layoutH = QHBoxLayout()
        self.image_form = QLabel()
        self.picture = picture
        if self.picture is not None:
            self.img = QPixmap(picture)
        self.label = QLabel(question)
        self.answer = 'Yes'
        self.init_ui()
        self.show()

    def init_ui(self):
        if self.picture is not None:
            self.set_pic()
        self.layoutV.addWidget(self.label)
        # Img and Question
        # answer
        button = QPushButton(self.answer)
        button.setFixedSize(300, 50)
        self.layoutH.addWidget(button)

        self.layoutV.addLayout(self.layoutH)
        self.setLayout(self.layoutV)

    def set_pic(self):
        self.image_form.setFixedSize(500, 500)
        self.img.scaled(500, 500, Qt.AspectRatioMode.IgnoreAspectRatio)
        self.image_form.setPixmap(self.img)
        self.layoutV.addWidget(self.image_form)


def ask_question(question, picture):
    if picture is None:
        picture = IMG_PATH.joinpath("1.jpg")
    # app = QApplication(sys.argv)
    logging.info(question)
    wid = askQuestion(question=question, picture=picture)
    # sys.exit()


def draw_text(img, text,
              font=cv2.FONT_HERSHEY_COMPLEX_SMALL,
              pos=(10, 10),
              font_scale=2,
              font_thickness=2,
              text_color=(0, 255, 0),
              text_color_bg=(0, 0, 0)):
    x, y = pos
    text_size, _ = cv2.getTextSize(text, font, font_scale, font_thickness)
    text_w, text_h = text_size
    cv2.rectangle(img, pos, (x + text_w + 10, y + text_h + 15), text_color_bg, -1)
    cv2.putText(img, text, (x, y + text_h + font_scale - 1), font, font_scale, text_color, font_thickness)

    return text_size


def display_img(question, picture):
    logging.info(question)
    picture = str(picture)
    img = cv2.imread(picture)
    img = cv2.resize(img, (1200, 800))
    draw_text(img, text=question)
    window_name = question
    cv2.imshow(window_name, img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    # ask_question(question='hello', picture=IMG_PATH.joinpath("3.jpg"))
    display_img(question='Clean and Inspect Optic Cable', picture=IMG_PATH.joinpath("OPM.JPG"))

