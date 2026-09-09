"""Application layer: Streamlit dashboard.

Subscribes to the telemetry topic, renders live metrics, runs the local LLM on
demand and publishes actuation commands back to the agents. Actions are
semi-automatic on purpose - the model recommends, the operator approves.
"""

import json
import time

import paho.mqtt.client as mqtt
import streamlit as st

import config
from ai_engine import analyze_with_ai

st.set_page_config(
    page_title="Self-Healing AIoT Network Monitor",
    layout="wide",
    page_icon="⚡",
)

st.markdown(
    """
<style>
    [data-testid="stMetricValue"] { font-size: 24px; }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6; border: 1px solid #d6d9e0;
        padding: 15px; border-radius: 10px;
    }
    .stButton button { width: 100%; border-radius: 8px; height: 3em; }
</style>
""",
    unsafe_allow_html=True,
)


# --- MQTT ---
def on_message(client, userdata, msg):
    try:
        userdata["latest"] = json.loads(msg.payload.decode())
        userdata["received_at"] = time.strftime("%H:%M:%S")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"MQTT payload error: {exc}")


@st.cache_resource
def start_listener():
    """One background client per session, shared across Streamlit reruns."""
    buffer = {"latest": None, "received_at": None}
    client = mqtt.Client(userdata=buffer)
    client.on_message = on_message
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
    client.subscribe(config.TOPIC_TELEMETRY)
    client.loop_start()
    return client, buffer


def send_command(command):
    if command not in config.SUPPORTED_COMMANDS:
        return False
    try:
        publisher = mqtt.Client()
        publisher.connect(config.MQTT_BROKER, config.MQTT_PORT, config.MQTT_KEEPALIVE)
        publisher.publish(config.TOPIC_COMMANDS, command)
        publisher.disconnect()
        return True
    except OSError as exc:
        print(f"Command publish failed: {exc}")
        return False


_, telemetry = start_listener()
data = telemetry["latest"]

# --- Layout ---
st.title("⚡ Self-Healing AIoT Network Monitor")
st.markdown("Real-time IoT telemetry, edge LLM diagnosis and operator-approved recovery")

head_left, head_right = st.columns([3, 1])
with head_left:
    st.caption(f"Broker `{config.MQTT_BROKER}:{config.MQTT_PORT}` · Topic `{config.TOPIC_TELEMETRY}` · Model `{config.OLLAMA_MODEL}`")
with head_right:
    auto_refresh = st.toggle("Auto refresh", value=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📡 Live Telemetry")

    if data:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Signal (RSSI)", f"{data.get('rssi', 'N/A')} dBm")
        m2.metric("Latency", f"{data.get('latency_ms', 'N/A')} ms")
        m3.metric("DNS Time", f"{data.get('dns_ms', 'N/A')} ms")
        m4.metric("Last Update", telemetry["received_at"])

        status = data.get("status", "Unknown")
        if "DNS" in status or "Disconnected" in status:
            st.error(f"🌐 Critical: {status}")
        elif "High" in status or "Weak" in status:
            st.warning(f"⚠️ Alert: {status}")
        else:
            st.success(f"✅ System Stable: {status}")

        st.json(data)
    else:
        st.info("Waiting for the telemetry stream - is the ESP32 or software agent running?")

with col2:
    st.subheader("🧠 Edge AI Diagnostics")

    if not data:
        st.caption("Diagnosis needs at least one telemetry sample.")
    elif st.button("Run AI Analysis 🚀"):
        with st.spinner(f"{config.OLLAMA_MODEL} is analyzing..."):
            st.session_state["diagnosis"] = analyze_with_ai(data)
            st.session_state["diagnosis_at"] = time.strftime("%H:%M:%S")

    diagnosis = st.session_state.get("diagnosis")
    if diagnosis:
        score = diagnosis["health_score"]
        st.progress(score)
        st.write(f"Network Health Score: **{score}/100** · {st.session_state['diagnosis_at']}")

        if score < 60:
            st.error(f"📋 **Diagnosis:** {diagnosis['summary']}")
        else:
            st.success(f"📋 **Diagnosis:** {diagnosis['summary']}")

        st.warning(f"🔍 **Root Cause:** {diagnosis['root_cause']}")
        st.info(f"🛠️ **Action:** {diagnosis['recommendation']}")

st.markdown("---")

st.subheader("⚙️ Autonomous Response Panel")
c1, c2 = st.columns(2)
with c1:
    if st.button("🧹 Flush DNS Cache (Real OS)"):
        if send_command("CLEAR_DNS"):
            st.toast("Command sent: flushing DNS cache...", icon="💻")
        else:
            st.toast("Could not reach the broker.", icon="⚠️")
with c2:
    if st.button("🔄 Reset Router (Simulated)"):
        if send_command("RESET_SIMULATION"):
            st.toast("Command sent: rebooting router...", icon="📡")
        else:
            st.toast("Could not reach the broker.", icon="⚠️")

if auto_refresh:
    time.sleep(config.POLL_INTERVAL)
    st.rerun()
