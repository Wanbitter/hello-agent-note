import json
import httpx


def main():
    url = "http://127.0.0.1:8002/chat/stream"
    body = {"session_id": "u1", "text": "北京天气如何"}      # ← 想换问题改这里

    with httpx.stream("POST", url, json=body, timeout=60) as r:
        print("HTTP", r.status_code)

        for line in r.iter_lines():                 # ★ 一行行读，边到边处理
            if not line.startswith("data: "):       # 空行 / 其他行跳过
                continue

            event = json.loads(line[6:])            # ★ 去掉 "data: " 这 6 个字符 → 中文在这里还原

            kind = event.get("type")
            if kind == "tool_call":
                print(f"[正在调用工具] {event['name']}  参数={event['args']}")
            elif kind == "tool_result":
                print(f"[工具返回] {event['text']}")
            elif kind == "final":
                print(f"\n【最终回答】\n{event['text']}")
                break                               # 拿到最终答案就收工
            else:
                print(event)


if __name__ == "__main__":
    main()