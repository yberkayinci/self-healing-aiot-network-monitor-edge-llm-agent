"""Actuation layer: subscribes to the command topic and executes recovery steps.

Only the commands listed in config.SUPPORTED_COMMANDS are executed; anything
else on the topic is logged and dropped. CLEAR_DNS touches the real operating
system, RESET_SIMULATION is a simulated router reboot.
"""

import platform
import subprocess
import time

import paho.mqtt.client as mqtt

import config


def flush_dns():
    system = platform.system().lower()
    if system == "windows":
        return ["ipconfig", "/flushdns"]
    if system == "darwin":
        return ["dscacheutil", "-flushcache"]
    return ["resolvectl", "flush-caches"]


def handle_clear_dns():
    print("⚙️  Action: flushing the OS DNS resolver cache...")
    time.sleep(1)
    result = subprocess.run(flush_dns(), capture_output=True, text=True)
    output = (result.stdout or result.stderr).strip()
    if output:
        print(output)
    if result.returncode == 0:
        print("✅  SUCCESS: operating system executed the command.")
    else:
        print(f"❌  FAILED: exit code {result.returncode}.")


def handle_reset_simulation():
    print("⚠️  Action: router reboot sequence...")
    time.sleep(2)
    print("✅  SUCCESS: virtual router restarted.")


HANDLERS = {
    "CLEAR_DNS": handle_clear_dns,
    "RESET_SIMULATION": handle_reset_simulation,
}


def on_connect(client, userdata, flags, rc):
    print(f"🤖 [SYSTEM AGENT] Connected. Listening on: {config.TOPIC_COMMANDS}")
    client.subscribe(config.TOPIC_COMMANDS)


def on_message(client, userdata, msg):
    command = msg.payload.decode(errors="replace").strip()
    print(f"\n📩 NEW COMMAND: {command}")

    handler = HANDLERS.get(command)
    if handler is None:
        print("🚫  Ignored: command is not in the allow-list.")
        return
    try:
        handler()
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"❌  Execution error: {exc}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[SYSTEM AGENT] Stopped.")
        client.disconnect()


if __name__ == "__main__":
    main()
