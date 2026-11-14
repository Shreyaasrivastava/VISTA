import json, sys, time, urllib.request, urllib.error

key = sys.argv[1]
url = "http://127.0.0.1:8000/density-events"
# Platform 1 = 140 m2: Warning ~114 log se upar, Critical ~137 se upar
counts = [40] * 3 + [125] * 8 + [145] * 8 + [40] * 15

for n in counts:
    req = urllib.request.Request(
        url, data=json.dumps({"people_count": n}).encode(),
        headers={"Content-Type": "application/json", "X-Camera-Key": key}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            print(n, r.status)
    except urllib.error.HTTPError as e:
        print(n, e.code, e.read().decode())
        break
    time.sleep(1)
