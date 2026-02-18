from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/send", methods=["POST"])
def send():
    data = request.get_json() or {}
    # In a real app we'd send email/SMS; here we just acknowledge
    return jsonify({"sent": True, "payload": data}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
