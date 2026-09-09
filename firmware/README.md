# ESP32 Telemetry Node

Perception-layer firmware for the hardware node. It samples Wi-Fi RSSI, a TCP
round-trip time and DNS resolution time, then publishes them as JSON on the
MQTT telemetry topic - the same schema the Python software agent uses.

## Build

1. Install the [Arduino core for ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html)
   and select **ESP32 Dev Module** as the board.
2. Install the **PubSubClient** library (Library Manager → search "PubSubClient").
3. Copy the credentials header and fill it in:

   ```bash
   cp esp32_telemetry/secrets.h.example esp32_telemetry/secrets.h
   ```

4. Open `esp32_telemetry/esp32_telemetry.ino`, upload, and watch the serial
   monitor at **115200 baud**.

`MQTT_TOPIC_TELEMETRY` in `secrets.h` must match `MQTT_TOPIC_PREFIX` on the
Python side (`src/config.py` / `.env`), otherwise the dashboard will not see
the node.

## Published payload

```json
{
  "timestamp": "2025-12-18T22:38:09",
  "source": "esp32",
  "rssi": -37,
  "latency_ms": 149,
  "dns_ms": 0,
  "status": "Stable"
}
```

Thresholds (`LATENCY_WARN_MS`, `DNS_WARN_MS`) are mirrored from `src/config.py`;
change both if you retune them.
