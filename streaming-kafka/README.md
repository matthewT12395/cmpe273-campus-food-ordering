# Streaming Kafka Implementation

This directory contains the Kafka streaming implementation for the food ordering service.

## Structure

```
streaming-kafka/
├── docker-compose.yml          # Kafka and Zookeeper setup
├── producer_order/             # Order event producer
│   ├── producer.py            # Publishes OrderPlaced events
│   └── requirements.txt
├── inventory_consumer/         # Inventory service consumer
│   ├── consumer.py            # Consumes orders, emits inventory events
│   └── requirements.txt
├── analytics_consumer/         # Analytics service consumer
│   ├── consumer.py            # Computes orders/min and failure rate
│   └── requirements.txt
└── tests/                      # Test scripts
    ├── test_producer.py       # Test 10k events production
    ├── test_consumer_lag.py   # Test consumer lag under throttling
    └── test_replay.py         # Test replay and metric consistency
```

## Setup

1. Start Kafka and Zookeeper:
```bash
docker-compose up -d
```

2. Install dependencies:
```bash
pip install -r producer_order/requirements.txt
pip install -r inventory_consumer/requirements.txt
pip install -r analytics_consumer/requirements.txt
pip install -r tests/requirements.txt
```

## Usage

### Producer
Publish OrderPlaced events:
```bash
python producer_order/producer.py
```

### Inventory Consumer
Consume order events and emit inventory events:
```bash
python inventory_consumer/consumer.py
```

### Analytics Consumer
Consume events and compute metrics:
```bash
python analytics_consumer/consumer.py
```

## Testing

### Produce 10k Events
```bash
python tests/test_producer.py
```

### Test Consumer Lag
```bash
python tests/test_consumer_lag.py
```

### Test Replay
```bash
python tests/test_replay.py
```

## Features

- **Producer**: Publishes OrderPlaced events to order-events topic
- **Inventory Consumer**: Consumes orders and emits InventoryEvents
- **Analytics Consumer**: Computes:
  - Orders per minute
  - Failure rate
  - Supports replay by resetting consumer offset

## Metrics Output

The analytics consumer generates metrics files:
- `metrics_output.txt` - Standard metrics output
- `metrics_after_replay.txt` - Metrics after replay demonstration

## Documentation

For detailed usage instructions and architecture explanation, see:
- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Complete guide on how to use the system and understand component relationships
