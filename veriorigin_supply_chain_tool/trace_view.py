from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QHBoxLayout, QMenu, QScrollArea, QTableView,
    QToolButton, QVBoxLayout, QWidget, QWidgetAction,
)

# (header label, event key)
COLUMNS = [
    ("Seq", "seq"),
    ("Task", "task_id"),
    ("Server", "server"),
    ("Tool", "tool_name"),
    ("Resource", "target_resource"),
    ("Status", "result_status")
]

STATUS_COLORS = {
    "success": QColor(204, 236, 204),  # green
    "error": QColor(255, 236, 153),    # yellow
    "blocked": QColor(245, 180, 180),  # red
}

# Holds the events for one session and exposes them as table rows
class TraceModel(QAbstractTableModel):

    def __init__(self, events, parent=None):
        super().__init__(parent)
        self._events = list(events)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._events)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][0]
        return None

    def data(self, index, role=Qt.DisplayRole):
        event = self._events[index.row()]
        key = COLUMNS[index.column()][1]
        if role == Qt.DisplayRole:
            value = event.get(key)
            return "" if value is None else str(value)
        if role == Qt.BackgroundRole and key == "result_status":
            return STATUS_COLORS.get(event["result_status"])
        return None

    def event_at(self, row):
        return self._events[row]

# Keeps a row only if its server, status, and task are all in the selected sets 
class TraceFilterProxy(QSortFilterProxyModel):


    def __init__(self, parent=None):
        super().__init__(parent)
        # None means "no restriction on this field".
        self._allowed = {"server": None, "result_status": None, "task_id": None}

    def set_allowed(self, field, values):
        self._allowed[field] = set(values)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        event = self.sourceModel().event_at(source_row)
        return all(
            allowed is None or event[field] in allowed
            for field, allowed in self._allowed.items()
        )


# A button that opens a menu of checkboxes. Emits the set of checked values
class MultiSelectFilter(QToolButton):


    changed = Signal(set)

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.title = title
        self._boxes = {}
        self.setPopupMode(QToolButton.InstantPopup)
        self.menu = QMenu(self)
        self.setMenu(self.menu)
        self.setText(title)

    def set_values(self, values):
        self.menu.clear()
        self._boxes.clear()
        for value in sorted(values):
            box = QCheckBox(value)
            box.setChecked(True)
            box.toggled.connect(self._emit)
            action = QWidgetAction(self.menu)
            action.setDefaultWidget(box)   # keeps the menu open while clicking boxes
            self.menu.addAction(action)
            self._boxes[value] = box
        self._emit()

    def selected(self):
        return {value for value, box in self._boxes.items() if box.isChecked()}

    def _emit(self, *_):
        selected = self.selected()
        self.setText(f"{self.title} ({len(selected)}/{len(self._boxes)})")
        self.changed.emit(selected)


# A header button that shows or hides its content widget
class CollapsibleSection(QWidget):


    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.toggle = QToolButton()
        self.toggle.setText(title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setArrowType(Qt.DownArrow)
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.toggle.toggled.connect(self._on_toggled)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle)
        layout.addWidget(content)
        self.content = content

    def _on_toggled(self, expanded):
        self.toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content.setVisible(expanded)


# Filter bar on top, one collapsible table per session below
class TraceView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proxies = []

        self.server_filter = MultiSelectFilter("Server")
        self.status_filter = MultiSelectFilter("Status")
        self.task_filter = MultiSelectFilter("Task")
        self.server_filter.changed.connect(lambda v: self._apply("server", v))
        self.status_filter.changed.connect(lambda v: self._apply("result_status", v))
        self.task_filter.changed.connect(lambda v: self._apply("task_id", v))

        bar = QHBoxLayout()
        for widget in (self.server_filter, self.status_filter, self.task_filter):
            bar.addWidget(widget)
        bar.addStretch()

        self.sections_layout = QVBoxLayout()
        self.sections_layout.setAlignment(Qt.AlignTop)
        container = QWidget()
        container.setLayout(self.sections_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.addLayout(bar)
        outer.addWidget(scroll)

    def show_trace(self, events):
        # Remove sections from any previous analysis.
        while self.sections_layout.count():
            item = self.sections_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._proxies = []
        self._tables = []

        by_session = {}
        for event in events:
            by_session.setdefault(event["session_id"], []).append(event)

        for session_id, session_events in sorted(by_session.items()):
            proxy = TraceFilterProxy()
            proxy.setSourceModel(TraceModel(session_events))
            self._proxies.append(proxy)

            table = QTableView()
            table.setModel(proxy)
            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setStretchLastSection(True)
            table.setMinimumHeight(200)
            table.setWordWrap(True)
            self._tables.append(table)

            title = f"Session {session_id} ({len(session_events)} events)"
            self.sections_layout.addWidget(CollapsibleSection(title, table))

        # Repopulating the filters emits "changed", which applies the selections to the new proxies.
        self.server_filter.set_values({e["server"] for e in events})
        self.status_filter.set_values({e["result_status"] for e in events})
        self.task_filter.set_values({e["task_id"] for e in events})

    def _apply(self, field, values):
        for proxy in self._proxies:
            proxy.set_allowed(field, values)

# Select and scroll to the event with this sequence number (used by the Review tab)
    def select_seq(self, seq):

        for proxy, table in zip(self._proxies, self._tables):
            model = proxy.sourceModel()
            for row in range(model.rowCount()):
                if model.event_at(row).get("seq") == seq:
                    index = proxy.mapFromSource(model.index(row, 0))
                    if index.isValid():
                        table.selectRow(index.row())
                        table.scrollTo(index)
                        table.setFocus()
                        return True
        return False