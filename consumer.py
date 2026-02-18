"""
Inventory consumer that consumes OrderEvents and emits InventoryEvents
"""
import json
from kafka import KafkaConsumer, KafkaProducer
from typing import Dict, Any


class InventoryConsumer:
    def __init__(self, 
                 bootstrap_servers: str = 'localhost:9092',
                 order_topic: str = 'order-events',
                 inventory_topic: str = 'inventory-events',
                 group_id: str = 'inventory-consumer-group'):
        self.consumer = KafkaConsumer(
            order_topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        self.inventory_topic = inventory_topic

    def process_order(self, order_event: Dict[str, Any]) -> None:
        """Process an order event and emit inventory events"""
        if order_event.get('event_type') != 'OrderPlaced':
            return
        
        order_id = order_event.get('order_id')
        items = order_event.get('items', [])
        status = order_event.get('status', 'placed')
        
        # Emit inventory events for each item
        for item in items:
            inventory_event = {
                "event_type": "InventoryEvent",
                "order_id": order_id,
                "item_id": item.get('item_id'),
                "quantity": item.get('quantity'),
                "action": "reserve" if status == "placed" else "release",
                "timestamp": order_event.get('timestamp')
            }
            
            self.producer.send(
                self.inventory_topic, 
                key=item.get('item_id'), 
                value=inventory_event
            )
            print(f"Inventory event emitted: {inventory_event['action']} {inventory_event['quantity']} of {inventory_event['item_id']}")
        
        self.producer.flush()

    def consume(self) -> None:
        """Start consuming order events"""
        print("Inventory consumer started. Waiting for order events...")
        try:
            for message in self.consumer:
                order_event = message.value
                print(f"Received order event: {order_event.get('order_id')}")
                self.process_order(order_event)
        except KeyboardInterrupt:
            print("\nStopping inventory consumer...")
        finally:
            self.consumer.close()
            self.producer.close()

    def reset_offset(self) -> None:
        """Reset consumer offset to earliest (for replay demonstration)"""
        print("Resetting consumer offset to earliest...")
        self.consumer.close()
        self.consumer = KafkaConsumer(
            'order-events',
            bootstrap_servers='localhost:9092',
            group_id=self.consumer.config['group_id'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        print("Offset reset complete. Ready to replay events.")


if __name__ == "__main__":
    consumer = InventoryConsumer()
    try:
        consumer.consume()
    except KeyboardInterrupt:
        print("\nStopping consumer...")
    finally:
        consumer.consumer.close()
        consumer.producer.close()


