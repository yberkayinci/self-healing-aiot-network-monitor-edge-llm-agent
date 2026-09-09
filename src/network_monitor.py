"""Sensing + processing layer.

Measures ICMP round-trip time and DNS resolution time from the host machine,
classifies the result against the thresholds in config.py and publishes the
payload to the MQTT telemetry topic. Runs next to the ESP32 node so the
dashboard keeps receiving data even when the hardware is offline.
"""

import json
import platform
import socket
import subprocess
import time

import paho.mqtt.client as mqtt

import config


def measure_ping(host=config.PING_TARGET):
    """Round-trip time in ms, or -1 when the host is unreachable."""
    flag = "-n" if platform.system().lower() == "windows" else "-c"
    started = time.perf_counter()
    try:
        subprocess.check_output(
            ["ping", flag, "1", host],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return config.PING_FAILURE_MS
    return round((time.perf_counter() - started) * 1000, 2)


def measure_dns(hostname=config.DNS_TARGET):
    """DNS lookup time in ms, or 9999 when resolution fails."""
    started = time.perf_counter()
    try:
        socket.gethostbyname(hostname)
    except socket.gaierror:
        return config.DNS_FAILURE_MS
    return round((time.perf_counter() - started) * 1000, 2)


def classify(latency_ms, dns_ms):
    """Processing layer: turn raw numbers into a single status label."""
    if latency_ms == config.PING_FAILURE_MS:
        return "Disconnected"
    if latency_ms > config.LATENCY_WARN_MS:
        return "High Latency"
    if dns_ms > config.DNS_WARN_MS:
        return "DNS Timeout"
    return "Stable"


def build_payload():
    latency_ms = measure_ping()
    dns_ms = measure_dns()
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "software-agent",
        "rssi": config.SOFTWARE_AGENT_RSSI,
        "latency_ms": latency_ms,
        "dns_ms": dns_ms,
        "status": classify(latency_ms, dns_ms),
    }


def main():
    client = mqtt.Client()
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    client.loop_start()
    print(f"🚀 [SOFTWARE AGENT] Publishing to {config.TOPIC_TELEMETRY}")

    try:
        while True:
            payload = build_payload()
            client.publish(config.TOPIC_TELEMETRY, json.dumps(payload))
            print(
                f"Sent: Ping {payload['latency_ms']}ms | "
                f"DNS {payload['dns_ms']}ms | Status {payload['status']}"
            )
            time.sleep(config.POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n[SOFTWARE AGENT] Stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
