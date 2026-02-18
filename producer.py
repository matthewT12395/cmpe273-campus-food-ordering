"""
Producer that publishes OrderEvents stream: OrderPlaced
"""
import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer
from typing import Dict, Any


class OrderEventProducer:
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'order-events'):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        self.topic = topic

    def publish_order_placed(self, order_id: str, user_id: str, items: list, 
                             total_amount: float, status: str = "placed") -> None:
        """Publish an OrderPlaced event"""
        event = {
            "event_type": "OrderPlaced",
            "order_id": order_id,
            "user_id": user_id,
            "items": items,
            "total_amount": total_amount,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Use order_id as key for partitioning
        self.producer.send(self.topic, key=order_id, value=event)
        self.producer.flush()
        print(f"Published OrderPlaced event: {order_id}")

    def produce_events(self, num_events: int = 10000) -> None:
        """Produce a specified number of events for testing"""
        print(f"Producing {num_events} events...")
        
        for i in range(num_events):
            order_id = f"order_{i:06d}"
            user_id = f"user_{random.randint(1, 1000)}"
            items = [
                {"item_id": f"item_{j}", "quantity": random.randint(1, 3), 
                 "price": round(random.uniform(5.0, 25.0), 2)}
                for j in range(random.randint(1, 5))
            ]
            total_amount = sum(item["quantity"] * item["price"] for item in items)
            
            # Simulate some failures (status = "failed")
            status = "placed" if random.random() > 0.05 else "failed"
            
            self.publish_order_placed(order_id, user_id, items, total_amount, status)
            
            # Small delay to avoid overwhelming
            if i % 1000 == 0:
                print(f"Produced {i} events...")
                time.sleep(0.1)
        
        print(f"Finished producing {num_events} events")

    def close(self):
        """Close the producer"""
        self.producer.close()


if __name__ == "__main__":
    producer = OrderEventProducer()
    try:
        # Produce 10k events for testing
        producer.produce_events(10000)
    except KeyboardInterrupt:
        print("\nStopping producer...")
    finally:
        producer.close()


