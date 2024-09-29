import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QTimer
import paho.mqtt.client as mqtt

broker = 'broker.hivemq.com'
port = 1883
topic = "iot/sensors/accelerometer"

class AccelerometerEmulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.connect(broker, port)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Accelerometer Emulator')
        layout = QVBoxLayout()

        self.accel_label = QLabel('Tilt Data: Waiting...')
        self.start_button = QPushButton('Start Publishing Data')
        self.start_button.clicked.connect(self.start_publishing)

        layout.addWidget(self.accel_label)
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
        tilt_x = round(random.uniform(-10.0, 10.0), 2)  
        tilt_y = round(random.uniform(-10.0, 10.0), 2)  
        tilt_z = round(random.uniform(-10.0, 10.0), 2)
        message = f"Tilt X: {tilt_x}, Tilt Y: {tilt_y}, Tilt Z: {tilt_z}"
        self.client.publish(topic, message)
        self.accel_label.setText(f'Tilt X: {tilt_x}, Y: {tilt_y}, Z: {tilt_z}')
        print(f'Published: {message}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AccelerometerEmulator()
    ex.show()
    sys.exit(app.exec_())
