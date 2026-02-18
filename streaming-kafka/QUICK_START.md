# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Start Kafka
```bash
cd streaming-kafka
docker-compose up -d
```

### 2. Install Dependencies
```bash
pip install -r producer_order/requirements.txt
pip install -r analytics_consumer/requirements.txt
```

### 3. Run the System

**Terminal 1** - Start Analytics Consumer:
```bash
python analytics_consumer/consumer.py
```

**Terminal 2** - Produce Events:
```bash
python producer_order/producer.py
```

Watch Terminal 1 to see metrics being computed in real-time!

## 📊 What Each Component Does

| Component | Purpose | What It Does |
|-----------|---------|--------------|
| **Producer** | Creates events | Publishes `OrderPlaced` events to Kafka |
| **Inventory Consumer** | Manages inventory | Reads orders, emits inventory events |
| **Analytics Consumer** | Computes metrics | Calculates orders/min and failure rate |

## 🔄 Event Flow

```
Producer → Kafka (order-events) → Analytics Consumer → Metrics
                              → Inventory Consumer → Inventory Events
```

## 🧪 Run Tests

```bash
# Test 1: Produce 10k events
python tests/test_producer.py

# Test 2: Show consumer lag
python tests/test_consumer_lag.py

# Test 3: Demonstrate replay
python tests/test_replay.py
```

## 📁 Output Files

After running, check:
- `metrics_output.txt` - Your metrics report
- `metrics_after_replay.txt` - Metrics after replay

For more details, see [USAGE_GUIDE.md](USAGE_GUIDE.md)


