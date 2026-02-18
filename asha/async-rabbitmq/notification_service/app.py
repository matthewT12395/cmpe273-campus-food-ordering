"""Async RabbitMQ - Notification Service Consumer"""
import pika
import json
import logging
import os
import sqlite3
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
DB_PATH = "/tmp/notifications.db"


def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (notification_id TEXT PRIMARY KEY,
                  order_id TEXT,
                  customer_id TEXT,
                  message TEXT,
                  status TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def on_message_received(ch, method, properties, body):
    """Callback when InventoryReserved message is received"""
    try:
        event = json.loads(body)
        event_type = event.get("event_type")
        
        logger.info(f"Received event: {event_type}")
        
        if event_type == "InventoryReserved":
            handle_inventory_reserved(ch, method, event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def handle_inventory_reserved(ch, method, event):
    """Process InventoryReserved event"""
    order_id = event.get("order_id")
    customer_id = event.get("order_id")  # In real scenario, this would come from order service
    item_id = event.get("item_id")
    quantity = event.get("quantity")
    
    try:
        notification_id = f"NOTIF-{order_id}"
        message = f"Your order {order_id} for {quantity} units of {item_id} has been confirmed!"
        
        # Store notification
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO notifications 
                    (notification_id, order_id, customer_id, message, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (notification_id, order_id, customer_id, message, "sent", datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        logger.info(f"Notification sent for order {order_id}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error handling notification: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def main():
    """Start the notification service consumer"""
    logger.info("Starting Notification Service Consumer")
    
    init_db()
    
    # Connect to RabbitMQ
    max_retries = 10
    connection = None
    
    for i in range(max_retries):
        try:
            credentials = pika.PlainCredentials('guest', 'guest')
            parameters = pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials
            )
            connection = pika.BlockingConnection(parameters)
            logger.info("Connected to RabbitMQ")
            break
        except Exception as e:
            logger.warning(f"RabbitMQ connection attempt {i+1}/{max_retries} failed: {str(e)}")
            if i < max_retries - 1:
                time.sleep(2)
    
    if connection is None:
        logger.error("Failed to connect to RabbitMQ")
        return
    
    channel = connection.channel()
    
    # Declare exchanges and queues
    channel.exchange_declare(exchange='orders', exchange_type='topic', durable=True)
    
    channel.queue_declare(queue='notifications.pending', durable=True)
    channel.queue_bind(exchange='orders', queue='notifications.pending', routing_key='inventory.event')
    
    # Set QoS
    channel.basic_qos(prefetch_count=1)
    
    # Consume messages
    channel.basic_consume(queue='notifications.pending', on_message_callback=on_message_received)
    
    logger.info("Waiting for messages...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()
        logger.info("Connection closed")


if __name__ == "__main__":
    main()
