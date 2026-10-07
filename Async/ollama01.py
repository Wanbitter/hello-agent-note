import asyncio
import httpx
import json

async def main() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get("http://127.0.0.1:11434/api/tags")
        print("HTTP 状态码:", resp.status_code)
        resp.raise_for_status()
        data = resp.json()

    print("顶层键:", list(data.keys()))

    for model in data[list(data.keys())[0]]:
        print(" -", model["name"], "|", model["details"]["parameter_size"])
    # print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())