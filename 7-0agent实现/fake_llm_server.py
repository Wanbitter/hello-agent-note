# -*- coding: utf-8 -*-
"""零成本的假 LLM 服务：模仿 OpenAI 兼容接口（/v1/chat/completions），支持流式与非流式。
用途：验证 openai SDK + hello_agents 这条链路能不能通，不花钱、不联网。
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PIECES = ["你好", "，我是", "假模型", "。"]
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except Exception:
            body = {}
        model = body.get("model", "fake-model")
        print(f"[fake-llm] path={self.path} model={model} stream={bool(body.get('stream'))} "
              f"messages={len(body.get('messages', []))}", flush=True)

        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            for piece in PIECES:
                chunk = {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0,
                         "model": model, "choices": [{"index": 0, "delta": {"content": piece},
                                                      "finish_reason": None}]}
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8"))
                self.wfile.flush()
            end = {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 0,
                   "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            self.wfile.write(f"data: {json.dumps(end, ensure_ascii=False)}\n\n".encode("utf-8"))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            payload = {"id": "chatcmpl-fake", "object": "chat.completion", "created": 0, "model": model,
                       "choices": [{"index": 0, "message": {"role": "assistant",
                                                            "content": "".join(PIECES)},
                                    "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"[fake-llm] listening on http://127.0.0.1:{PORT}/v1", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
