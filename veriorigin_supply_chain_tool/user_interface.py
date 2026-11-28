import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal
from pathlib import Path

from trace_view import TraceView
from review_view import ReviewView
from decisions_view import DecisionsView
from resources import bundled_path, project_root

PROJECT = project_root()
LOGO_PATH = bundled_path("veriorigin_supply_chain_tool", "VeriOrigin_logo.png")

INITIAL_DIMENSION = (300, 50, 10, 10)
SCREEN_DIMENSIONS = [(10, 10), (1000, 700)]

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
        layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tab_views = {}

        self.review_view = ReviewView()
        self.tabs.addTab(self.review_view, "Review")          # first tab: what the lead decides on

        self.trace_view = TraceView()
        self.tabs.addTab(self.trace_view, "Evidence")         # the raw steps behind each finding

        self.decisions_view = DecisionsView()
        self.tabs.addTab(self.decisions_view, "Decisions")    # audit trail of Approve/Escalate

        self.review_view.evidence_clicked.connect(self.show_evidence)
        self.tabs.currentChanged.connect(
            lambda i: self.decisions_view.refresh(self.session_paths) if self.tabs.widget(i) is self.decisions_view else None)
        self.session_paths = []
        self.export_text = lambda: "Analyze a session first."

        layout.addWidget(self.tabs)

        log_button = QPushButton("Export Analysis")
        log_button.clicked.connect(self.export_analysis)
        layout.addWidget(log_button)

        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.set_current_index(0))
        layout.addWidget(back_button)

        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.close)
        layout.addWidget(quit_button)

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
            "Text file (*.txt)",
        )
        if path:
            if not path.endswith(".txt"):
                path += ".txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.export_text())

# Fill all three tabs for one analyzed session
    def show_results(self, report, cards, risks, events, paths, export_text):

        self.session_paths = paths
        self.export_text = export_text
        self.review_view.show_review(report, cards, risks, events, paths)
        self.trace_view.show_trace(events)
        self.decisions_view.refresh(paths)
        self.tabs.setCurrentIndex(0)
        self.Stack.setCurrentIndex(1)

    def show_evidence(self, seq):
        self.tabs.setCurrentWidget(self.trace_view)
        self.trace_view.select_seq(seq)

def choose_session():
    app = QApplication.instance() or QApplication(sys.argv)
    window = stackedExample()
    window.show()
    app.exec()
    return window.selected_file