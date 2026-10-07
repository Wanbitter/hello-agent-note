import asyncio

def normal(x: int) -> int:
    print("  >>> normal 在执行")
    return x * 2

async def coro(x: int) -> int:
    print("  >>> coro 在执行")
    return x * 2

print("=== 普通 def ===")
r1 = normal(5)
print("返回值:", r1, "| 类型:", type(r1))

print("=== async def ===")
r2 = coro(5)
print("返回值:", r2, "| 类型:", type(r2))
print("能直接当数字用吗:", r2 + 1)        # ← 注意这一行


print("=== 用 run 拿协程的结果 ===")
r3 = asyncio.run(coro(5))
print("返回值:", r3, "| 类型:", type(r3))


