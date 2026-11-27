from collections import Counter

from PySide6.QtCharts import (QBarCategoryAxis, QBarSet, QChart, QChartView,
                              QStackedBarSeries, QValueAxis)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

# Same meaning as the trace table: red = serious, yellow = caution, green = fine.
SEVERITIES = ("high", "medium", "info")
SEVERITY_COLORS = {
    "high": QColor(245, 180, 180),
    "medium": QColor(255, 236, 153),
    "info": QColor(204, 236, 204),
}

# recommendation -> (label text, background colour)
RECOMMENDATION_STYLE = {
    "escalate_for_review": ("Escalate for review", "#f5b4b4"),
    "review": ("Review", "#ffec99"),
    "no_review_flags": ("No review flags", "#cceccc"),
}


def _clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())


class DashboardView(QWidget):
    """Headline per session, severity chart, then the most frequent rules."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.headline_label = QLabel("Analyse a session to see results.")
        self.headline_label.setStyleSheet("font-weight: bold;")
        self.headlines_layout = QVBoxLayout()

        self.chart_title = QLabel("Findings by session and severity")
        self.chart_title.setStyleSheet("font-weight: bold;")
        self.chart_slot = QVBoxLayout()   # the chart widget is swapped in here

        self.rules_title = QLabel("Most frequent rules")
        self.rules_title.setStyleSheet("font-weight: bold;")
        self.rules_table = QTableWidget(0, 3)
        self.rules_table.setHorizontalHeaderLabels(["Rule", "Severity", "Count"])
        self.rules_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        outer = QVBoxLayout(self)
        outer.addLayout(self.headlines_layout)
        outer.addWidget(self.chart_title)
        outer.addLayout(self.chart_slot, stretch=1)
        outer.addWidget(self.rules_title)
        outer.addWidget(self.rules_table, stretch=1)

    def show_reports(self, reports):
        _clear_layout(self.headlines_layout)
        _clear_layout(self.chart_slot)

        if not reports:
            self.headlines_layout.addWidget(QLabel("No sessions were analysed."))
            self.rules_table.setRowCount(0)
            return

        for report in reports:
            self.headlines_layout.addWidget(self._headline(report))

        self.chart_slot.addWidget(QChartView(self._severity_chart(reports)))
        self._fill_rules_table(reports)

    def _headline(self, report):
        text, colour = RECOMMENDATION_STYLE.get(
            report["recommendation"], (report["recommendation"], "#e0e0e0"))
        label = QLabel(f"Session {report['session_id']}: {text} "
                       f"({report['event_count']} events)")
        label.setStyleSheet(f"background: {colour}; padding: 8px; "
                            f"border-radius: 4px; font-weight: bold;")
        return label

    def _severity_chart(self, reports):
        categories = []
        counts = {severity: [] for severity in SEVERITIES}
        for report in reports:
            categories.append(str(report["session_id"]))
            tally = Counter(finding["severity"] for finding in report["findings"])
            for severity in SEVERITIES:
                counts[severity].append(tally.get(severity, 0))

        series = QStackedBarSeries()
        for severity in SEVERITIES:
            bar_set = QBarSet(severity.capitalize())
            bar_set.append(counts[severity])
            bar_set.setColor(SEVERITY_COLORS[severity])
            series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setMin(0)
        axis_y.setMax(max(1, max(sum(c) for c in zip(*counts.values()))))
        axis_y.setTickCount(2)  # adjust if the counts get large
        axis_y.applyNiceNumbers()
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.setAnimationOptions(QChart.NoAnimation)
        return chart

    def _fill_rules_table(self, reports):
        totals = Counter()
        for report in reports:
            for finding in report["findings"]:
                totals[(finding["rule_id"], finding["severity"])] += 1

        # Most frequent first, then by severity order.
        rows = sorted(totals.items(),
                      key=lambda item: (-item[1], SEVERITIES.index(item[0][1])
                                        if item[0][1] in SEVERITIES else len(SEVERITIES)))
        self.rules_table.setRowCount(len(rows))
        for row, ((rule_id, severity), count) in enumerate(rows):
            rule_item = QTableWidgetItem(rule_id)
            severity_item = QTableWidgetItem(severity.upper())
            if severity in SEVERITY_COLORS:
                severity_item.setBackground(SEVERITY_COLORS[severity])
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.rules_table.setItem(row, 0, rule_item)
            self.rules_table.setItem(row, 1, severity_item)
            self.rules_table.setItem(row, 2, count_item)