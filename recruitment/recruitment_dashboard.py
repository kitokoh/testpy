from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel

from .job_openings_widget import JobOpeningsWidget
from .candidates_widget import CandidatesWidget
from .interviews_widget import InterviewsWidget # Import InterviewsWidget

class RecruitmentDashboard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recruitment Dashboard")

        # Main layout
        self.main_layout = QVBoxLayout(self)

        # Tab widget
        self.tab_widget = QTabWidget()

        # Job Openings Tab
        self.job_openings_widget = JobOpeningsWidget()
        self.tab_widget.addTab(self.job_openings_widget, "Job Openings")

        # Candidates Tab
        self.candidates_widget = CandidatesWidget()
        self.tab_widget.addTab(self.candidates_widget, "Candidates")

        # Interviews Tab
        self.interviews_widget = InterviewsWidget() # Instantiate InterviewsWidget
        self.tab_widget.addTab(self.interviews_widget, "Interviews")

        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)

        self.setLayout(self.main_layout)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # To properly test JobOpeningsWidget import, it needs to exist.
    # We'll create a dummy JobOpeningsWidget here for the __main__ block to run without actual file.

    # Dummy class for JobOpeningsWidget if not yet created, for testing dashboard structure
    class JobOpeningsWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            label = QLabel("Actual JobOpeningsWidget (Simulated for Test)")
            layout.addWidget(label)
            self.setObjectName("JobOpeningsWidget")

    # Monkey patch the module if the real one is not yet available for testing purposes.
    # This is NOT standard practice for production code but useful for incremental dev.
    import recruitment # Assuming current dir is parent of recruitment
    if not hasattr(recruitment, 'job_openings_widget'): # If real one not there
        recruitment.job_openings_widget = sys.modules[__name__] # sys.modules[__name__] refers to current file
        # Now the from .job_openings_widget import JobOpeningsWidget inside RecruitmentDashboard
        # would need to be `from recruitment.job_openings_widget import JobOpeningsWidget`
        # For the placeholder mechanism in RecruitmentDashboard to work with this __main__,
        # the import `from .job_openings_widget import JobOpeningsWidget` would need to be changed
        # or this dummy class defined in a file named job_openings_widget.py in the same dir.

    # For the current setup in RecruitmentDashboard (commented out real import, using placeholder label):
    dashboard = RecruitmentDashboard()
    dashboard.resize(800, 600)
    dashboard.show()
    sys.exit(app.exec_())
```
