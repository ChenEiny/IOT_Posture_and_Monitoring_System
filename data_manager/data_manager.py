import sqlite3
import paho.mqtt.client as mqtt
import logging

# Setup Logging using the standard logger
logger = logging.getLogger(__name__)
handler = logging.FileHandler('data_manager.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

db_path = 'iot_data.db'  # Path to SQLite database

# Ensure the 'sensor_data' table exists
def ensure_table_exists():
    try:
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
        logger.info("Ensured sensor_data table exists.")
    except Exception as e:
        logger.error(f"Error ensuring table exists: {e}")

# Function to log data into the database
def log_to_db(topic, message):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sensor_data (topic, message) VALUES (?, ?)", (topic, message))
        conn.commit()
        conn.close()
        # Keep logging data-related events
        logger.info(f"Data logged to database - Topic: {topic}, Message: {message}")
    except Exception as e:
        logger.error(f"Error logging to database: {e}")

# Callback for MQTT messages
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    topic = msg.topic

    # Only log raw data from sensors; no alerts here
    if "dht" in topic or "accelerometer" in topic or "pressure" in topic:
        logger.info(f"Received message on topic {topic}: {message}")

    # Log the message to the database
    log_to_db(topic, message)

# Start the data manager with MQTT connection
def start_data_manager():
    logger.info(f"Using database at path: {db_path}")
    ensure_table_exists()  # Ensure the table is created

    client = mqtt.Client()
    client.connect('broker.hivemq.com', 1883)
    client.subscribe("iot/sensors/accelerometer")
    client.subscribe("iot/sensors/pressure")
    client.subscribe("iot/sensors/dht")
    client.on_message = on_message
    logger.info("Data Manager started and subscribed to accelerometer, pressure, and DHT topics.")
    client.loop_forever()

if __name__ == "__main__":
    start_data_manager()
