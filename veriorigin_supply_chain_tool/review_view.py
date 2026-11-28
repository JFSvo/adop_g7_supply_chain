from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from decision_log import record_decision
from review_model import ACTION_LABELS, evidence_steps, rule_label

ACTION_COLORS = {"escalate": "#f5b4b4", "review": "#ffec99", "proceed": "#cceccc"}
OVERALL = {"escalate_for_review": ("ESCALATE FOR REVIEW", "#f5b4b4"),
           "review": ("REVIEW", "#ffec99"), "no_review_flags": ("PROCEED: no review flags", "#cceccc")}
STATUS_TEXT = {"listed": "Approved", "unlisted": "Not approved", "version_unlisted": "Version not approved",
               "unknown": "Unknown"}


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setParent(None)  # remove now, not at the next event loop pass
            widget.deleteLater()


def _badge(text, colour):
    label = QLabel(text)
    label.setStyleSheet(f"background:{colour}; padding:6px 10px; border-radius:4px; font-weight:bold;")
    return label


class DependencyCard(QFrame):
    evidence_clicked = Signal(int)
    decided = Signal()

    def __init__(self, card, events, context, parent=None):
        super().__init__(parent)
        self.card, self.context = card, context
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("DependencyCard { border:1px solid #bbb; border-radius:6px; background:#fafafa; }")
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel(f"<b style='font-size:15px'>{card['package']}</b> {card['version'] or ''}")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(_badge(f"Risk {card['score']}/100", ACTION_COLORS[card["suggested_action"]]))
        header.addWidget(_badge(f"Suggested: {ACTION_LABELS[card['suggested_action']]}",
                                ACTION_COLORS[card["suggested_action"]]))
        layout.addLayout(header)

        facts = QGridLayout()
        rows = [("On approved list", STATUS_TEXT.get(card["registry_status"], card["registry_status"])),
                ("Source approved", STATUS_TEXT.get(card["source_registry_status"], card["source_registry_status"])),
                ("Came from", ", ".join(card["sources"]) or "No source page found"),
                ("Why flagged", "; ".join(rule_label(rule) for rule in card["rules"]))]
        for row, (name, value) in enumerate(rows):
            facts.addWidget(QLabel(f"<b>{name}:</b>"), row, 0, Qt.AlignTop)
            text = QLabel(value)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse)
            facts.addWidget(text, row, 1)
        facts.setColumnStretch(1, 1)
        layout.addLayout(facts)

        chain = QHBoxLayout()
        chain.addWidget(QLabel("<b>Evidence:</b>"))
        for index, (seq, label) in enumerate(evidence_steps(card, events)):
            if index:
                chain.addWidget(QLabel("→"))
            step = QPushButton(f"#{seq} {label}")
            step.setToolTip("Show this step in the Evidence tab")
            step.setFlat(True)
            step.setStyleSheet("color:#1a5fb4; text-decoration:underline;")
            step.clicked.connect(lambda _=False, s=seq: self.evidence_clicked.emit(s))
            chain.addWidget(step)
        chain.addStretch()
        layout.addLayout(chain)

        b = card["breakdown"]
        why = QLabel(f"Score = severity {b['severity']} + approved list {b['registry']} + "
                     f"source {b['source']} + reached the build {b['reach']}")
        why.setStyleSheet("color:#555;")
        layout.addWidget(why)

        self.actions = QHBoxLayout()
        self.approve = QPushButton("Approve")
        self.escalate = QPushButton("Escalate")
        self.approve.clicked.connect(lambda: self._decide("approve"))
        self.escalate.clicked.connect(lambda: self._decide("escalate"))
        self.actions.addStretch()
        self.actions.addWidget(self.approve)
        self.actions.addWidget(self.escalate)
        layout.addLayout(self.actions)

    def _decide(self, decision):
        reviewer = self.context["reviewer"]()
        try:
            entry = record_decision(self.card, decision, reviewer, self.context["paths"], self.context["policy"])
        except ValueError as exc:
            QMessageBox.warning(self, "Decision not recorded", str(exc))
            return
        self.approve.hide()
        self.escalate.hide()
        self.actions.insertWidget(1, QLabel(f"<b>{decision.capitalize()}d</b> by {entry['reviewer_id']} "
                                            f"at {entry['timestamp'][:19].replace('T', ' ')} UTC. Logs fingerprinted."))
        self.decided.emit()


class ReviewView(QWidget):
    evidence_clicked = Signal(int)
    decided = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        top = QHBoxLayout()
        self.overall = QLabel("Analyze a session to see results.")
        top.addWidget(self.overall, stretch=1)
        top.addWidget(QLabel("Reviewer ID:"))
        self.reviewer = QLineEdit("seclead-01")
        self.reviewer.setMaximumWidth(140)
        self.reviewer.setToolTip("A role ID such as seclead-01, not your name")
        top.addWidget(self.reviewer)

        self.privacy = QLabel()
        self.privacy.setStyleSheet("color:#6a1b9a;")

        self.body = QVBoxLayout()
        self.body.setAlignment(Qt.AlignTop)
        container = QWidget()
        container.setLayout(self.body)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.addLayout(top)
        outer.addWidget(self.privacy)
        outer.addWidget(scroll)

    def show_review(self, report, cards, risks, events, paths):
        _clear(self.body)
        text, colour = OVERALL.get(report["recommendation"], (report["recommendation"], "#e0e0e0"))
        self.overall.setText(f"Session {report['session_id']}: <b>{text}</b>")
        self.overall.setStyleSheet(f"background:{colour}; padding:8px; border-radius:4px;")
        privacy = report.get("privacy", {})
        withheld = len(privacy.get("withheld_fields", []))
        self.privacy.setText(f"Privacy filter {privacy.get('policy_version', 'not applied')} applied: "
                             f"{withheld} field{'' if withheld == 1 else 's'} withheld, home folders masked.")

        context = {"reviewer": lambda: self.reviewer.text().strip(), "paths": paths,
                   "policy": privacy.get("policy_version", "none")}
        self.body.addWidget(QLabel("<h3>Dependencies added or changed by the agent</h3>"))
        if not cards:
            self.body.addWidget(QLabel("No dependency changes in this session."))
        for card in cards:
            widget = DependencyCard(card, events, context)
            widget.evidence_clicked.connect(self.evidence_clicked)
            widget.decided.connect(self.decided)
            self.body.addWidget(widget)

        self.body.addWidget(QLabel("<h3>Other risks in this session</h3>"))
        if not risks:
            self.body.addWidget(QLabel("None."))
        for risk in risks:
            row = QHBoxLayout()
            row.addWidget(_badge(risk["severity"].upper(), "#f5b4b4" if risk["severity"] == "high" else "#ffec99"))
            row.addWidget(QLabel(f"{risk['label']}" + (f" (x{risk['count']})" if risk["count"] > 1 else "")), stretch=1)
            for seq in risk["evidence_seq"][:6]:
                step = QPushButton(f"#{seq}")
                step.setFlat(True)
                step.setStyleSheet("color:#1a5fb4; text-decoration:underline;")
                step.clicked.connect(lambda _=False, s=seq: self.evidence_clicked.emit(s))
                row.addWidget(step)
            holder = QWidget()
            holder.setLayout(row)
            self.body.addWidget(holder)
