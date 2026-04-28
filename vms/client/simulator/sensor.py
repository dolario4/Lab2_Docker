import os
import time
import random
import paho.mqtt.client as mqtt


class Sensor:
    def __init__(self):
        self.sensor_type = os.getenv("SENSOR_TYPE", "temperature")
        self.sensor_name = os.getenv("SENSOR_NAME", "sensor1")
        self.publish_interval = float(os.getenv("PUBLISH_INTERVAL", "5"))
        self.mqtt_host = os.getenv("MQTT_HOST", "192.168.4.1")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        self.topic = os.getenv("MQTT_TOPIC", f"sensors/{self.sensor_type}")

        self.birth_day = int(os.getenv("BIRTH_DAY", "4"))
        self.birth_month = int(os.getenv("BIRTH_MONTH", "9"))
        self.birth_year = int(os.getenv("BIRTH_YEAR", "2003"))

        self.client = mqtt.Client()

    def connect(self):
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)

    def generate_value(self):
        raise NotImplementedError("Метод generate_value() должен быть переопределен")

    def format_message(self, value):
        return f"{self.sensor_type},name={self.sensor_name} value={value}"

    def run(self):
        self.connect()
        while True:
            value = self.generate_value()
            message = self.format_message(value)
            self.client.publish(self.topic, message)
            print(f"[{self.sensor_name}] topic={self.topic} message={message}", flush=True)
            time.sleep(self.publish_interval)


class TemperatureSensor(Sensor):
    def generate_value(self):
        base = 22.0
        noise = random.uniform(-2.0, 2.0)
        correction = self.birth_month * 0.05
        return round(base + noise + correction, 2)


class PressureSensor(Sensor):
    def generate_value(self):
        base = 1.2
        noise = random.uniform(-0.15, 0.15)
        correction = self.birth_day * 0.001
        return round(base + noise + correction, 3)


class CurrentSensor(Sensor):
    def generate_value(self):
        base = 8.0
        noise = random.uniform(-1.5, 1.5)
        correction = (self.birth_year % 100) * 0.01
        return round(base + noise + correction, 2)


class HumiditySensor(Sensor):
    def generate_value(self):
        base = 55.0
        noise = random.uniform(-8.0, 8.0)
        correction = self.birth_month * 0.2
        return round(base + noise + correction, 2)


def create_sensor():
    sensor_type = os.getenv("SENSOR_TYPE", "temperature").lower()

    if sensor_type == "temperature":
        return TemperatureSensor()
    if sensor_type == "pressure":
        return PressureSensor()
    if sensor_type == "current":
        return CurrentSensor()
    if sensor_type == "humidity":
        return HumiditySensor()

    raise ValueError(f"Unknown sensor type: {sensor_type}")
