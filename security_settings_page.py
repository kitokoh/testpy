import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from security_module.biometric_auth import BiometricAuthenticator

class SecuritySettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.authenticator = BiometricAuthenticator()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Security Settings - Biometric Authentication Test')
        self.setGeometry(300, 300, 400, 250)

        layout = QVBoxLayout()

        self.status_label = QLabel('Click a button to test an authentication method.')
        layout.addWidget(self.status_label)

        btn_voice_auth = QPushButton('Test Voice Authentication')
        btn_voice_auth.clicked.connect(self.test_voice_auth)
        layout.addWidget(btn_voice_auth)

        btn_face_auth = QPushButton('Test Face Authentication')
        btn_face_auth.clicked.connect(self.test_face_auth)
        layout.addWidget(btn_face_auth)

        btn_fingerprint_auth = QPushButton('Test Fingerprint Authentication')
        btn_fingerprint_auth.clicked.connect(self.test_fingerprint_auth)
        layout.addWidget(btn_fingerprint_auth)

        self.setLayout(layout)

    def test_voice_auth(self):
        self.status_label.setText('Testing Voice Authentication...')
        QApplication.processEvents() # Update UI
        result = self.authenticator.authenticate_voice()
        if result:
            QMessageBox.information(self, 'Voice Auth Result', 'Voice Authentication Successful!')
            self.status_label.setText('Voice Authentication Successful.')
        else:
            QMessageBox.warning(self, 'Voice Auth Result', 'Voice Authentication Failed.')
            self.status_label.setText('Voice Authentication Failed.')

    def test_face_auth(self):
        self.status_label.setText('Testing Face Authentication...')
        QApplication.processEvents() # Update UI
        result = self.authenticator.authenticate_face()
        if result:
            QMessageBox.information(self, 'Face Auth Result', 'Face Authentication Successful!')
            self.status_label.setText('Face Authentication Successful.')
        else:
            QMessageBox.warning(self, 'Face Auth Result', 'Face Authentication Failed.')
            self.status_label.setText('Face Authentication Failed.')

    def test_fingerprint_auth(self):
        self.status_label.setText('Testing Fingerprint Authentication...')
        QApplication.processEvents() # Update UI
        result = self.authenticator.authenticate_fingerprint()
        if result:
            QMessageBox.information(self, 'Fingerprint Auth Result', 'Fingerprint Authentication Successful!')
            self.status_label.setText('Fingerprint Authentication Successful.')
        else:
            QMessageBox.warning(self, 'Fingerprint Auth Result', 'Fingerprint Authentication Failed.')
            self.status_label.setText('Fingerprint Authentication Failed.')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SecuritySettingsPage()
    ex.show()
    sys.exit(app.exec_())
