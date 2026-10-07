import httpx
if __name__ == "__main__":
    r = httpx.post(
        "http://127.0.0.1:8001/chat",          # ★ 端口
        json={"text": "介绍一下自己"},          # ★ 直接给一个字典
        timeout=60,                            # ★ 一定要设
    )
    print(r.status_code)
    print(r.json()["reply"])