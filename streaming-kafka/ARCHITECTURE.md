# System Architecture & Component Relationships

## High-Level Architecture

```
┌─────────────────┐
│   Producer      │  Creates OrderPlaced events
│  (producer.py)  │
└────────┬────────┘
         │
         │ Publishes to Kafka
         ↓
┌─────────────────────────────────┐
│      Kafka Topic                │
│    "order-events"               │  ← Event stream storage
│                                 │
│  [Event1] [Event2] [Event3]...  │
└────────┬────────────────────────┘
         │
         │ Multiple consumers can read same events
         │
    ┌────┴────┐
    ↓         ↓
┌─────────┐ ┌──────────────────┐
│Inventory│ │   Analytics      │
│Consumer │ │   Consumer       │
└────┬────┘ └────────┬──────────┘
     │              │
     │              │ Computes:
     │              │ • Orders/min
     │              │ • Failure rate
     ↓              ↓
┌─────────────┐  ┌──────────────┐
│inventory-   │  │ metrics_     │
│events topic │  │ output.txt   │
└─────────────┘  └──────────────┘
```

## Component Details

### 1. Producer (`producer_order/producer.py`)

**Role**: Event Source
- **Input**: None (generates events)
- **Output**: Publishes to `order-events` Kafka topic
- **Event Type**: `OrderPlaced`
- **Key Features**:
  - Can produce 10,000+ events for testing
  - Simulates real order data (items, prices, users)
  - ~5% failure rate simulation

**Event Structure**:
```python
{
  "event_type": "OrderPlaced",
  "order_id": "order_000001",
  "user_id": "user_123",
  "items": [{"item_id": "burger", "quantity": 2, "price": 10.0}],
  "total_amount": 20.0,
  "status": "placed" or "failed",
  "timestamp": "2024-01-15T10:30:00"
}
```

### 2. Inventory Consumer (`inventory_consumer/consumer.py`)

**Role**: Order Processor → Inventory Manager
- **Input**: Consumes from `order-events` topic
- **Output**: Publishes to `inventory-events` topic
- **What it does**:
  1. Reads `OrderPlaced` events
  2. For each item in the order, emits `InventoryEvent`
  3. Action: "reserve" (if placed) or "release" (if failed)

**Relationship**: 
- **Depends on**: Producer (needs events to process)
- **Independent**: Can run in parallel with Analytics Consumer
- **One-to-many**: One order → multiple inventory events (one per item)

### 3. Analytics Consumer (`analytics_consumer/consumer.py`)

**Role**: Metrics Calculator
- **Input**: Consumes from `order-events` topic
- **Output**: Computed metrics (printed + saved to file)
- **Metrics Computed**:
  1. **Total Orders**: Count of all events
  2. **Failed Orders**: Count of events with `status="failed"`
  3. **Failure Rate**: `(failed_orders / total_orders) × 100`
  4. **Orders per Minute**: 
     - Groups events by minute
     - Calculates average and current rate

**Key Feature - Replay**:
- Can reset consumer offset to beginning
- Replays all events and recomputes metrics
- Demonstrates that replay produces consistent results

**Relationship**:
- **Depends on**: Producer (needs events to analyze)
- **Independent**: Can run in parallel with Inventory Consumer
- **Read-only**: Doesn't modify events, only analyzes them

## Data Flow Example

### Scenario: User places an order

```
1. Producer creates event:
   OrderPlaced(order_id="order_001", items=[burger, fries], status="placed")
   
2. Event stored in Kafka:
   order-events topic: [OrderPlaced: order_001]
   
3. Inventory Consumer reads event:
   → Emits: InventoryEvent(item="burger", action="reserve")
   → Emits: InventoryEvent(item="fries", action="reserve")
   
4. Analytics Consumer reads same event:
   → Increments total_orders: 1
   → Increments orders_this_minute: 1
   → Updates failure_rate calculation
```

## Testing Components

### `tests/test_producer.py`
- **Purpose**: Verify producer can handle 10k events
- **What it tests**: Event generation and publishing
- **Success criteria**: All 10k events published successfully

### `tests/test_consumer_lag.py`
- **Purpose**: Demonstrate consumer lag
- **What it tests**: What happens when producer is faster than consumer
- **Shows**: Kafka's ability to buffer events

### `tests/test_replay.py`
- **Purpose**: Verify replay consistency
- **What it tests**: 
  1. Process events → compute metrics
  2. Reset offset → replay events → recompute metrics
  3. Compare: metrics should match
- **Success criteria**: Metrics are identical (or very close)

## Why This Architecture?

### Benefits:

1. **Decoupling**: Producer doesn't know about consumers
   - Can add new consumers without changing producer
   - Consumers can be added/removed independently

2. **Scalability**: 
   - Multiple consumers can process same events
   - Can scale consumers horizontally

3. **Replayability**: 
   - Events are persisted in Kafka
   - Can reset offset and reprocess
   - Useful for debugging, testing, recovery

4. **Resilience**:
   - If consumer crashes, events aren't lost
   - Can resume from last processed position

5. **Real-time Analytics**:
   - Analytics consumer computes metrics as events arrive
   - No need to query database
   - Always up-to-date

## File Relationships

```
docker-compose.yml
    └── Defines Kafka infrastructure (used by all components)

producer_order/
    ├── producer.py → Publishes to Kafka
    └── requirements.txt → kafka-python dependency

inventory_consumer/
    ├── consumer.py → Reads from Kafka, publishes to Kafka
    └── requirements.txt → kafka-python dependency

analytics_consumer/
    ├── consumer.py → Reads from Kafka, computes metrics
    └── requirements.txt → kafka-python dependency

tests/
    ├── test_producer.py → Uses producer_order module
    ├── test_consumer_lag.py → Uses producer + analytics modules
    ├── test_replay.py → Uses producer + analytics modules
    └── requirements.txt → kafka-python dependency
```

## Execution Order

### Typical Workflow:

1. **Start Infrastructure**: `docker-compose up -d`
2. **Start Consumers** (can run in parallel):
   - `python analytics_consumer/consumer.py`
   - `python inventory_consumer/consumer.py` (optional)
3. **Start Producer**: `python producer_order/producer.py`
4. **Observe**: Consumers process events in real-time

### Testing Workflow:

1. **Test Producer**: `python tests/test_producer.py`
2. **Test Lag**: `python tests/test_consumer_lag.py`
3. **Test Replay**: `python tests/test_replay.py`
4. **Check Output**: Review `metrics_*.txt` files

## Key Concepts

### Consumer Groups
- Each consumer belongs to a "consumer group"
- Same group = share work (load balancing)
- Different groups = each gets all events (broadcast)
- Our setup: Each consumer uses its own group (gets all events)

### Offsets
- Kafka tracks position in stream (offset)
- Consumer reads from last offset
- Reset offset = start from beginning (replay)

### Topics
- `order-events`: Main event stream
- `inventory-events`: Secondary stream (inventory operations)


