"""
Analytics consumer that consumes streams and computes:
- orders per minute
- failure rate
Supports replay by resetting consumer offset
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict
from kafka import KafkaConsumer
from typing import Dict, Any, List


class AnalyticsConsumer:
    def __init__(self,
                 bootstrap_servers: str = 'localhost:9092',
                 order_topic: str = 'order-events',
                 group_id: str = 'analytics-consumer-group'):
        self.consumer = KafkaConsumer(
            order_topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        self.order_topic = order_topic
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        
        # Metrics tracking
        self.orders_by_minute = defaultdict(int)
        self.total_orders = 0
        self.failed_orders = 0
        self.order_timestamps = []

    def process_order_event(self, order_event: Dict[str, Any]) -> None:
        """Process an order event and update metrics"""
        if order_event.get('event_type') != 'OrderPlaced':
            return
        
        self.total_orders += 1
        status = order_event.get('status', 'placed')
        
        if status == 'failed':
            self.failed_orders += 1
        
        # Parse timestamp and group by minute
        try:
            timestamp_str = order_event.get('timestamp')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                minute_key = timestamp.replace(second=0, microsecond=0)
                self.orders_by_minute[minute_key] += 1
                self.order_timestamps.append(timestamp)
        except Exception as e:
            print(f"Error parsing timestamp: {e}")

    def compute_metrics(self) -> Dict[str, Any]:
        """Compute and return current metrics"""
        failure_rate = (self.failed_orders / self.total_orders * 100) if self.total_orders > 0 else 0
        
        # Calculate average orders per minute
        if self.orders_by_minute:
            total_minutes = len(self.orders_by_minute)
            total_orders_in_period = sum(self.orders_by_minute.values())
            avg_orders_per_minute = total_orders_in_period / total_minutes if total_minutes > 0 else 0
        else:
            avg_orders_per_minute = 0
        
        # Calculate current orders per minute (last minute)
        current_minute = datetime.utcnow().replace(second=0, microsecond=0)
        current_orders_per_minute = self.orders_by_minute.get(current_minute, 0)
        
        metrics = {
            "total_orders": self.total_orders,
            "failed_orders": self.failed_orders,
            "failure_rate_percent": round(failure_rate, 2),
            "average_orders_per_minute": round(avg_orders_per_minute, 2),
            "current_orders_per_minute": current_orders_per_minute,
            "orders_by_minute": dict(sorted(self.orders_by_minute.items()))
        }
        
        return metrics

    def print_metrics(self) -> None:
        """Print current metrics"""
        metrics = self.compute_metrics()
        print("\n" + "="*50)
        print("ANALYTICS METRICS")
        print("="*50)
        print(f"Total Orders: {metrics['total_orders']}")
        print(f"Failed Orders: {metrics['failed_orders']}")
        print(f"Failure Rate: {metrics['failure_rate_percent']}%")
        print(f"Average Orders per Minute: {metrics['average_orders_per_minute']}")
        print(f"Current Orders per Minute: {metrics['current_orders_per_minute']}")
        print("="*50 + "\n")

    def save_metrics(self, filename: str = "metrics_output.txt") -> None:
        """Save metrics to a file"""
        metrics = self.compute_metrics()
        with open(filename, 'w') as f:
            f.write("ANALYTICS METRICS REPORT\n")
            f.write("="*50 + "\n")
            f.write(f"Total Orders: {metrics['total_orders']}\n")
            f.write(f"Failed Orders: {metrics['failed_orders']}\n")
            f.write(f"Failure Rate: {metrics['failure_rate_percent']}%\n")
            f.write(f"Average Orders per Minute: {metrics['average_orders_per_minute']}\n")
            f.write(f"Current Orders per Minute: {metrics['current_orders_per_minute']}\n")
            f.write("\nOrders by Minute:\n")
            for minute, count in sorted(metrics['orders_by_minute'].items()):
                f.write(f"  {minute}: {count} orders\n")
            f.write("="*50 + "\n")
        print(f"Metrics saved to {filename}")

    def reset_metrics(self) -> None:
        """Reset all metrics (for replay)"""
        self.orders_by_minute = defaultdict(int)
        self.total_orders = 0
        self.failed_orders = 0
        self.order_timestamps = []
        print("Metrics reset. Ready for replay.")

    def reset_offset(self) -> None:
        """Reset consumer offset to earliest (for replay demonstration)"""
        print("Resetting consumer offset to earliest for replay...")
        self.consumer.close()
        self.consumer = KafkaConsumer(
            self.order_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        print("Offset reset complete. Ready to replay events.")

    def consume(self, print_interval: int = 100) -> None:
        """Start consuming order events and compute metrics"""
        print("Analytics consumer started. Computing metrics...")
        try:
            for message in self.consumer:
                order_event = message.value
                self.process_order_event(order_event)
                
                # Print metrics periodically
                if self.total_orders % print_interval == 0:
                    self.print_metrics()
        except KeyboardInterrupt:
            print("\nStopping analytics consumer...")
            self.print_metrics()
        finally:
            self.consumer.close()

    def replay_and_recompute(self) -> None:
        """Demonstrate replay: reset offset and recompute metrics"""
        print("\n=== REPLAY DEMONSTRATION ===")
        print("Resetting metrics and consumer offset...")
        self.reset_metrics()
        self.reset_offset()
        
        print("Replaying events and recomputing metrics...")
        try:
            for message in self.consumer:
                order_event = message.value
                self.process_order_event(order_event)
        except KeyboardInterrupt:
            print("\nReplay complete.")
            self.print_metrics()
            self.save_metrics("metrics_after_replay.txt")
        finally:
            self.consumer.close()


if __name__ == "__main__":
    consumer = AnalyticsConsumer()
    try:
        # Consume events and compute metrics
        consumer.consume(print_interval=1000)
    except KeyboardInterrupt:
        print("\nStopping consumer...")
        consumer.print_metrics()
        consumer.save_metrics()
    finally:
        consumer.consumer.close()


