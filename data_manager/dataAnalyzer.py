import logging
import paho.mqtt.client as mqtt

# Setup Logging
logger = logging.getLogger(__name__)
handler = logging.FileHandler('data_analyzer.log')
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Function to analyze temperature data from DHT
def analyze_data(topic, message):
    try:
        if "Temperature" in message:
            # Extract the temperature value and remove the "C" and space
            temp_value_str = message.split(":")[1].split(",")[0].strip().replace(" C", "")
            temp_value = float(temp_value_str)
            if temp_value > 29.0:
                logger.warning(f"High temperature detected: {temp_value}°C")
                return f"<p style='color:blue;'>High temperature detected: {temp_value}°C</p>"
        return None
    except Exception as e:
        logger.error(f"Error analyzing data: {e}")
        return None

# Callback for MQTT messages
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    topic = msg.topic

    # Only log temperature-related messages; avoid other sensor types
    if "dht" in topic:
        logger.info(f"Received message on topic {topic}: {message}")

        # Analyze the message for alerts
        alert = analyze_data(topic, message)
        if alert:
            logger.info(f"Alert triggered: {alert}")
            client.publish("iot/alerts", alert)  # Send alert via MQTT to the GUI alert dock

# Start the data analyzer with MQTT connection
def start_analyzer():
    client = mqtt.Client()
    client.connect('broker.hivemq.com', 1883)
    client.subscribe("iot/sensors/dht")  # Subscribe only to DHT sensor data
    client.on_message = on_message
    logger.info("Data Analyzer started and subscribed to DHT sensors.")
    client.loop_forever()

if __name__ == "__main__":
    start_analyzer()
