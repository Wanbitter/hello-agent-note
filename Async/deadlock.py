import asyncio

sem = asyncio.Semaphore(1)          # 故意只给 1 个许可

async def inner() -> str:
    async with sem:                 # ← inner 也要许可
        print("inner 拿到了许可")
        await asyncio.sleep(0.1)
    return "inner 完成"

async def outer() -> None:
    async with sem:                 # ← outer 先把唯一的许可拿走了
        print("outer 拿到了许可，现在准备等 inner")
        try:
            result = await asyncio.wait_for(inner(), timeout=1)
            print(result)
        except TimeoutError:
            print("TLE!!!")
    result = await asyncio.gather(inner())
    print(result)






if __name__ == "__main__":
    asyncio.run(outer())
