
import asyncio
import time


async def work(name: str, seconds: float) -> str:
    print(f"{name} 开始")
    await asyncio.sleep(seconds)
    print(f"{name} 结束")
    return name



async def main() -> None:
    t = time.perf_counter()

    taskA = asyncio.create_task(work("A", 1))
    print(f"[{time.perf_counter()-t:.2f}s] A 已启动")

    await asyncio.sleep(0.5)                      # ← A 在后台跑，我干别的
    print(f"[{time.perf_counter()-t:.2f}s] 过了 0.5 秒，现在再补一个 B")

    taskB = asyncio.create_task(work("B", 1))     # ← A 还在跑，动态加一个新任务
    print(f"[{time.perf_counter()-t:.2f}s] B 已启动")

    await taskA
    print(f"[{time.perf_counter()-t:.2f}s] A 完成")
    await taskB
    print(f"[{time.perf_counter()-t:.2f}s] B 完成")

asyncio.run(main())