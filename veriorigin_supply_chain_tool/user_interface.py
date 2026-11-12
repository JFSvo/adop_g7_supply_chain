import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(__file__).resolve().parent / "VeriOrigin_logo.png"

class stackedExample(QWidget):

    def __init__(self):
        super(stackedExample, self).__init__()
        self.selected_file = None

        self.Stack = QStackedWidget()
        self.stack1 = QWidget()
        self.stack2 = QWidget()
        self.stack3 = QWidget()
        
        self.stack1UI()
        self.stack2UI()
        
        self.Stack.addWidget (self.stack1)
        self.Stack.addWidget (self.stack2)
        
        hbox = QHBoxLayout(self)
        hbox.addWidget(self.Stack)

        self.setLayout(hbox)
        self.setGeometry(300, 50, 10,10)
        self.setWindowTitle('VeriOrigin Analyzer')
        self.show()
        

    def stack1UI(self):
        layout = QVBoxLayout()

        logo = QLabel()
        pixmap = QPixmap(str(LOGO_PATH))
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.addWidget(logo)

        layout.addSpacing(20)

        file_dialog_button = QPushButton("Analyze Session")
        file_dialog_button.clicked.connect(self.choose_file)
        layout.addWidget(file_dialog_button, alignment=Qt.AlignHCenter)

        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        layout.addWidget(quit_button, alignment=Qt.AlignHCenter)

        layout.addStretch()  # pushes everything to the top
        self.stack1.setLayout(layout)
        
    def stack2UI(self):
        layout = QFormLayout()
        sex = QHBoxLayout()
        sex.addWidget(QRadioButton("Male"))
        sex.addWidget(QRadioButton("Female"))
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.set_current_index(0))
        layout.addRow(back_button)
        layout.addRow(QLabel("Sex"),sex)
        layout.addRow("Date of Birth",QLineEdit())

        self.stack2.setLayout(layout)
        
    def set_current_index(self,i):
        self.Stack.setCurrentIndex(i)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Session to Analyze",
            str(PROJECT / "corpus"),
            "JSON Lines (*.jsonl)",
        )
        if path:
            self.selected_file = path
            self.Stack.setCurrentIndex(1)

def choose_session():
    app = QApplication.instance() or QApplication(sys.argv)
    window = stackedExample()
    window.show()
    app.exec()
    return window.selected_file