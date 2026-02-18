from flask import Flask, request, jsonify
import time

app = Flask(__name__)


@app.route("/reserve", methods=["POST"])
def reserve():
    # Support failure or delay injection via query params: ?delay=2 or ?fail=true
    delay = request.args.get("delay")
    fail = request.args.get("fail")

    if delay:
        try:
            d = float(delay)
            time.sleep(d)
        except Exception:
            pass

    if fail and fail.lower() in ("1", "true", "yes"):
        return jsonify({"reserved": False, "reason": "injected-failure"}), 500

    data = request.get_json() or {}
    items = data.get("items", [])

    # Very simple: always succeed when not failing
    return jsonify({"reserved": True, "items": items}), 200


@app.route("/", methods=["GET"])
def index():
    return jsonify({"service": "inventory", "status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
