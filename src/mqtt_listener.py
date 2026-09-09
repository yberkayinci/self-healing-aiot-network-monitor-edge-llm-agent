"""Terminal monitor for the telemetry topic - handy when debugging the pipeline
without opening the dashboard.
"""

import json

import paho.mqtt.client as mqtt

import config


def on_connect(client, userdata, flags, rc):
    print(f"✅ Monitoring: {config.TOPIC_TELEMETRY}")
    client.subscribe(config.TOPIC_TELEMETRY)


def on_message(client, userdata, msg):
    print("\n📩 NEW TELEMETRY:")
    try:
        data = json.loads(msg.payload.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        print(f"   ⚠️  Unparsable payload: {msg.payload!r}")
        return

    print(f"   📡 Signal: {data.get('rssi')} dBm")
    print(f"   ⚡ Ping:   {data.get('latency_ms')} ms")
    print(f"   🌐 DNS:    {data.get('dns_ms')} ms")
    print(f"   📊 Status: {data.get('status')}")
    print("-" * 30)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        client.disconnect()


if __name__ == "__main__":
    main()
