"""
Test script to demonstrate consumer lag under throttling
"""
import time
import sys
import os
from kafka import KafkaConsumer
import json

# Add project root to path so we can import local packages
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from producer_order.producer import OrderEventProducer
from analytics_consumer.consumer import AnalyticsConsumer


def test_consumer_lag():
    """Demonstrate consumer lag by producing events faster than consuming"""
    print("="*50)
    print("TEST: Consumer Lag Under Throttling")
    print("="*50)
    
    producer = OrderEventProducer()
    consumer = AnalyticsConsumer(group_id='test-analytics-group')
    
    print("\nStep 1: Starting consumer (will process slowly)...")
    print("Step 2: Producing events at high rate...")
    print("Step 3: Observing consumer lag...\n")
    
    # Start consumer in a way that processes slowly (simulating throttling)
    import threading
    
    def slow_consume():
        """Consume with artificial delay to simulate throttling"""
        count = 0
        try:
            for message in consumer.consumer:
                order_event = message.value
                consumer.process_order_event(order_event)
                count += 1
                
                # Simulate throttling - process slowly
                time.sleep(0.01)  # 10ms delay per event
                
                if count % 100 == 0:
                    print(f"Consumer processed {count} events...")
        except Exception as e:
            print(f"Consumer error: {e}")
    
    # Start consumer thread
    consumer_thread = threading.Thread(target=slow_consume, daemon=True)
    consumer_thread.start()
    
    # Give consumer a moment to start
    time.sleep(2)
    
    # Produce events quickly
    print("Producing 1000 events quickly...")
    start_time = time.time()
    for i in range(1000):
        order_id = f"test_order_{i:06d}"
        producer.publish_order_placed(
            order_id=order_id,
            user_id=f"user_{i % 100}",
            items=[{"item_id": f"item_{i}", "quantity": 1, "price": 10.0}],
            total_amount=10.0,
            status="placed" if i % 20 != 0 else "failed"
        )
    
    producer.close()
    produce_time = time.time() - start_time
    print(f"Finished producing 1000 events in {produce_time:.2f} seconds")
    
    # Wait for consumer to catch up
    print("\nWaiting for consumer to process events...")
    time.sleep(30)
    
    # Print final metrics
    consumer.print_metrics()
    print("\nNote: If consumer processed fewer events than produced,")
    print("this demonstrates consumer lag under throttling.")


if __name__ == "__main__":
    test_consumer_lag()


