import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from pathlib import Path

# PySide GUI front end configuration for VeriOrigin

PROJECT = Path(__file__).resolve().parent.parent
LOGO_PATH = Path(__file__).resolve().parent / "VeriOrigin_logo.png"

INITIAL_DIMENSION = (300, 50, 10, 10)
SCREEN_DIMENSIONS = [(10, 10), (10, 700)]

class VeriOrigin_UI(QWidget):

    file_selected = Signal(str)

    def __init__(self):
        super(VeriOrigin_UI, self).__init__()
        self.selected_file = None
        self.stored_text = dict()

        self.Stack = QStackedWidget()
        self.menu_screen = QWidget()
        self.results_screen = QWidget()

        self.page_results = QWidget()
        
        self.menu_UI()
        self.results_UI()
        
        self.Stack.addWidget (self.menu_screen)
        self.Stack.addWidget (self.results_screen)
        
        hbox = QHBoxLayout(self)
        hbox.addWidget(self.Stack)

        self.setLayout(hbox)
        self.setGeometry(*INITIAL_DIMENSION)
        self.setWindowTitle('VeriOrigin Analyzer')
        self.show()
        

    def menu_UI(self):
        layout = QVBoxLayout()

        logo = QLabel()
        pixmap = QPixmap(str(LOGO_PATH))
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.addWidget(logo)

        layout.addSpacing(20)

        file_dialog_button = QPushButton("Analyze Session")
        file_dialog_button.clicked.connect(self.choose_log)
        layout.addWidget(file_dialog_button, alignment=Qt.AlignHCenter)

        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        layout.addWidget(quit_button, alignment=Qt.AlignHCenter)

        layout.addStretch()  # pushes everything to the top
        self.menu_screen.setLayout(layout)
        
    def results_UI(self):
        layout = QFormLayout()
        self.tabs = QTabWidget()
        self.tab_views = {}
        for name in ("Trace", "Dependency Findings", "Early Signals", "Boundary Findings"):
            view = QTextEdit()
            view.setReadOnly(True)
            view.setFontFamily("monospace")
            self.tabs.addTab(view, name)
            self.tab_views[name] = view
        layout.addWidget(self.tabs)
        log_button = QPushButton("Export Analysis")
        log_button.clicked.connect(lambda: self.export_analysis())
        layout.addRow(log_button)
        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.set_current_index(0))
        layout.addRow(back_button)
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        layout.addWidget(quit_button)
        self.page_results.setLayout(layout)
        self.results_screen.setLayout(layout)
        
    def set_current_index(self,i):
        self.resize(*SCREEN_DIMENSIONS[i])
        self.Stack.setCurrentIndex(i)

    def choose_log(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Session to Analyze",
            str(PROJECT / "corpus"),
            "JSON Lines (*.jsonl)",
        )
        if path:
            self.file_selected.emit(path)
            self.set_current_index(1)

    def export_analysis(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Output File",
            "",
            "Log file (*.log)",
        )
        if path:
            if not path.endswith(".log"):
                path += ".log"
            log_text = "\n\n".join(
                "\n".join(lines) for name, lines in self.stored_text.items()
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(log_text)

    def set_text_sections(self, sections: dict[str, str]):
        self.stored_text.update(sections)
        for name, lines in sections.items():
            self.tab_views[name].setPlainText("\n".join(lines))
        self.Stack.setCurrentIndex(1)

def choose_session():
    app = QApplication.instance() or QApplication(sys.argv)
    window = stackedExample()
    window.show()
    app.exec()
    return window.selected_file