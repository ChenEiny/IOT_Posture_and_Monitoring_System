import logging
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget, QLineEdit, QPushButton, QFormLayout, QWidget, QLabel, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt, QTimer,  QMetaObject, Q_ARG, pyqtSlot
import time
import sys
import paho.mqtt.client as mqtt


# Setup Logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('gui.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

db_path = 'iot_data.db'

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_to_db(topic, message):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sensor_data (topic, message) VALUES (?, ?)", (topic, message))
        conn.commit()
        conn.close()
        logger.info(f"Data logged to database - Topic: {topic}, Message: {message}")
    except Exception as e:
        logger.error(f"Error logging to database: {e}")

# MQTT Client Class
class Mqtt_client:
    def __init__(self, main_window):
        self.broker = 'broker.hivemq.com'  # HiveMQ broker
        self.port = 1883
        self.client = None
        self.connected = False
        self.main_window = main_window  # Reference to the main window
        self.last_published_message = None  # Store the last published message


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Successfully connected to {self.broker}:{self.port}")
            self.main_window.connectionDock.update_button_color(connected=True)
        else:
            logger.error(f"Failed to connect. Returned code={rc}")
            self.main_window.connectionDock.update_button_color(connected=False)

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"Message received from {topic}: {payload}")

        # Ignore messages that were recently published by this client
        if topic == "iot/alerts" and payload == self.last_published_message:
            logger.info("Ignoring message received from the broker as it was recently published by this client.")
            return

        # Log data to DB
        log_to_db(topic, payload)

        # Dispatch the updates to the main thread using QMetaObject.invokeMethod
        if "posture" in topic:
            QMetaObject.invokeMethod(self.main_window.postureDock, "update_posture_data",
                                    Qt.QueuedConnection, Q_ARG(str, payload))
        elif "environment" in topic or "dht" in topic:
            QMetaObject.invokeMethod(self.main_window.environmentDock, "update_environment_data",
                                    Qt.QueuedConnection, Q_ARG(str, payload))
        elif "alerts" in topic:
            QMetaObject.invokeMethod(self.main_window.alertDock, "show_alert",
                                    Qt.QueuedConnection, Q_ARG(str, payload), Q_ARG(str, 'good'))

        elif "accelerometer" in topic:
            QMetaObject.invokeMethod(self.main_window.accelerometerDock, "update_accel_data",
                                    Qt.QueuedConnection, Q_ARG(str, payload))
        elif "pressure" in topic:
            QMetaObject.invokeMethod(self.main_window.pressureDock, "update_pressure_data",
                                    Qt.QueuedConnection, Q_ARG(str, payload))




    def publish_message(self, topic, message):
        self.client.publish(topic, message)
        logger.info(f"Published message to {topic}: {message}")
        self.last_published_message = message  # Track the last published message


    def connect_to_broker(self, broker, port):
        self.broker = broker
        self.port = port
        logger.info(f"Attempting to connect to {broker}:{port}")
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.connect(broker, port)

        # Subscribing to the topics
        self.client.subscribe("iot/sensors/dht")
        self.client.subscribe("iot/sensors/pressure")
        self.client.subscribe("iot/sensors/accelerometer")
        self.client.subscribe("iot/alerts")
        self.client.loop_start()
        self.connected = True

# Connection Dock
class ConnectionDock(QDockWidget):
    def __init__(self, mc):
        super().__init__()
        self.mc = mc
        self.setWindowTitle("Connection Panel")

        self.eHostInput = QLineEdit("broker.hivemq.com")
        self.ePort = QLineEdit("1883")
        self.eConnectButton = QPushButton("Connect")
        self.eConnectButton.setStyleSheet("background-color: red")
        self.eConnectButton.clicked.connect(self.on_connect_click)

        formLayout = QFormLayout()
        formLayout.addRow("Host", self.eHostInput)
        formLayout.addRow("Port", self.ePort)
        formLayout.addRow("", self.eConnectButton)

        widget = QWidget()
        widget.setLayout(formLayout)
        self.setWidget(widget)

    def on_connect_click(self):
        broker = self.eHostInput.text()
        port = int(self.ePort.text())
        self.mc.connect_to_broker(broker, port)

    def update_button_color(self, connected):
        if connected:
            self.eConnectButton.setStyleSheet("background-color: green")
            self.eConnectButton.setText("Connected")
        else:
            self.eConnectButton.setStyleSheet("background-color: red")
            self.eConnectButton.setText("Connect")

