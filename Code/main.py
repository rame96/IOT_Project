from fastapi import FastAPI
from typing import Dict
import paho.mqtt.client as mqtt
import pyttsx3  # For speech output
import logging  # For logging events

# FastAPI app instance
app = FastAPI()

# Bin configuration
BIN_HEIGHT_MM = 600  # Bin height in mm
THRESHOLD_PERCENTAGE = 80  # Alert threshold in percentage

# Bin configuration
sensor_data = {
    "distance_mm": 0,  # Initial distance
    "fill_percentage": 0  # Initial fill percentage (calculated)
}

# MQTT Configuration
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/distance"

# MQTT Client setup
mqtt_client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    """
    Callback when the MQTT client connects to the broker.
    """
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC)  # Subscribe to the topic
    else:
        print(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    """
    Callback when a message is received from the MQTT broker.
    """
    global sensor_data
    try:
        # Parse the message payload (assuming it’s a raw number in mm)
        distance = float(msg.payload.decode())
        sensor_data["distance_mm"] = distance
        sensor_data["fill_percentage"] = max(
            0, 100 - (distance / BIN_HEIGHT_MM) * 100
        )
        print(f"Received distance: {distance} mm, Fill percentage: {sensor_data['fill_percentage']}%")
    except ValueError:
        print(f"Invalid payload: {msg.payload.decode()}")


# Assign callbacks to the MQTT client
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Start the MQTT client in a background thread
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# Initialize text-to-speech engine
tts_engine = pyttsx3.init()

# Setup logging
logging.basicConfig(filename="bin_alerts.log", level=logging.INFO, format="%(asctime)s - %(message)s")


@app.get("/bin/status", response_model=Dict[str, float])
async def get_bin_status():
    """
    Returns the current status of the bin including fill percentage.
    """
    # Return the latest sensor data
    return sensor_data


@app.post("/bin/alert")
async def check_bin_alert():
    """
    Checks if the bin fill percentage exceeds the threshold and triggers an alert.
    """
    if sensor_data["fill_percentage"] >= THRESHOLD_PERCENTAGE:
        message = "Bin is over 80% full. Please empty it!"

        # Trigger speech output
        tts_engine.say(message)
        tts_engine.runAndWait()

        # Log the alert event
        logging.info(message)

        return {"alert": True, "message": message}

    return {"alert": False, "message": "Bin is below the alert threshold."}
