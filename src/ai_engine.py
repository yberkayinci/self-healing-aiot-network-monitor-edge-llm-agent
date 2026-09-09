"""Analytics layer: local LLM diagnosis of a telemetry sample.

The model runs through Ollama on the same machine, so telemetry never leaves
the network and the pipeline keeps working without internet access.
"""

import json
import re

import ollama

import config

SYSTEM_PROMPT = """
You are a senior Network Reliability Engineer (SRE). Your job is to analyze network telemetry JSON and output a DIAGNOSIS JSON.

RULES:
1. Output MUST be valid JSON. Do not use Markdown (```json). Do not talk.
2. Use Double Quotes (") for keys and values.
3. JSON Keys must be exactly: "summary", "root_cause", "recommendation", "health_score".

EXAMPLE INPUT:
{"rssi": -85, "latency_ms": 300, "dns_ms": 20, "status": "Weak Signal"}

EXAMPLE OUTPUT:
{
    "summary": "Connection quality is poor due to weak Wi-Fi signal.",
    "root_cause": "Device is too far from the router or obstructed.",
    "recommendation": "Move device closer to access point or use a repeater.",
    "health_score": 45
}

NOW ANALYZE THE USER INPUT AND GENERATE SIMILAR JSON OUTPUT.
"""

REQUIRED_KEYS = ("summary", "root_cause", "recommendation", "health_score")

_client = ollama.Client(host=config.OLLAMA_HOST) if config.OLLAMA_HOST else ollama


def _extract_json(raw_text):
    """Small models like to wrap JSON in prose or fences - cut it back out."""
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")
    return json.loads(match.group(0))


def _normalise(diagnosis):
    if not isinstance(diagnosis, dict):
        raise ValueError("Model output is not a JSON object.")

    # Small models sometimes drop a field; keep whatever they did produce.
    for key in REQUIRED_KEYS:
        diagnosis.setdefault(key, "Not reported by the model.")

    try:
        score = int(float(diagnosis["health_score"]))
    except (TypeError, ValueError):
        score = 0
    diagnosis["health_score"] = max(0, min(100, score))
    return diagnosis


def analyze_with_ai(network_data, model=None):
    """Return a diagnosis dict. Never raises - the dashboard stays usable."""
    model = model or config.OLLAMA_MODEL
    try:
        response = _client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"INPUT DATA: {json.dumps(network_data)}"},
            ],
        )
        raw_text = response["message"]["content"]
        print(f"DEBUG (RAW AI OUTPUT): {raw_text}")
        return _normalise(_extract_json(raw_text))

    except Exception as exc:  # noqa: BLE001 - surfaced in the UI instead
        print(f"AI ENGINE ERROR: {exc}")
        return {
            "summary": "AI analysis failed to parse.",
            "root_cause": f"{type(exc).__name__}: {exc}",
            "recommendation": "Check that Ollama is running and the model is pulled.",
            "health_score": 0,
        }
