"""Fake OpenAI-compatible server to test the LLM judge plumbing offline."""
import json, re
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        user = body["messages"][-1]["content"]
        ids = re.findall(r"id=(C\d+)", user)
        quotes = re.findall(r'\): "(.*?)"', user)
        res = []
        for n, i in enumerate(ids):
            res.append({"id": i, "hook": 7, "cliff": 6 + n % 3, "standalone": 5, "verdict": "keep",
                        "hook_line": quotes[0] if quotes and n % 2 == 0 else "A totally invented line",
                        "cliff_line": quotes[-1] if quotes else "", "why": "mock"})
        out = {"choices": [{"message": {"content": json.dumps({"results": res})}}],
               "usage": {"prompt_tokens": len(user) // 4, "completion_tokens": 80 * len(ids)}}
        b = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass

HTTPServer(("127.0.0.1", 8765), H).serve_forever()
