/*
 * Perception layer - ESP32 telemetry node.
 *
 * Publishes Wi-Fi signal strength, a TCP round-trip measurement and DNS
 * resolution time to the MQTT telemetry topic as JSON. The payload matches
 * exactly what src/network_monitor.py publishes, so the dashboard and the
 * LLM engine do not care which node a sample came from.
 *
 * Libraries: PubSubClient (Nick O'Leary)
 * Board:     ESP32 Dev Module (Arduino core for ESP32)
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>

#include "secrets.h"

// --- Sensing configuration ---
static const char *PING_HOST = "8.8.8.8";
static const uint16_t PING_PORT = 53;          // DNS port answers a TCP handshake
static const char *DNS_HOST = "www.google.com";
static const uint32_t PUBLISH_INTERVAL_MS = 2000;

// --- Processing thresholds (mirror of src/config.py) ---
static const long LATENCY_WARN_MS = 150;
static const long DNS_WARN_MS = 500;

// --- NTP, so samples carry a real timestamp ---
static const char *NTP_SERVER = "pool.ntp.org";
static const long GMT_OFFSET_SEC = 3 * 3600;   // UTC+3
static const int DAYLIGHT_OFFSET_SEC = 0;

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char payload[256];
uint32_t lastPublish = 0;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  Serial.printf("Connecting to Wi-Fi \"%s\"", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nConnected. IP: %s\n", WiFi.localIP().toString().c_str());
  configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);
}

void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = "esp32-telemetry-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.printf("Connecting to broker %s:%d ...\n", MQTT_BROKER, MQTT_PORT);
    if (mqtt.connect(clientId.c_str())) {
      Serial.printf("Broker connected. Publishing to %s\n", MQTT_TOPIC_TELEMETRY);
    } else {
      Serial.printf("Failed (state %d), retrying in 2s\n", mqtt.state());
      delay(2000);
    }
  }
}

// TCP handshake time to the ping host, or -1 when unreachable.
long measureLatency() {
  WiFiClient probe;
  probe.setTimeout(3);
  uint32_t started = millis();
  if (!probe.connect(PING_HOST, PING_PORT)) {
    return -1;
  }
  long elapsed = (long)(millis() - started);
  probe.stop();
  return elapsed;
}

long measureDns() {
  IPAddress resolved;
  uint32_t started = millis();
  if (!WiFi.hostByName(DNS_HOST, resolved)) {
    return 9999;
  }
  return (long)(millis() - started);
}

const char *classify(long latencyMs, long dnsMs) {
  if (latencyMs < 0) {
    return "Disconnected";
  }
  if (latencyMs > LATENCY_WARN_MS) {
    return "High Latency";
  }
  if (dnsMs > DNS_WARN_MS) {
    return "DNS Timeout";
  }
  return "Stable";
}

void isoTimestamp(char *buffer, size_t size) {
  struct tm timeInfo;
  if (getLocalTime(&timeInfo, 100)) {
    strftime(buffer, size, "%Y-%m-%dT%H:%M:%S", &timeInfo);
  } else {
    snprintf(buffer, size, "uptime+%lus", millis() / 1000);
  }
}

void publishTelemetry() {
  long latencyMs = measureLatency();
  long dnsMs = measureDns();
  char timestamp[32];
  isoTimestamp(timestamp, sizeof(timestamp));

  snprintf(payload, sizeof(payload),
           "{\"timestamp\":\"%s\",\"source\":\"esp32\",\"rssi\":%d,"
           "\"latency_ms\":%ld,\"dns_ms\":%ld,\"status\":\"%s\"}",
           timestamp, WiFi.RSSI(), latencyMs, dnsMs, classify(latencyMs, dnsMs));

  if (mqtt.publish(MQTT_TOPIC_TELEMETRY, payload)) {
    Serial.println(payload);
  } else {
    Serial.println("Publish failed.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  connectWiFi();
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setKeepAlive(60);
  connectMqtt();
}

void loop() {
  connectWiFi();
  if (!mqtt.connected()) {
    connectMqtt();
  }
  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
    lastPublish = millis();
    publishTelemetry();
  }
}
