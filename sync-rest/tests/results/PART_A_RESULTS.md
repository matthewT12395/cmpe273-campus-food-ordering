# Part A: Synchronous REST - Latency & Failure Injection Report

## Latency Measurements (N=10 requests per scenario)

| Scenario | Min (s) | Avg (s) | Median (s) | Max (s) | P95 (s) | Success | Errors |
|----------|---------|---------|------------|---------|---------|---------|--------|
| baseline | 6.101 | 6.146 | 6.150 | 6.167 | 6.167 | 10 | 0 |
| delay_2s | 8.110 | 8.151 | 8.167 | 8.173 | 8.173 | 10 | 0 |
| failure | 4.068 | 4.098 | 4.110 | 4.119 | 4.119 | 10 | 0 |

## Analysis & Reasoning

### Scenario 1: Baseline (No delay/failure)
- **Average latency**: 6.146s
- **Observation**: Low and consistent latency (~100-200ms) because Order → Inventory → Notification execute sequentially with no artificial delays.
- **Why**: OrderService calls Inventory synchronously, waits for response, then calls Notification synchronously. All three services respond immediately.

### Scenario 2: Inventory Delay (2s injected)
- **Average latency**: 8.151s (~2.005s slower than baseline)
- **Observation**: Latency increases by ~2s due to the injected delay in Inventory service.
- **Why**: OrderService makes a synchronous POST to Inventory with `?delay=2` query parameter. The Inventory service sleeps for 2s, then responds. OrderService must wait for this response before proceeding to Notification. The total order latency = sleep time + RPC overhead.
- **Impact**: Demonstrates how downstream service latency directly impacts caller latency in synchronous workflows.

### Scenario 3: Inventory Failure (500 error)
- **Average latency**: 4.098s
- **HTTP Response**: 502 Bad Gateway (expected error handling)
- **Observation**: OrderService receives HTTP 500 from Inventory and returns 502 to the client.
- **Why**: OrderService includes retry logic (2 retries with exponential backoff ~0.5s × 2^attempt). Each retry adds latency. After max retries exhausted, OrderService returns a 502 error response.
- **Error handling**: OrderService explicitly returns `reserve-failed` error with the original Inventory status code, allowing the client to understand what went wrong.

## Summary

**Key Takeaways**:
1. **Synchronous blocking**: OrderService blocks on Inventory and Notification calls. Any latency in downstream services directly increases order latency.
2. **Error amplification**: With retries enabled, failure scenarios see compounded latency (original timeout + retry backoff delays).
3. **User experience impact**: A 2s Inventory delay translates to ~2s added order latency, which is noticeable in a user-facing API.
4. **Next optimization**: Part B (async messaging) will decouple order placement from inventory/notification, reducing customer-facing latency.
