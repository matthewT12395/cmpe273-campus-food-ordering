"""Async RabbitMQ - Inventory Service Consumer"""
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
DB_PATH = "/tmp/inventory.db"

# In-memory inventory
inventory = {
    "ITEM001": {"name": "Pizza", "quantity": 100},
    "ITEM002": {"name": "Burger", "quantity": 50},
    "ITEM003": {"name": "Salad", "quantity": 75},
}

# Track processed messages for idempotency
processed_messages = set()


def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reservations
                 (reservation_id TEXT PRIMARY KEY,
                  order_id TEXT UNIQUE,
                  item_id TEXT,
                  quantity INTEGER,
                  status TEXT,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS failed_reservations
                 (order_id TEXT PRIMARY KEY,
                  item_id TEXT,
                  quantity INTEGER,
                  reason TEXT,
                  created_at TEXT)''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def on_message_received(ch, method, properties, body):
    """Callback when OrderPlaced message is received"""
    try:
        event = json.loads(body)
        event_type = event.get("event_type")
        order_id = event.get("order_id")
        
        logger.info(f"Received event: {event_type} for order {order_id}")
        
        # Check for duplicate processing (idempotency)
        message_id = f"{order_id}:{method.delivery_tag}"
        if order_id in processed_messages:
            logger.warning(f"Duplicate message for order {order_id}, skipping")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        if event_type == "OrderPlaced":
            handle_order_placed(ch, method, event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {str(e)}")
        # Send to DLQ
        send_to_dlq(ch, properties, body, "invalid_json")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Send to DLQ
        send_to_dlq(ch, properties, body, str(e))
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def handle_order_placed(ch, method, event):
    """Process OrderPlaced event"""
    order_id = event.get("order_id")
    item_id = event.get("item_id")
    quantity = event.get("quantity", 1)
    
    try:
        # Check inventory
        available = inventory.get(item_id, {}).get("quantity", 0)
        
        if available < quantity:
            logger.warning(f"Insufficient inventory for {item_id}: needed {quantity}, available {available}")
            
            # Store failed reservation
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''INSERT INTO failed_reservations 
                        (order_id, item_id, quantity, reason, created_at)
                        VALUES (?, ?, ?, ?, ?)''',
                     (order_id, item_id, quantity, "insufficient_quantity", datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            
            # Publish InventoryFailed event
            publish_event(ch, {
                "event_type": "InventoryFailed",
                "order_id": order_id,
                "item_id": item_id,
                "quantity": quantity,
                "reason": "insufficient_quantity",
                "created_at": datetime.utcnow().isoformat()
            })
        else:
            # Reserve inventory
            inventory[item_id]["quantity"] -= quantity
            reservation_id = f"RES-{order_id}"
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''INSERT INTO reservations 
                        (reservation_id, order_id, item_id, quantity, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (reservation_id, order_id, item_id, quantity, "reserved", datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            
            logger.info(f"Reserved {quantity} units of {item_id} for order {order_id}")
            
            # Publish InventoryReserved event
            publish_event(ch, {
                "event_type": "InventoryReserved",
                "order_id": order_id,
                "item_id": item_id,
                "quantity": quantity,
                "reservation_id": reservation_id,
                "created_at": datetime.utcnow().isoformat()
            })
        
        # Mark as processed (idempotency)
        processed_messages.add(order_id)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error handling order: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def publish_event(ch, event):
    """Publish an event"""
    try:
        ch.basic_publish(
            exchange='orders',
            routing_key='inventory.event',
            body=json.dumps(event),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        logger.info(f"Published {event['event_type']} event")
    except Exception as e:
        logger.error(f"Failed to publish event: {str(e)}")


def send_to_dlq(ch, properties, body, reason):
    """Send message to Dead Letter Queue"""
    try:
        # Try to parse body, but if it fails, just use as string
        try:
            if isinstance(body, bytes):
                original_msg = body.decode('utf-8')
            else:
                original_msg = body
        except:
            original_msg = str(body)
        
        dlq_event = {
            "original_message": original_msg,
            "error_reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to use existing channel first
        try:
            ch.basic_publish(
                exchange='',
                routing_key='dlq.inventory',
                body=json.dumps(dlq_event),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            logger.info(f"Sent message to DLQ: {reason}")
        except Exception as channel_error:
            # If channel fails, create a new connection and send
            logger.warning(f"Channel publish failed, using new connection: {channel_error}")
            try:
                dlq_conn = pika.BlockingConnection(
                    pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
                )
                dlq_ch = dlq_conn.channel()
                dlq_ch.queue_declare(queue='dlq.inventory', durable=True)
                dlq_ch.basic_publish(
                    exchange='',
                    routing_key='dlq.inventory',
                    body=json.dumps(dlq_event),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                dlq_ch.close()
                dlq_conn.close()
                logger.info(f"Sent message to DLQ via new connection: {reason}")
            except Exception as new_conn_error:
                logger.error(f"Failed to send to DLQ via new connection: {new_conn_error}")
    except Exception as e:
        logger.error(f"Failed to send to DLQ: {str(e)}")


def main():
    """Start the inventory service consumer"""
    logger.info("Starting Inventory Service Consumer")
    
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
    
    channel.queue_declare(queue='orders.created', durable=True)
    channel.queue_bind(exchange='orders', queue='orders.created', routing_key='order.placed')
    
    channel.queue_declare(queue='dlq.inventory', durable=True)
    
    # Set QoS
    channel.basic_qos(prefetch_count=1)
    
    # Consume messages
    channel.basic_consume(queue='orders.created', on_message_callback=on_message_received)
    
    logger.info("Waiting for messages...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()
        logger.info("Connection closed")


if __name__ == "__main__":
    main()
