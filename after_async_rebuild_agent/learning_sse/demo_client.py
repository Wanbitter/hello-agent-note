"""看 demo_sse.py 的流。在 PyCharm 里跑这个（demo_sse.py 要开着）。"""

import json
import time

import httpx

URL = "http://127.0.0.1:8099/count"
t0 = time.time()

with httpx.stream("GET", URL, timeout=30) as r:
    print("HTTP", r.status_code, flush=True)

    for line in r.iter_lines():              # ★ 一行行读，边到边处理
        if not line.startswith("data: "):
            continue
        data = json.loads(line[6:])          # 去掉 "data: " 这 6 个字符
        print(f"[+{time.time() - t0:5.2f}s] {data}", flush=True)   # ★ 秒数会一路涨

print("结束", flush=True)