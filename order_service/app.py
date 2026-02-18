"""Async RabbitMQ - Order Service"""
from flask import Flask, request, jsonify
import pika
import json
import logging
import os
from datetime import datetime
import sqlite3
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
DB_PATH = "/tmp/orders.db"

# RabbitMQ connection
connection = None
channel = None


def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY,
                  customer_id TEXT,
                  item_id TEXT,
                  quantity INTEGER,
                  status TEXT,
                  created_at TEXT,
                  updated_at TEXT)''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def connect_rabbitmq():
    """Connect to RabbitMQ"""
    global connection, channel
    try:
        credentials = pika.PlainCredentials('guest', 'guest')
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=credentials,
            connection_attempts=5,
            retry_delay=2
        )
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Declare exchanges and queues
        channel.exchange_declare(exchange='orders', exchange_type='topic', durable=True)
        
        channel.queue_declare(queue='orders.created', durable=True)
        channel.queue_bind(exchange='orders', queue='orders.created', routing_key='order.placed')
        
        logger.info("Connected to RabbitMQ")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
        return False


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "order-service"}), 200


@app.route("/order", methods=["POST"])
def create_order():
    """
    POST /order
    Creates an order and publishes OrderPlaced event
    """
    try:
        data = request.get_json()
        order_id = data.get("order_id")
        item_id = data.get("item_id")
        quantity = data.get("quantity", 1)
        customer_id = data.get("customer_id")
        
        if not all([order_id, item_id, customer_id]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Store order in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        try:
            c.execute('''INSERT INTO orders 
                        (order_id, customer_id, item_id, quantity, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (order_id, customer_id, item_id, quantity, 'pending', now, now))
            conn.commit()
            logger.info(f"Order {order_id} stored locally")
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"error": f"Order {order_id} already exists"}), 409
        finally:
            conn.close()
        
        # Publish OrderPlaced event
        try:
            event = {
                "event_type": "OrderPlaced",
                "order_id": order_id,
                "customer_id": customer_id,
                "item_id": item_id,
                "quantity": quantity,
                "created_at": now
            }
            
            channel.basic_publish(
                exchange='orders',
                routing_key='order.placed',
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            logger.info(f"Published OrderPlaced event for {order_id}")
        except Exception as e:
            logger.error(f"Failed to publish event: {str(e)}")
            return jsonify({
                "error": "Failed to publish order event",
                "details": str(e)
            }), 500
        
        return jsonify({
            "order_id": order_id,
            "status": "pending",
            "message": "Order received and queued for processing"
        }), 202
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/orders", methods=["GET"])
def get_orders():
    """Get all orders"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM orders")
        rows = c.fetchall()
        conn.close()
        
        orders = [{
            "order_id": row[0],
            "customer_id": row[1],
            "item_id": row[2],
            "quantity": row[3],
            "status": row[4],
            "created_at": row[5],
            "updated_at": row[6]
        } for row in rows]
        
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    """Get a specific order"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Order not found"}), 404
        
        order = {
            "order_id": row[0],
            "customer_id": row[1],
            "item_id": row[2],
            "quantity": row[3],
            "status": row[4],
            "created_at": row[5],
            "updated_at": row[6]
        }
        
        return jsonify(order), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/orders/<order_id>/status", methods=["PATCH"])
def update_order_status(order_id):
    """Update order status (for testing)"""
    try:
        data = request.get_json()
        status = data.get("status")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        c.execute('''UPDATE orders 
                    SET status = ?, updated_at = ?
                    WHERE order_id = ?''',
                 (status, now, order_id))
        conn.commit()
        conn.close()
        
        return jsonify({"order_id": order_id, "status": status}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.before_request
def before_request():
    """Reconnect to RabbitMQ if needed"""
    global connection, channel
    if connection is None or connection.is_closed or channel is None or channel.is_closed:
        logger.warning("RabbitMQ connection lost, reconnecting...")
        connect_rabbitmq()


if __name__ == "__main__":
    init_db()
    
    # Connect to RabbitMQ
    max_retries = 10
    for i in range(max_retries):
        if connect_rabbitmq():
            break
        if i < max_retries - 1:
            logger.info(f"Retrying RabbitMQ connection ({i+1}/{max_retries})...")
            time.sleep(2)
    
    app.run(host="0.0.0.0", port=5000, debug=False)
