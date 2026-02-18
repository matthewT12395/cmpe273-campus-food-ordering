"""
Test script to produce 10k events and demonstrate consumer lag under throttling
"""
import time
import sys
import os

# Add project root to path so we can import producer_order as a package
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from producer_order.producer import OrderEventProducer


def test_produce_10k_events():
    """Produce 10k events for testing"""
    print("="*50)
    print("TEST: Producing 10,000 events")
    print("="*50)
    
    producer = OrderEventProducer()
    start_time = time.time()
    
    try:
        producer.produce_events(10000)
        end_time = time.time()
        elapsed = end_time - start_time
        
        print(f"\nTest completed in {elapsed:.2f} seconds")
        print(f"Average rate: {10000/elapsed:.2f} events/second")
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        producer.close()


if __name__ == "__main__":
    test_produce_10k_events()


