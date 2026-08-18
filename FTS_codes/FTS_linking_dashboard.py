"""First post-login screen: email Telegram deep links to unlinked students."""

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)

from FTS_database import (
    get_batches, get_students_by_batch, mark_telegram_link_email_sent,
)
from FTS_email_sender import send_telegram_link_email
from FTS_telegram_api import build_telegram_deep_link


class EmailLinkSenderThread(QThread):
    finished = pyqtSignal(int, str)

    def __init__(self, student_id, student_name, student_email, link_code):
        super().__init__()
        self.student_id = student_id
        self.student_name = student_name
        self.student_email = student_email
        self.link_code = link_code

    def run(self):
        telegram_link = build_telegram_deep_link(self.link_code)
        status = send_telegram_link_email(self.student_name, self.student_email, telegram_link)
        if status == "Sent":
            mark_telegram_link_email_sent(self.student_id)
        self.finished.emit(self.student_id, status)


class TelegramLinkingDashboard(QWidget):
    """Batch-wise student status and email-based Telegram account onboarding."""

    def __init__(self, faculty_id, faculty_username):
        super().__init__()
        self.faculty_id = faculty_id
        self.faculty_username = faculty_username
        self.email_thread = None
        self.pending_button = None
        self.setWindowTitle("Telegram Student Linking | EduNotify")
        self.setFixedSize(1050, 700)
        self.create_ui()
        self.load_batches()

    def create_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        top_layout = QHBoxLayout()
        title = QLabel("Telegram Student Linking")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #1e3c72;")

        message_btn = QPushButton("Send Message")
        message_btn.setFixedSize(130, 40)
        message_btn.setStyleSheet(self.nav_button_style())
        message_btn.clicked.connect(self.open_message_screen)
        history_btn = QPushButton("History")
        history_btn.setFixedSize(100, 40)
        history_btn.setStyleSheet(self.nav_button_style())
        history_btn.clicked.connect(self.open_history)
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedSize(100, 40)
        logout_btn.setStyleSheet(self.nav_button_style())
        logout_btn.clicked.connect(self.logout)

        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(message_btn)
        top_layout.addWidget(history_btn)
        top_layout.addWidget(logout_btn)
        main_layout.addLayout(top_layout)

        info = QLabel("Send each unlinked student a personal email containing their secure Telegram connection link.")
        info.setStyleSheet("color: gray; font-size: 13px;")
        main_layout.addWidget(info)

        batch_layout = QHBoxLayout()
        batch_label = QLabel("Select Batch:")
        batch_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.batch_combo = QComboBox()
        self.batch_combo.setFixedHeight(38)
        self.batch_combo.currentIndexChanged.connect(self.load_students)
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.setFixedSize(140, 38)
        refresh_btn.setStyleSheet(self.nav_button_style())
        refresh_btn.clicked.connect(self.refresh_students)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.batch_combo)
        batch_layout.addWidget(refresh_btn)
        batch_layout.addStretch()
        main_layout.addLayout(batch_layout)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(5)
        self.student_table.setHorizontalHeaderLabels([
            "Student Name", "Mobile Number", "Email", "Telegram Status", "Action"
        ])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.student_table.setStyleSheet("""
            QTableWidget { border: 1px solid #ccc; font-size: 14px; }
            QHeaderView::section { background-color: #1e3c72; color: white; font-weight: bold; height: 35px; }
        """)
        main_layout.addWidget(self.student_table)
        self.setLayout(main_layout)

    @staticmethod
    def nav_button_style():
        return "QPushButton { background-color: #1e3c72; color: white; border-radius: 8px; font-weight: bold; }"

    def load_batches(self):
        self.batch_combo.clear()
        self.batch_combo.addItem("-- Select Batch --", None)
        for batch_id, batch_name in get_batches():
            self.batch_combo.addItem(batch_name, batch_id)

    def refresh_students(self):
        self.load_students()

    def load_students(self):
        batch_id = self.batch_combo.currentData()
        self.student_table.setRowCount(0)
        if batch_id is None:
            return

        students = get_students_by_batch(batch_id)
        self.student_table.setRowCount(len(students))
        for row, student in enumerate(students):
            student_id, name, phone_number, email, chat_id, linked, link_code, email_sent_at = student
            self.student_table.setItem(row, 0, QTableWidgetItem(str(name)))
            self.student_table.setItem(row, 1, QTableWidgetItem(str(phone_number or "N/A")))
            self.student_table.setItem(row, 2, QTableWidgetItem(str(email or "N/A")))

            if linked and chat_id:
                self.student_table.setItem(row, 3, QTableWidgetItem("✅ Linked"))
                linked_label = QLabel("✓ Linked")
                linked_label.setAlignment(Qt.AlignCenter)
                linked_label.setStyleSheet("color: #198754; font-weight: bold;")
                self.student_table.setCellWidget(row, 4, linked_label)
                continue

            status = "Email Sent — Not Linked" if email_sent_at else "❌ Not Linked"
            self.student_table.setItem(row, 3, QTableWidgetItem(status))
            button_text = "Resend Telegram Link" if email_sent_at else "Send Telegram Link"
            link_button = QPushButton(button_text)
            link_button.setStyleSheet("""
                QPushButton { background-color: #1e3c72; color: white; border-radius: 6px; font-weight: bold; }
            """)
            link_button.clicked.connect(
                lambda checked=False, sid=student_id, student_name=name, student_email=email,
                code=link_code, button=link_button: self.send_link_email(
                    sid, student_name, student_email, code, button
                )
            )
            self.student_table.setCellWidget(row, 4, link_button)

    def send_link_email(self, student_id, student_name, student_email, link_code, button):
        button.setEnabled(False)
        button.setText("Sending...")
        self.pending_button = button
        self.email_thread = EmailLinkSenderThread(student_id, student_name, student_email, link_code)
        self.email_thread.finished.connect(self.on_email_finished)
        self.email_thread.start()

    def on_email_finished(self, _student_id, status):
        if self.pending_button is not None:
            self.pending_button.setEnabled(True)
        if status == "Sent":
            QMessageBox.information(self, "Telegram Link Email", "Telegram linking email sent successfully.")
            self.refresh_students()
        else:
            QMessageBox.warning(self, "Telegram Link Email", status)
            if self.pending_button is not None:
                self.pending_button.setText("Send Telegram Link")
        self.pending_button = None
        self.email_thread = None

    def open_message_screen(self):
        from FTS_dashboard import FacultyDashboard
        self.message_dashboard = FacultyDashboard(self.faculty_id, self.faculty_username, self)
        self.message_dashboard.show()
        self.hide()

    def open_history(self):
        from FTS_dashboard import HistoryWindow
        HistoryWindow().exec_()

    def logout(self):
        from FTS_login import FacultyLogin
        self.login_window = FacultyLogin()
        self.login_window.show()
        self.close()
