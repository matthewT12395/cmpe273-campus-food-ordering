"""
Test script to demonstrate replay: reset consumer offset and recompute metrics
"""
import time
import sys
import os

# Add project root to path so we can import local packages
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from producer_order.producer import OrderEventProducer
from analytics_consumer.consumer import AnalyticsConsumer


def test_replay():
    """Demonstrate replay by resetting offset and recomputing metrics"""
    print("="*50)
    print("TEST: Replay Demonstration")
    print("="*50)
    
    # Step 1: Produce some events
    print("\nStep 1: Producing initial 1000 events...")
    producer = OrderEventProducer()
    producer.produce_events(1000)
    producer.close()
    time.sleep(2)
    
    # Step 2: Consume and compute initial metrics
    print("\nStep 2: Consuming events and computing initial metrics...")
    consumer1 = AnalyticsConsumer(group_id='replay-test-group-1')
    
    event_count = 0
    try:
        for message in consumer1.consumer:
            order_event = message.value
            consumer1.process_order_event(order_event)
            event_count += 1
            
            if event_count >= 1000:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        consumer1.consumer.close()
    
    print("\nInitial Metrics:")
    consumer1.print_metrics()
    consumer1.save_metrics("metrics_initial.txt")
    
    # Step 3: Reset offset and replay
    print("\nStep 3: Resetting consumer offset and replaying events...")
    consumer2 = AnalyticsConsumer(group_id='replay-test-group-2')
    consumer2.reset_metrics()
    consumer2.reset_offset()
    
    event_count = 0
    try:
        for message in consumer2.consumer:
            order_event = message.value
            consumer2.process_order_event(order_event)
            event_count += 1
            
            if event_count >= 1000:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        consumer2.consumer.close()
    
    print("\nMetrics After Replay:")
    consumer2.print_metrics()
    consumer2.save_metrics("metrics_after_replay.txt")
    
    # Step 4: Compare metrics
    print("\nStep 4: Comparing metrics...")
    initial_metrics = consumer1.compute_metrics()
    replay_metrics = consumer2.compute_metrics()
    
    print("\nComparison:")
    print(f"Initial Total Orders: {initial_metrics['total_orders']}")
    print(f"Replay Total Orders: {replay_metrics['total_orders']}")
    print(f"Initial Failure Rate: {initial_metrics['failure_rate_percent']}%")
    print(f"Replay Failure Rate: {replay_metrics['failure_rate_percent']}%")
    
    if (initial_metrics['total_orders'] == replay_metrics['total_orders'] and
        abs(initial_metrics['failure_rate_percent'] - replay_metrics['failure_rate_percent']) < 0.01):
        print("\n✓ Metrics are consistent! Replay produced same results.")
    else:
        print("\n⚠ Metrics differ. This may be due to:")
        print("  - Events processed in different order")
        print("  - Timing differences in timestamp parsing")
        print("  - Consumer group offset differences")


if __name__ == "__main__":
    test_replay()