# Posture Dock
class PostureDock(QDockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Posture Monitoring")
        self.postureLabel = QTextEdit()
        self.postureLabel.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.postureLabel)
        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

        # Flags and data storage
        self.is_new_accel_data = False
        self.is_new_pressure_data = False
        self.current_tilt_x = 0.0
        self.current_tilt_y = 0.0
        self.current_seat_pressure = 0
        self.current_back_pressure = 0

        self.previous_alert = None  # Initialize the previous_alert attribute

        # Alert cooldown timer
        self.alert_timer = QTimer(self)
        self.alert_timer.setSingleShot(True)
        self.alert_timer.timeout.connect(self.reset_alert_state)
        self.alert_cooldown = False

        logger.info("PostureDock initialized.")

    @pyqtSlot(float, float)
    def update_accel_data(self, tilt_x, tilt_y):
        logger.info(f"Accelerometer data received - X: {tilt_x}, Y: {tilt_y}")
        self.current_tilt_x = tilt_x
        self.current_tilt_y = tilt_y
        self.is_new_accel_data = True

        # Check if both accelerometer and pressure data have been updated
        self.check_and_calculate_posture()

    @pyqtSlot(int, int)
    def update_pressure_data(self, seat_pressure, back_pressure):
        logger.info(f"Pressure data received - Seat: {seat_pressure}, Back: {back_pressure}")
        self.current_seat_pressure = seat_pressure
        self.current_back_pressure = back_pressure
        self.is_new_pressure_data = True

        # Check if both accelerometer and pressure data have been updated
        self.check_and_calculate_posture()

    def check_and_calculate_posture(self):
        # Only calculate posture if both accelerometer and pressure data have been updated
        if self.is_new_accel_data and self.is_new_pressure_data:
            logger.info("Both data sets received, calculating posture.")
            self.calculate_posture()

            # Reset the flags so that the next round of data can be processed
            self.is_new_accel_data = False
            self.is_new_pressure_data = False

    def calculate_posture(self):
        # Display the current accelerometer and pressure data
        data_message = (
            f"Accelerometer Data: X: {self.current_tilt_x}, Y: {self.current_tilt_y}\n"
            f"Pressure Data: Seat: {self.current_seat_pressure}, Back: {self.current_back_pressure}\n"
        )

        # Append data message to postureLabel without overwriting old data
        self.postureLabel.append(data_message)

        pressure_threshold_absolute = 38
        pressure_threshold_percent = 20.0  # Percentage difference
        tilt_threshold_magnitude = 15.0  # Overall tilt magnitude

        # Calculate percentage difference in seat and back pressure
        avg_pressure = (self.current_seat_pressure + self.current_back_pressure) / 2.0
        pressure_difference_percent = abs(self.current_seat_pressure - self.current_back_pressure) / avg_pressure * 100

        # Calculate tilt magnitude from X, Y, and Z components
        tilt_magnitude = (self.current_tilt_x**2 + self.current_tilt_y**2 )**0.5

        # Posture evaluation logic: determine bad or good posture
        bad_posture = (
            abs(self.current_seat_pressure - self.current_back_pressure) > pressure_threshold_absolute or
            pressure_difference_percent > pressure_threshold_percent or
            tilt_magnitude > tilt_threshold_magnitude
        )

        # Always trigger an alert regardless of whether the posture has changed
        if bad_posture:
            self.trigger_alert("Bad posture detected!", alert_type='bad')
            self.previous_alert = "bad"
        else:
            self.trigger_alert("Good posture!", alert_type='good')
            self.previous_alert = "good"



    def trigger_alert(self, message, alert_type):
        logger.info(f"Triggering alert: {message}")

        # Always send the alert if new data is received, even if it's the same posture
        self.previous_alert_time = time.time()  # Add a timestamp to track when the last alert was sent
        self.parent().alertDock.show_alert(message, alert_type=alert_type)
        self.parent().mc.publish_message("iot/alerts", message)


    def reset_alert_state(self):
        self.alert_cooldown = False


