import requests
import time

BASE = "http://localhost:5000"


def test_happy_path():
    resp = requests.post(f"{BASE}/order", json={"items": ["pizza"]})
    print("happy", resp.status_code, resp.json())


def test_inventory_delay():
    start = time.time()
    resp = requests.post(f"{BASE}/order", json={"items": ["sushi"], "delay": 2})
    elapsed = time.time() - start
    print("delay", elapsed, resp.status_code, resp.json())


def test_inventory_fail():
    resp = requests.post(f"{BASE}/order", json={"items": ["salad"], "fail": True})
    print("fail", resp.status_code, resp.json())


if __name__ == "__main__":
    print("Running tests against running docker-compose services on localhost:5000")
    test_happy_path()
    test_inventory_delay()
    test_inventory_fail()
