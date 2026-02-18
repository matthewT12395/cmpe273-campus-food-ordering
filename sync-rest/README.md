# Sync REST Part (Part A)

This folder contains a minimal synchronous implementation of the campus food ordering workflow with three services:

- `order_service` (POST /order)
- `inventory_service` (POST /reserve) — supports delay and failure injection via query params `?delay=2` and `?fail=true`
- `notification_service` (POST /send)

Use `docker-compose up --build` inside this folder to run all services locally.
