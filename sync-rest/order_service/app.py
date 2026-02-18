from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

INVENTORY_URL = os.environ.get("INVENTORY_URL", "http://inventory:5001")
NOTIFICATION_URL = os.environ.get("NOTIFICATION_URL", "http://notification:5002")


@app.route("/order", methods=["POST"])
def order():
    data = request.get_json() or {}
    # Forward reserve request to Inventory. Accept optional `delay` and `fail` in payload and forward as query params
    params = {}
    if "delay" in data:
        params["delay"] = data["delay"]
    if "fail" in data:
        params["fail"] = data["fail"]

    try:
        # Default simple forward (timeout/backoff will be added later)
        resp = requests.post(f"{INVENTORY_URL}/reserve", json={"items": data.get("items", [])}, params=params, timeout=5)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "inventory-unavailable", "details": str(e)}), 503

    if resp.status_code != 200:
        return jsonify({"error": "reserve-failed", "status": resp.status_code, "body": resp.text}), 502

    # If reserved, call notification service
    try:
        nresp = requests.post(f"{NOTIFICATION_URL}/send", json={"order": data}, timeout=5)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "notification-failed", "details": str(e)}), 502

    return jsonify({"order_status": "placed", "notification_status": nresp.status_code}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
