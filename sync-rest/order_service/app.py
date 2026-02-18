from flask import Flask, request, jsonify
import os
import requests
import time

app = Flask(__name__)

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://inventory:5001")
NOTIFICATION_URL = os.environ.get("NOTIFICATION_URL", "http://notification:5002")
REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "5"))
RETRY_COUNT = int(os.environ.get("RETRY_COUNT", "2"))
RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", "0.5"))


def post_with_retries(url, json=None, params=None, timeout=REQUEST_TIMEOUT):
    last_exc = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            return requests.post(url, json=json, params=params, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_BACKOFF * (2 ** attempt))
            else:
                raise


@app.route("/order", methods=["POST"])
def order():
    data = request.get_json() or {}
    params = {}
    if "delay" in data:
        params["delay"] = data["delay"]
    if "fail" in data:
        params["fail"] = data["fail"]

    # Call Inventory service with retries and timeouts
    try:
        resp = post_with_retries(f"{INVENTORY_URL}/reserve", json={"items": data.get("items", [])}, params=params)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "inventory-unavailable", "details": str(e)}), 503

    if resp.status_code != 200:
        return jsonify({"error": "reserve-failed", "status": resp.status_code, "body": resp.text}), 502

    # If reserved, call notification service but don't retry on notification failures (it's best-effort)
    try:
        nresp = requests.post(f"{NOTIFICATION_URL}/send", json={"order": data}, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as e:
        return jsonify({"order_status": "placed", "notification_status": "failed", "details": str(e)}), 200

    return jsonify({"order_status": "placed", "notification_status": nresp.status_code}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
