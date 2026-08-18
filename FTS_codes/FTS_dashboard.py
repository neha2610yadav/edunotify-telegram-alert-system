"""Linked-student Telegram message screen and message-history dialog."""

import sys
import time

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget, QHeaderView,
)

from FTS_database import (
    get_batches, get_linked_students_by_batch, get_message_history,
    save_message_history,
)
from FTS_telegram_sender import send_to_student


class TelegramSenderThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int, list)

    def __init__(self, faculty_id, faculty_username, batch_name, selected_students, message):
        super().__init__()
        self.faculty_id = faculty_id
        self.faculty_username = faculty_username
        self.batch_name = batch_name
        self.selected_students = selected_students
        self.message = message

    def run(self):
        final_message = f"📢 [{self.batch_name}]\nFrom: {self.faculty_username}\n\n{self.message}"
        success_count = 0
        failed_count = 0
        failed_details = []
        total = len(self.selected_students)

        for index, student in enumerate(self.selected_students):
            status = send_to_student(student["chat_id"], final_message)
            save_message_history(self.faculty_id, student["id"], final_message, status)
            if status.startswith("Sent"):
                success_count += 1
            else:
                failed_count += 1
                failed_details.append(f"{student['name']} - {status}")
            self.progress.emit(success_count, failed_count, f"Sending {index + 1}/{total}...")
            time.sleep(0.05)

        self.finished.emit(success_count, failed_count, failed_details)


class HistoryWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Message History | EduNotify")
        self.setFixedSize(1050, 500)
        self.create_ui()
        self.load_history()

    def create_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Telegram Message History")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1e3c72;")
        layout.addWidget(title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Faculty", "Batch", "Student", "Channel", "Message", "Date & Time", "Status"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        self.setLayout(layout)

    def load_history(self):
        history = get_message_history()
        self.history_table.setRowCount(len(history))
        for row, record in enumerate(history):
            for column, value in enumerate(record):
                self.history_table.setItem(row, column, QTableWidgetItem(str(value or "N/A")))


class FacultyDashboard(QWidget):
    """Message screen: only fully Telegram-linked students are selectable."""

    def __init__(self, faculty_id, faculty_username, linking_dashboard=None):
        super().__init__()
        self.faculty_id = faculty_id
        self.faculty_username = faculty_username
        self.linking_dashboard = linking_dashboard
        self.sender_thread = None
        self.setWindowTitle("Send Telegram Message | EduNotify")
        self.setFixedSize(1000, 750)
        self.create_ui()
        self.load_batches()

    def create_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(15)

        top_layout = QHBoxLayout()
        title = QLabel("Send Telegram Notification")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet("color: #1e3c72;")

        linking_btn = QPushButton("Telegram Linking")
        linking_btn.setFixedSize(140, 40)
        linking_btn.setStyleSheet(self.nav_button_style())
        linking_btn.clicked.connect(self.open_linking)
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
        top_layout.addWidget(linking_btn)
        top_layout.addWidget(history_btn)
        top_layout.addWidget(logout_btn)
        main_layout.addLayout(top_layout)

        batch_layout = QHBoxLayout()
        batch_label = QLabel("Select Batch:")
        batch_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.batch_combo = QComboBox()
        self.batch_combo.setFixedHeight(38)
        self.batch_combo.currentIndexChanged.connect(self.load_students)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.batch_combo)
        batch_layout.addStretch()
        main_layout.addLayout(batch_layout)

        self.no_students_label = QLabel("")
        self.no_students_label.setStyleSheet("color: gray; font-size: 13px;")
        main_layout.addWidget(self.no_students_label)

        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["Select", "Student Name", "Phone Number", "Email"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.student_table.setStyleSheet("""
            QTableWidget { border: 1px solid #ccc; font-size: 14px; }
            QHeaderView::section { background-color: #1e3c72; color: white; font-weight: bold; height: 35px; }
        """)
        main_layout.addWidget(self.student_table)

        msg_label = QLabel("Write Urgent Message:")
        msg_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        main_layout.addWidget(msg_label)
        self.message_box = QTextEdit()
        self.message_box.setFixedHeight(130)
        self.message_box.setPlaceholderText("Type your urgent notification here...")
        main_layout.addWidget(self.message_box)

        self.send_btn = QPushButton("📤 Send to Selected Students via Telegram")
        self.send_btn.setFixedHeight(45)
        self.send_btn.setStyleSheet(self.send_button_style("#198754"))
        self.send_btn.clicked.connect(self.send_message)
        main_layout.addWidget(self.send_btn)
        self.setLayout(main_layout)

    @staticmethod
    def nav_button_style():
        return "QPushButton { background-color: #1e3c72; color: white; border-radius: 8px; font-weight: bold; }"

    @staticmethod
    def send_button_style(color):
        return f"QPushButton {{ background-color: {color}; color: white; border-radius: 8px; font-size: 15px; font-weight: bold; }}"

    def load_batches(self):
        self.batch_combo.clear()
        self.batch_combo.addItem("-- Select Batch --", None)
        for batch_id, batch_name in get_batches():
            self.batch_combo.addItem(batch_name, batch_id)

    def load_students(self):
        batch_id = self.batch_combo.currentData()
        self.student_table.setRowCount(0)
        self.no_students_label.setText("")
        if batch_id is None:
            return

        students = get_linked_students_by_batch(batch_id)
        if not students:
            self.no_students_label.setText(
                "No Telegram-linked students found in this batch. Please link students from the Telegram Linking Dashboard first."
            )
            return

        self.student_table.setRowCount(len(students))
        for row, student in enumerate(students):
            student_id, name, phone_number, email, chat_id, _linked, _code, _email_sent = student
            checkbox = QCheckBox()
            checkbox.student_id = student_id
            checkbox.chat_id = chat_id
            checkbox.setStyleSheet("margin-left: 50px;")
            self.student_table.setCellWidget(row, 0, checkbox)
            self.student_table.setItem(row, 1, QTableWidgetItem(str(name)))
            self.student_table.setItem(row, 2, QTableWidgetItem(str(phone_number or "N/A")))
            self.student_table.setItem(row, 3, QTableWidgetItem(str(email or "N/A")))

    def send_message(self):
        batch_name = self.batch_combo.currentText()
        message = self.message_box.toPlainText().strip()
        if self.batch_combo.currentData() is None:
            QMessageBox.warning(self, "Warning", "Please select a batch.")
            return
        if not message:
            QMessageBox.warning(self, "Warning", "Please write a message.")
            return

        selected_students = []
        for row in range(self.student_table.rowCount()):
            checkbox = self.student_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_students.append({
                    "id": checkbox.student_id,
                    "name": self.student_table.item(row, 1).text(),
                    "chat_id": checkbox.chat_id,
                })
        if not selected_students:
            QMessageBox.warning(self, "Warning", "Please select at least one linked student.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Send", f"Send Telegram alert to {len(selected_students)} linked student(s)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self.send_btn.setEnabled(False)
        self.send_btn.setText("📤 Initializing...")
        self.send_btn.setStyleSheet(self.send_button_style("#6c757d"))
        self.sender_thread = TelegramSenderThread(
            self.faculty_id, self.faculty_username, batch_name, selected_students, message
        )
        self.sender_thread.progress.connect(self.on_sending_progress)
        self.sender_thread.finished.connect(self.on_sending_finished)
        self.sender_thread.start()

    def on_sending_progress(self, sent, failed, status_text):
        self.send_btn.setText(f"📤 {status_text} (✅{sent} ❌{failed})")

    def on_sending_finished(self, sent, failed, details):
        self.send_btn.setEnabled(True)
        self.send_btn.setText("📤 Send to Selected Students via Telegram")
        self.send_btn.setStyleSheet(self.send_button_style("#198754"))
        result = f"✅ Sent: {sent}\n❌ Failed: {failed}"
        if details:
            result += "\n\nDetails:\n" + "\n".join(details[:5])
        QMessageBox.information(self, "Send Complete", result)
        if sent > 0:
            self.message_box.clear()
        self.sender_thread = None

    def open_linking(self):
        if self.linking_dashboard is not None:
            self.linking_dashboard.refresh_students()
            self.linking_dashboard.show()
            self.close()

    def open_history(self):
        HistoryWindow().exec_()

    def logout(self):
        from FTS_login import FacultyLogin
        self.login_window = FacultyLogin()
        self.login_window.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FacultyDashboard(1, "faculty")
    window.show()
    sys.exit(app.exec_())
