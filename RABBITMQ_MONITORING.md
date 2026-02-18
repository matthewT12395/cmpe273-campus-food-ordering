# RABBITMQ MONITORING GUIDE FOR SCREENSHOTS

## Quick Access

### 1. Open RabbitMQ Management UI
```
URL: http://localhost:15672/
Username: guest
Password: guest
```

### 2. What to Look For

#### Queue: `orders.created`
- **Location:** Queues and Streams tab
- **Shows:** Orders waiting to be processed
- **Look for:** Messages_ready count increases/decreases
- **Screenshot:** Capture when queue has messages in it

#### Exchange: `orders` 
- **Type:** Topic exchange
- **Routing Key:** order.placed
- **Shows:** Message routing configuration

#### Queue: `notifications.pending`
- **Shows:** Notifications being sent
- **After InventoryReserved:** Should have notifications

#### Queue: `dlq.inventory`
- **Shows:** Dead Letter Queue
- **Contains:** Malformed messages during TEST 4

---

## What Happens During Each Test

### TEST 2: Idempotency (Running Now ~5 min total)
**During this test:**
1. Order created → Message sent to `orders.created`
2. Watch messages_ready count in queue
3. Duplicate message published
4. Watch if message count increases (it might not if processed)

**Screenshot to capture:**
- Queue depth showing messages
- Then shows messages being consumed

### TEST 3: Backlog & Recovery (After TEST 2)
**During this test:**
1. Service will be killed at 13:21:20
2. Orders published while service is down
3. Messages accumulate in `orders.created` queue
4. **CAPTURE THIS:** Queue showing high message count
5. Service restarts at 13:22:24
6. **CAPTURE THIS:** Queue draining back to 0

### TEST 4: DLQ (Last test ~5 min)
**During this test:**
1. Malformed message published
2. Check `dlq.inventory` queue
3. **CAPTURE:** Message in DLQ queue

---

## Tab Navigation in RabbitMQ UI

### Queues and Streams Tab
1. Click "Queues and Streams" at top
2. See all queues listed
3. Each shows:
   - Queue name
   - messages_ready (waiting)
   - messages_unacked (being processed)
   - messages (total)
4. Click queue name to see message details

### Messages Tab (in queue details)
1. Click on queue name (e.g., orders.created)
2. Scroll down to "Messages"
3. Shows actual message payload
4. Can inspect JSON content

---

## Commands to Monitor from Terminal (Alt Method)

```bash
# List all queues and message counts
docker exec async-rabbitmq-rabbitmq-1 rabbitmqctl list_queues

# Watch continuously
watch 'docker exec async-rabbitmq-rabbitmq-1 rabbitmqctl list_queues'

# Inspect specific queue
docker exec async-rabbitmq-rabbitmq-1 rabbitmqctl list_queue_length orders.created
```

---

## Best Screenshots to Take

### 1. Normal Operation
- Queues tab showing all queues
- `orders.created` queue with some messages
- Show message count > 0

### 2. DLQ with Malformed Message
- `dlq.inventory` queue visible
- Click on queue to expand
- Show the malformed message in details

### 3. Queue Drained
- After recovery from backlog test
- Show `orders.created` back to 0 messages

### 4. Message Details
- Click on any queue
- Scroll to "Messages" section
- Show actual OrderPlaced JSON

---

## Quick Reference

```
Queue Name              | Purpose                | Test
─────────────────────────────────────────────────────────
orders.created         | Orders to process      | All
notifications.pending  | Notifications sent     | TEST 2
dlq.inventory          | Dead Letter Queue      | TEST 4
```

---

## During Backlog Test (TEST 3)

**Timeline:**
- T+0:   Service kill
- T+1-2: Orders published (messages accumulate)
- T+60:  Service restart
- T+65:  Queue drain complete

**What to capture:**
1. At T+30: Show queue with ~5 messages waiting
2. At T+65: Show queue back to 0

---

## Pro Tips

- Keep RabbitMQ tab open during entire test
- Refresh every 10 seconds during backlog test
- Use browser zoom if text is small
- Tab shows real-time updates

---

## Failed? Here's What to Check

If you don't see messages:
1. Verify RabbitMQ is running: `docker-compose ps`
2. Check it shows "healthy"
3. Try refreshing http://localhost:15672/
4. Check credentials: guest/guest

---

**When test is running, go to http://localhost:15672 and watch the queues!**
