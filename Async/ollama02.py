import asyncio
import httpx
import json
import time

async def main() -> None:
    payload = {
        "model": "deepseek-r1",
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        "stream": True,                    # ← 改回 True
    }

    pieces: list[str] = []                 # 边流边攒
    n = 0
    t0 = time.perf_counter()
    first_thinking_at = None
    first_content_at = None

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST", "http://127.0.0.1:11434/api/chat", json=payload
        ) as resp:
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)     # 每次只解析"一行"
                n += 1
                msg = chunk.get("message") or {}

                thinking = msg.get("thinking") or ""
                if thinking and first_thinking_at is None:
                    first_thinking_at = time.perf_counter() - t0

                piece = msg.get("content") or ""
                if piece:
                    if first_content_at is None:
                        first_content_at = time.perf_counter() - t0
                    pieces.append(piece)
                    print(piece, end="", flush=True)

                if chunk.get("done"):
                    print()
                    break

    print(f"数据块数量      : {n}")
    print(f"首个 thinking 到达: {first_thinking_at}")
    print(f"首个 content  到达: {first_content_at}")
    print(f"完整文本长度    : {len(''.join(pieces))}")


if __name__ == "__main__":
    # loop = asyncio.get_event_loop()
    asyncio.run(main())