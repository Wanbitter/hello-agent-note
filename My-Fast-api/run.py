import time
import httpx

N = 753
client = httpx.Client(timeout=5)          # ★ 复用连接，别每次新建

t0 = time.time()
for i in range(N):
    r = client.post("http://127.0.0.1:8000/ask", json={"question": "你好"})

dt = time.time() - t0
print(f"{N} 次请求，共 {dt:.2f} 秒")
print(f"平均 {dt / N * 1000:.1f} 毫秒/次")
print(f"吞吐量约 {N / dt:.0f} 次/秒")