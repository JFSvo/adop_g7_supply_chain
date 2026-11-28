import sys
from pathlib import Path
 
from provenance_analysis import analyze_events, load_events, load_registry, with_companions, load_baseline_manifest
from privacy_filter import filter_event, filter_report
from review_model import dependency_cards, export_text, other_risks
from decision_log import read_decisions
 
from PySide6.QtWidgets import QApplication
from user_interface import VeriOrigin_UI
 
# VeriOrigin's primary application file that calls all necessary modules to to perform data pre-processing, analysis, and GUI output
 
PROJECT = Path(__file__).resolve().parent.parent
file_path = None
def on_file_selected(window, path):
    try:
        paths = with_companions([path])
        events = load_events(paths)
        reports = analyze_events(events, load_registry(), load_baseline_manifest())
        # P-01/P-02: only allowlisted, identity-masked fields reach the interface and the export.
        reports = [filter_report(report) for report in reports]
        events = [filter_event(event) for event in events]
    except (OSError, ValueError) as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(window, "Session could not be analyzed", str(exc))
        return
        return
    if not reports:
        return
    report = reports[0]  # one session per selected file (its companion file is the same session)
    cards = dependency_cards(report)
    risks = other_risks(report)
    window.show_results(report, cards, risks, events, paths,
                        lambda: export_text(report, cards, risks, read_decisions(), events))

def main():
    app = QApplication(sys.argv)
    window = VeriOrigin_UI()
    window.file_selected.connect(lambda path: on_file_selected(window, path))
    window.show()
    sys.exit(app.exec())
 
 
if __name__ == "__main__":
    main()