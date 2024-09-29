import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QTimer
import paho.mqtt.client as mqtt

broker = 'broker.hivemq.com'
port = 1883
topic = "iot/sensors/pressure"

class PressureEmulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.connect(broker, port)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Pressure Sensor Emulator')
        layout = QVBoxLayout()

        self.pressure_label = QLabel('Pressure Data: Waiting...')
        self.start_button = QPushButton('Start Publishing Data')
        self.start_button.clicked.connect(self.start_publishing)

        layout.addWidget(self.pressure_label)
        layout.addWidget(self.start_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_publishing(self):
        self.start_button.setDisabled(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_data)
        self.timer.start(15000)  # Publish every 15 seconds

    def publish_data(self):
        seat_pressure = random.randint(40, 100)
        back_pressure = random.randint(40, 100)
        message = f"Seat Pressure: {seat_pressure}, Back Pressure: {back_pressure}"
        self.client.publish(topic, message)
        self.pressure_label.setText(f'Seat: {seat_pressure}, Back: {back_pressure}')
        print(f'Published: {message}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PressureEmulator()
    ex.show()
    sys.exit(app.exec_())
