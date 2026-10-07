import asyncio
import time

# async def fetch(name: str, seconds: float, should_fail: bool = False) -> str:
#     print(f"{name} start")
#     await asyncio.sleep(seconds) #表示等待时间
#     if should_fail:
#         raise RuntimeError(f"{name} 炸了！")
#     print(f"{name} end")
#     return name
#
#
# async def main() -> None:
#     t = time.perf_counter()
#     # await fetch("A",1)
#     # await fetch("B",3,True)
#     # await fetch("C",1)
#     # await fetch("D", 4)
#     # print(f"总耗时{time.perf_counter() - t:.1f}秒")
#
#     ans = await asyncio.gather(
#         fetch("A", 1),
#         fetch("B", 1, should_fail=True),  # 1 秒后炸
#         fetch("C", 6),
#         fetch("D", 4),
#         return_exceptions=True,
#     )
#     print(ans)


# =============================================================================
# 以上为普通asyncio 和await的调用 写了async表示可以作为异步处理的函数，await就是纯等待
# await asyncio.sleep(seconds)是等待函数
# 在函数调用前面加上 await asyncio就表示输入输出异步处理，
# 用await asyncio.gather()表示同步启动，根据运行时长的不同以此打印结果
# 但是任务还在，会一一对位
# time.perf_counter()是计时函数,调用以此表示按下开始，再次调用就是按下暂停
# 接下来学并发限制
# =============================================================================


sem = asyncio.Semaphore(3)

async def job(name: str, seconds: float) -> str:
    async with sem:
        print(f"{time.perf_counter():6.2f}s  {name} start")
        await asyncio.sleep(seconds)
        print(f"{time.perf_counter():6.2f}s  {name} end")
    return name

async def main() -> None:
    t = time.perf_counter()
    ans = await asyncio.gather(
        job("任务1", 9),
        job("任务2", 8),
        job("任务3", 7),
        job("任务5", 5),
        job("任务6", 4),
        job("任务4", 6),
        job("任务7", 3),
        job("任务8", 2),
        job("任务9", 1),
    )
    print(f"总耗时 {time.perf_counter() - t:.2f} 秒")
    print(ans)




if __name__ == "__main__":
    asyncio.run(main())