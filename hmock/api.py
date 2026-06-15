"""Small HTTP API surface for HMock utilities."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .brokers import MockValidationError
from .evaluation import evaluate_mock_definition


def handle_evaluate_http_request(
    method: str,
    path: str,
    body: bytes,
    *,
    base_dir: str | Path = ".",
) -> tuple[int, dict[str, str], bytes]:
    if path != "/api/v1/evaluate":
        return json_response(404, {"error": "not found"})
    if method.upper() != "POST":
        return json_response(405, {"error": "method not allowed"})
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json_response(400, {"errors": [{"field": "body", "message": "Invalid JSON", "type": "invalid"}]})
    if not isinstance(document, dict):
        return json_response(400, {"errors": [{"field": "body", "message": "Request body must be an object", "type": "invalid"}]})
    try:
        result = evaluate_mock_definition(
            document.get("mock"),
            document.get("context"),
            base_dir=base_dir,
        )
    except MockValidationError as exc:
        return json_response(400, {"errors": exc.errors})
    return json_response(200, result)


def json_response(status: int, payload: dict[str, Any]) -> tuple[int, dict[str, str], bytes]:
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return (
        status,
        {
            "Content-Type": "application/json",
            "Content-Length": str(len(raw)),
        },
        raw,
    )


class EvaluationRequestHandler(BaseHTTPRequestHandler):
    base_dir: Path = Path(".")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        status, headers, body = handle_evaluate_http_request(
            "POST",
            self.path,
            self.rfile.read(length),
            base_dir=self.base_dir,
        )
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_evaluation_server(
    host: str = "127.0.0.1",
    port: int = 0,
    *,
    base_dir: str | Path = ".",
) -> ThreadingHTTPServer:
    class Handler(EvaluationRequestHandler):
        pass

    Handler.base_dir = Path(base_dir)
    return ThreadingHTTPServer((host, port), Handler)
