# Usage Guide: Kafka Streaming Food Ordering Service

## Overview

This system implements a **streaming event-driven architecture** for a food ordering service using Kafka. Events flow through the system as follows:

```
Producer → Kafka Topic → Consumers
           (order-events)
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Inventory Consumer   Analytics Consumer
    ↓                   ↓
(inventory-events)   (metrics computation)
```

## System Architecture

### 1. **Producer** (`producer_order/`)
- **Purpose**: Publishes order events to Kafka
- **What it does**: Creates `OrderPlaced` events when orders are placed
- **Output**: Events published to `order-events` Kafka topic

### 2. **Inventory Consumer** (`inventory_consumer/`)
- **Purpose**: Processes orders and manages inventory
- **What it does**: 
  - Consumes `OrderPlaced` events from `order-events` topic
  - Emits `InventoryEvent` events to `inventory-events` topic
  - Reserves/releases inventory based on order status

### 3. **Analytics Consumer** (`analytics_consumer/`)
- **Purpose**: Computes real-time metrics from order events
- **What it does**:
  - Consumes `OrderPlaced` events from `order-events` topic
  - Computes **orders per minute**
  - Computes **failure rate** (percentage of failed orders)
  - Supports **replay** by resetting consumer offset

## Step-by-Step Usage

### Step 1: Start Kafka Infrastructure

First, start Kafka and Zookeeper using Docker:

```bash
cd streaming-kafka
docker-compose up -d
```

Wait a few seconds for Kafka to be ready. Verify it's running:
```bash
docker-compose ps
```

### Step 2: Install Dependencies

Install Python dependencies for all components:

```bash
# Install for producer
pip install -r producer_order/requirements.txt

# Install for consumers
pip install -r inventory_consumer/requirements.txt
pip install -r analytics_consumer/requirements.txt

# Install for tests
pip install -r tests/requirements.txt
```

### Step 3: Run the System

You'll need **3 terminal windows** to run all components simultaneously:

#### Terminal 1: Analytics Consumer
```bash
cd streaming-kafka
python analytics_consumer/consumer.py
```
This will start consuming events and computing metrics. It will print metrics every 1000 events.

#### Terminal 2: Inventory Consumer (Optional)
```bash
cd streaming-kafka
python inventory_consumer/consumer.py
```
This processes orders and emits inventory events.

#### Terminal 3: Producer
```bash
cd streaming-kafka
python producer_order/producer.py
```
This will produce 10,000 events. Watch Terminal 1 to see metrics being computed in real-time.

## Testing Scenarios

### Test 1: Produce 10k Events

This tests the system's ability to handle a large volume of events:

```bash
cd streaming-kafka
python tests/test_producer.py
```

**What happens:**
- Produces exactly 10,000 `OrderPlaced` events
- Each event has random order data (items, prices, etc.)
- ~5% of events are marked as "failed" (to test failure rate calculation)
- Events are published to the `order-events` topic

**Expected output:**
- Progress messages every 1000 events
- Total time and average rate

### Test 2: Consumer Lag Under Throttling

This demonstrates what happens when consumers can't keep up with producers:

```bash
cd streaming-kafka
python tests/test_consumer_lag.py
```

**What happens:**
- Producer sends 1000 events quickly
- Consumer processes events slowly (with artificial delay)
- Demonstrates consumer lag (consumer falls behind producer)

**What to observe:**
- Producer finishes quickly
- Consumer takes longer to process all events
- This shows the system's ability to buffer events in Kafka

### Test 3: Replay Demonstration

This shows how to reset consumer offset and recompute metrics:

```bash
cd streaming-kafka
python tests/test_replay.py
```

**What happens:**
1. Produces 1000 events
2. First consumer processes events and computes metrics → saves to `metrics_initial.txt`
3. Resets consumer offset to beginning
4. Second consumer replays all events and recomputes metrics → saves to `metrics_after_replay.txt`
5. Compares both metrics to show consistency

**Expected result:**
- Both metrics should be identical (or very close)
- This demonstrates that replay produces consistent results

## Understanding the Metrics

The analytics consumer computes:

1. **Total Orders**: Count of all `OrderPlaced` events processed
2. **Failed Orders**: Count of orders with `status="failed"`
3. **Failure Rate**: Percentage of failed orders (failed/total × 100)
4. **Average Orders per Minute**: Average across all minutes
5. **Current Orders per Minute**: Orders in the current minute
6. **Orders by Minute**: Breakdown showing orders per minute

## Output Files

After running tests, you'll find:

- `metrics_output.txt` - Standard metrics report
- `metrics_initial.txt` - Metrics before replay
- `metrics_after_replay.txt` - Metrics after replay (should match initial)

## How Components Relate

### Event Flow Example

1. **Order is placed** → Producer creates event:
   ```json
   {
     "event_type": "OrderPlaced",
     "order_id": "order_000001",
     "user_id": "user_123",
     "items": [{"item_id": "burger", "quantity": 2, "price": 10.0}],
     "total_amount": 20.0,
     "status": "placed",
     "timestamp": "2024-01-15T10:30:00"
   }
   ```

2. **Event published to Kafka** → Stored in `order-events` topic

3. **Inventory Consumer receives event** → Emits inventory events:
   ```json
   {
     "event_type": "InventoryEvent",
     "order_id": "order_000001",
     "item_id": "burger",
     "quantity": 2,
     "action": "reserve"
   }
   ```

4. **Analytics Consumer receives event** → Updates metrics:
   - Increments total orders counter
   - If status="failed", increments failure counter
   - Groups by minute for orders/min calculation

### Why This Architecture?

- **Decoupled**: Producer doesn't need to know about consumers
- **Scalable**: Multiple consumers can process same events
- **Replayable**: Can reset offset and reprocess events
- **Resilient**: Events are persisted in Kafka, won't be lost

## Troubleshooting

### Kafka not running?
```bash
docker-compose up -d
docker-compose logs kafka
```

### Consumer not receiving events?
- Check that producer is running
- Verify Kafka is running: `docker-compose ps`
- Check consumer group: Events might have been consumed already
- Try using a new consumer group ID

### Want to start fresh?
```bash
# Stop everything
docker-compose down

# Remove volumes (clears all data)
docker-compose down -v

# Start again
docker-compose up -d
```

## Next Steps

1. **Run the basic flow**: Start analytics consumer, then producer
2. **Run tests**: Execute all three test scripts
3. **Check metrics**: Review the generated metrics files
4. **Experiment**: Modify event rates, add delays, test different scenarios


