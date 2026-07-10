"""S88: Load test script — 10 równoległych requestów do /health."""
import threading
import time
import urllib.request
import sys

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/api/v1/health"
results: list = []


def req():
    try:
        start = time.time()
        urllib.request.urlopen(URL, timeout=5)
        results.append(("ok", round(time.time() - start, 3)))
    except Exception as e:
        results.append(("err", str(e)))


threads = [threading.Thread(target=req) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

ok = sum(1 for r in results if r[0] == "ok")
avg = sum(r[1] for r in results if r[0] == "ok") / max(ok, 1)
print(f"{ok}/10 OK, avg={avg:.3f}s")
if ok < 8:
    print("WARN: <80% success rate")
    sys.exit(1)