# Environmental Monitoring Dock
class EnvironmentDock(QDockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Environmental Data")
        self.envLabel = QLabel("Temperature and Humidity: No Data")
        layout = QVBoxLayout()
        layout.addWidget(self.envLabel)
        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

    @pyqtSlot(str)  # Added this decorator
    def update_environment_data(self, data):
        self.envLabel.setText(f"Temperature and Humidity: {data}")

class AccelerometerDock(QDockWidget):
    def __init__(self, main_window):
        super().__init__()
        self.setWindowTitle("Accelerometer Monitoring")
        self.accelLabel = QTextEdit()
        self.accelLabel.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.accelLabel)
        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

        self.main_window = main_window

    @pyqtSlot(str)  # Ensure the method is marked as a slot and accepts a string argument
    def update_accel_data(self, data: str):
        try:
            tilt_x = float(data.split("Tilt X: ")[1].split(",")[0])
            tilt_y = float(data.split("Tilt Y: ")[1].split(",")[0])
            tilt_z = float(data.split("Tilt Z: ")[1].split(",")[0])

            # Append new data instead of replacing old data
            new_data = f"X: {tilt_x}, Y: {tilt_y}, Z: {tilt_z}\n"
            self.accelLabel.append(new_data)

            # Pass data to PostureDock
            self.main_window.postureDock.update_accel_data(tilt_x, tilt_y)
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing accelerometer data: {e}")







class PressureDock(QDockWidget):
    def __init__(self, main_window):
        super().__init__()
        self.setWindowTitle("Pressure Monitoring")
        self.pressureLabel = QTextEdit()
        self.pressureLabel.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.pressureLabel)
        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

        self.main_window = main_window

    @pyqtSlot(str)  # Added this decorator
    def update_pressure_data(self, data: str):
        try:
            # Parse the string data (coming from the MQTT message payload)
            seat_pressure_str = data.split("Seat Pressure: ")[1].split(",")[0].strip()
            back_pressure_str = data.split("Back Pressure: ")[1].strip()

            seat_pressure = int(seat_pressure_str)
            back_pressure = int(back_pressure_str)

            # Append new pressure data without overwriting old data
            new_data = f"Seat: {seat_pressure}, Back: {back_pressure}\n"
            self.pressureLabel.append(new_data)

            # Pass the data to PostureDock
            self.main_window.postureDock.update_pressure_data(seat_pressure, back_pressure)
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing pressure data: {e}")




class AlertDock(QDockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alerts")
        self.alertBox = QTextEdit()
        self.alertBox.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.alertBox)
        widget = QWidget()
        widget.setLayout(layout)
        self.setWidget(widget)

    @pyqtSlot(str, str)  # Ensure that it accepts both message and alert_type
    def show_alert(self, message: str, alert_type: str = 'good'):
        color = "red" if alert_type == 'bad' else "green"
        alert_message = f"<p style='color:{color};'>Alert: {message}</p>"
        self.alertBox.append(alert_message)




class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mc = Mqtt_client(self)

        self.postureDock = PostureDock()

        self.connectionDock = ConnectionDock(self.mc)
        self.environmentDock = EnvironmentDock()
        self.accelerometerDock = AccelerometerDock(self)  # Pass main_window reference
        self.pressureDock = PressureDock(self)            # Pass main_window reference
        self.alertDock = AlertDock()

        # Set up the main window layout
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('IoT Posture & Environment Monitoring')

        # Add docks to the main window
        self.addDockWidget(Qt.TopDockWidgetArea, self.connectionDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.postureDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.environmentDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.accelerometerDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.pressureDock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.alertDock)

        logger.info("Main window initialized with all docks.")

if __name__ == "__main__":
    init_db()  # Initialize the database
    app = QApplication(sys.argv)
    mainwin = MainWindow()
    mainwin.show()
    app.exec_()
