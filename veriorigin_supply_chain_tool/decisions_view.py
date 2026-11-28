from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from decision_log import DEFAULT_LOG, logs_unchanged, read_decisions

COLUMNS = ["Time (UTC)", "Reviewer", "Session", "Dependency", "Decision", "Score", "Logs unchanged"]


class DecisionsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.note = QLabel("Every decision records who, when, and a fingerprint (SHA-256) of the logs "
                           "it was based on. A ✗ means a log changed after the decision.")
        self.note.setWordWrap(True)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.note)
        layout.addWidget(self.table)

# paths: the log files of the open session, used to re-check that session's decisions
    def refresh(self, paths):

        by_label = {f"{Path(p).parent.name}/{Path(p).name}": p for p in paths}
        decisions = list(reversed(read_decisions(DEFAULT_LOG)))
        self.table.setRowCount(len(decisions))
        for row, entry in enumerate(decisions):
            files = [by_label.get(label) for label in entry["log_sha256"]]
            if all(files):
                ok = logs_unchanged(entry, files)
                check, colour = ("✓", QColor(204, 236, 204)) if ok else ("✗", QColor(245, 180, 180))
            else:
                check, colour = ("open session to check", None)
            values = [entry["timestamp"].replace("T", " ")[:19], entry["reviewer_id"], entry["session_id"],
                      f"{entry['package']} {entry['version'] or ''}", entry["decision"].upper(),
                      str(entry["score"]), check]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == len(values) - 1:
                    item.setTextAlignment(Qt.AlignCenter)
                    if colour:
                        item.setBackground(colour)
                self.table.setItem(row, column, item)