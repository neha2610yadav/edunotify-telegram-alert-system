import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QFrame
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from FTS_database import setup_database, check_login
from FTS_linking_dashboard import TelegramLinkingDashboard
from FTS_bot_listener import start_telegram_listener

class FacultyLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Faculty Login | EduNotify")
        self.setFixedSize(500, 600)
        self.setStyleSheet("background-color: #1e3c72;")
        self.create_ui()

    def create_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedSize(380, 430)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 18px;
            }
        """)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(35, 30, 35, 30)
        card_layout.setSpacing(15)

        logo = QLabel("EN")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(70, 70)
        logo.setStyleSheet("""
            QLabel {
                background-color: #1e3c72;
                color: white;
                border-radius: 35px;
                font-size: 26px;
                font-weight: bold;
            }
        """)
        card_layout.addWidget(logo, alignment=Qt.AlignCenter)

        title = QLabel("Faculty Login")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #1e3c72;")
        card_layout.addWidget(title)

        subtitle = QLabel("EduNotify Telegram Alert System")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray; font-size: 13px;")
        card_layout.addWidget(subtitle)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter faculty username")
        self.username_input.setFixedHeight(45)
        self.username_input.setStyleSheet(self.input_style())
        card_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(45)
        self.password_input.setStyleSheet(self.input_style())
        card_layout.addWidget(self.password_input)

        login_btn = QPushButton("Login")
        login_btn.setFixedHeight(45)
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e3c72;
                color: white;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16325f;
            }
        """)
        login_btn.clicked.connect(self.login_user)
        card_layout.addWidget(login_btn)

        footer = QLabel("Secure Faculty Access Only")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: gray; font-size: 12px;")
        card_layout.addWidget(footer)

        card.setLayout(card_layout)
        main_layout.addWidget(card)
        self.setLayout(main_layout)

    def input_style(self):
        return """
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 10px;
                padding-left: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1e3c72;
            }
        """

    def login_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        faculty = check_login(username, password)

        if faculty:
            faculty_id = faculty[0]
            faculty_username = faculty[1]

            self.dashboard = TelegramLinkingDashboard(faculty_id, faculty_username)
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")

if __name__ == "__main__":
    setup_database()
    start_telegram_listener()
    app = QApplication(sys.argv)
    window = FacultyLogin()
    window.show()
    sys.exit(app.exec_())
