"""Central configuration for every layer of the pipeline.

All values can be overridden with environment variables (see .env.example),
so the same code runs against the public test broker or a private one.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


def _env_float(name, default):
    return float(os.getenv(name, default))


def _env_int(name, default):
    return int(os.getenv(name, default))


# --- Connectivity layer (MQTT) ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = _env_int("MQTT_PORT", 1883)
MQTT_KEEPALIVE = _env_int("MQTT_KEEPALIVE", 60)

# Everything hangs off one prefix so a second deployment only needs one change.
TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "NihatBerkay/iot_project")
TOPIC_TELEMETRY = f"{TOPIC_PREFIX}/telemetry"
TOPIC_COMMANDS = f"{TOPIC_PREFIX}/commands"

# --- Analytics layer (local LLM) ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi4-mini:3.8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")  # None -> ollama default (127.0.0.1:11434)

# --- Sensing layer ---
PING_TARGET = os.getenv("PING_TARGET", "8.8.8.8")
DNS_TARGET = os.getenv("DNS_TARGET", "www.google.com")
POLL_INTERVAL = _env_float("POLL_INTERVAL", 2)
# The software agent has no radio, so it reports a fixed reference value.
# Real RSSI comes from the ESP32 node.
SOFTWARE_AGENT_RSSI = _env_int("SOFTWARE_AGENT_RSSI", -50)

# --- Processing layer thresholds ---
LATENCY_WARN_MS = _env_float("LATENCY_WARN_MS", 150)
DNS_WARN_MS = _env_float("DNS_WARN_MS", 500)
DNS_FAILURE_MS = 9999
PING_FAILURE_MS = -1

# --- Actuation layer ---
SUPPORTED_COMMANDS = ("CLEAR_DNS", "RESET_SIMULATION")
