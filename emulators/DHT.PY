import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QTimer
import paho.mqtt.client as mqtt

broker = 'broker.hivemq.com'
port = 1883
topic = "iot/sensors/dht"

class DHTEmulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.connect(broker, port)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('DHT Emulator (Temperature & Humidity)')
        layout = QVBoxLayout()
        
        self.temp_label = QLabel('Temperature: Waiting...')
        self.humidity_label = QLabel('Humidity: Waiting...')
        self.start_button = QPushButton('Start Publishing Data')
        self.start_button.clicked.connect(self.start_publishing)

        layout.addWidget(self.temp_label)
        layout.addWidget(self.humidity_label)
        layout.addWidget(self.start_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_publishing(self):
        self.start_button.setDisabled(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.publish_data)
        self.timer.start(10000)  # Publish every 10 seconds

    def publish_data(self):
        temperature = round(random.uniform(20.0, 30.0), 1)
        humidity = round(random.uniform(30.0, 60.0), 1)
        message = f"Temperature: {temperature} C, Humidity: {humidity}%"
        self.client.publish(topic, message)
        self.temp_label.setText(f'Temperature: {temperature} C')
        self.humidity_label.setText(f'Humidity: {humidity}%')
        print(f'Published: {message}')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DHTEmulator()
    ex.show()
    sys.exit(app.exec_())
