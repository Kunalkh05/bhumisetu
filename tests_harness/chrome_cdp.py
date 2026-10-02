"""Lightweight, resilient Chrome DevTools Protocol (CDP) driver for Python.
Uses Google Chrome in headless mode without third-party heavy dependencies.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

logger = logging.getLogger("chrome_cdp")


class ChromeCDPDriver:
    def __init__(
        self,
        port: int = 9222,
        user_data_dir: str = "/tmp/chrome_validation_profile",
        chrome_path: str = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ) -> None:
        self.port = port
        self.user_data_dir = user_data_dir
        self.chrome_path = chrome_path
        self.process: subprocess.Popen | None = None
        self.ws: Any = None
        self.msg_id = 0
        self.target_id: str | None = None

    def start(self) -> None:
        """Start headless Chrome process."""
        if os.path.exists(self.user_data_dir):
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        os.makedirs(self.user_data_dir, exist_ok=True)

        cmd = [
            self.chrome_path,
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1440,900",
            "--enable-automation",
            "--allow-running-insecure-content",
        ]
        self.process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Wait for port to be ready
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version") as resp:
                    if resp.status == 200:
                        break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError(f"Chrome failed to start on port {self.port}")

    def stop(self) -> None:
        """Stop Chrome and clean up."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            self.process = None
        if os.path.exists(self.user_data_dir):
            shutil.rmtree(self.user_data_dir, ignore_errors=True)

    async def connect(self) -> None:
        """Connect WebSocket to a new or existing tab."""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/new", method="PUT")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            ws_url = data["webSocketDebuggerUrl"]
            self.target_id = data["id"]

        self.ws = await websockets.connect(ws_url, max_size=20 * 1024 * 1024)
        await self.send("Page.enable")
        await self.send("Runtime.enable")
        await self.send("DOM.enable")

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send(self, method: str, params: dict | None = None) -> dict:
        """Send CDP command and await response."""
        self.msg_id += 1
        call_id = self.msg_id
        payload = {"id": call_id, "method": method, "params": params or {}}
        await self.ws.send(json.dumps(payload))

        while True:
            raw = await self.ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == call_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP error in {method}: {resp['error']}")
                return resp.get("result", {})

    async def navigate(self, url: str, wait_network_idle: float = 1.0) -> None:
        """Navigate to URL and wait."""
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(wait_network_idle)

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression and return Python object."""
        result = await self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        res_val = result.get("result", {})
        if "value" in res_val:
            return res_val["value"]
        if res_val.get("type") == "undefined":
            return None
        return res_val

    async def wait_for_function(
        self, js_condition: str, timeout: float = 10.0, interval: float = 0.2
    ) -> Any:
        """Poll until js_condition returns truthy or timeout expires."""
        start = time.time()
        while time.time() - start < timeout:
            val = await self.evaluate(js_condition)
            if val:
                return val
            await asyncio.sleep(interval)
        raise TimeoutError(f"Condition not met within {timeout}s: {js_condition}")

    async def click(self, selector: str) -> None:
        """Click element matching CSS selector."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) throw new Error('Element not found: ' + {json.dumps(selector)});
            el.scrollIntoView({{ behavior: 'instant', block: 'center' }});
            el.click();
            return true;
        }})()
        """
        await self.evaluate(js)

    async def fill(self, selector: str, text_value: str) -> None:
        """Set value of input field and dispatch input/change events."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) throw new Error('Input not found: ' + {json.dumps(selector)});
            el.focus();
            el.value = {json.dumps(text_value)};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return true;
        }})()
        """
        await self.evaluate(js)

    async def get_text(self, selector: str) -> str:
        """Get innerText of selector."""
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            return el ? el.innerText : '';
        }})()
        """
        return await self.evaluate(js) or ""

    async def screenshot(self, filepath: str) -> None:
        """Capture screenshot to PNG file."""
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(res["data"])
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(img_bytes)

    async def set_viewport(self, width: int, height: int, is_mobile: bool = False) -> None:
        """Set browser viewport dimensions."""
        await self.send(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": is_mobile,
            },
        )
