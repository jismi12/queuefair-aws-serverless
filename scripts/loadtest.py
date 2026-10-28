"""Load test: sends N authenticated /submit requests, 20 at a time.

Usage: python loadtest.py https://YOUR-API-URL YOUR-LOGIN-TOKEN 1000
Get the token in the signed-in portal: F12 > Console > sessionStorage.getItem('qf_token')
Never commit or share a token.
"""
import json, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

URL = sys.argv[1].rstrip("/")
TOKEN = sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

def send(i):
    body = json.dumps({"type": "certificate", "notify": False}).encode()
    req = urllib.request.Request(URL + "/submit", data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + TOKEN})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503):
                return e.code
        except Exception:
            pass
        time.sleep(0.5 * (attempt + 1))
    return 0

start = time.time()
with ThreadPoolExecutor(max_workers=20) as pool:
    results = list(pool.map(send, range(N)))
print(f"{results.count(202)}/{N} accepted in {time.time() - start:.1f}s")
