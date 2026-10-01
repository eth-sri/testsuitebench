#!/usr/bin/env python3
"""Run Muse Code through the local OpenRouter protocol adapter."""

from __future__ import annotations

import argparse
import http.client
import os
import ssl
import subprocess
import threading
from urllib.parse import urlsplit

from muse_code_openrouter.proxy import MuseOpenRouterHandler, MuseOpenRouterServer


class ProxiedHandler(MuseOpenRouterHandler):
    """Route the adapter's upstream requests through ProgramBench's Squid proxy."""

    def _connection(self) -> tuple[http.client.HTTPConnection, str]:
        target = urlsplit(self.adapter.upstream)
        if target.scheme != "https" or target.hostname != "openrouter.ai":
            raise ValueError("Muse upstream must be https://openrouter.ai")
        proxy_url = urlsplit(os.environ.get("HTTPS_PROXY", ""))
        if proxy_url.scheme != "http" or not proxy_url.hostname:
            raise ValueError("Muse OpenRouter adapter needs the ProgramBench HTTPS_PROXY")
        connection = http.client.HTTPSConnection(
            proxy_url.hostname, proxy_url.port or 80, context=ssl.create_default_context(), timeout=600
        )
        connection.set_tunnel(target.hostname, target.port or 443)
        return connection, target.path.rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("prompt")
    args = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        parser.error("OPENROUTER_API_KEY is required")
    if not args.model.startswith("meta/muse"):
        parser.error("Muse Code OpenRouter adapter requires a meta/muse* model ID")

    server = MuseOpenRouterServer(("127.0.0.1", 0), api_key=key, model=args.model)
    server.RequestHandlerClass = ProxiedHandler
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    muse_env = os.environ.copy()
    muse_env["META_API_KEY"] = "local-adapter"
    command = [
        "muse", "exec", "--json", "--yolo", "--disable-web-tools",
        "--base-url", f"http://127.0.0.1:{server.server_port}",
        "--model", args.model, "--reasoning-effort", args.reasoning_effort, args.prompt,
    ]
    try:
        return subprocess.call(command, env=muse_env)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
