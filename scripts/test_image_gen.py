#!/usr/bin/env python3
"""Offline tests for image_gen.py using a local stub HTTP server."""

from __future__ import annotations

import base64
import contextlib
import io
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import image_gen  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


class StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append({"method": "GET", "path": self.path})
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.end_headers()
        self.wfile.write(JPEG)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.requests.append(
            {"method": "POST", "path": self.path, "headers": dict(self.headers), "body": body}
        )
        status, payload = self.server.responses.pop(0)
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def b64_items(count: int) -> dict:
    return {"data": [{"b64_json": base64.b64encode(PNG).decode()} for _ in range(count)]}


class ImageGenTest(unittest.TestCase):
    def setUp(self):
        self.server = HTTPServer(("127.0.0.1", 0), StubHandler)
        self.server.requests = []
        self.server.responses = []
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()
        self.tmp = Path(tempfile.mkdtemp())
        self.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"
        self.environ = {
            "IMAGE_GEN_PROVIDER": "openai",
            "IMAGE_GEN_BASE_URL": self.base_url,
            "IMAGE_GEN_API_KEY": "test-key",
            "IMAGE_GEN_MODEL": "test-model",
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def run_cli(self, *argv, environ=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = image_gen.main(
                list(argv),
                environ=self.environ if environ is None else environ,
            )
        return code, out.getvalue(), err.getvalue()

    def test_generate_sends_only_required_fields(self):
        self.server.responses.append((200, b64_items(1)))
        code, out, err = self.run_cli("--prompt", "a cat", "--output-dir", str(self.tmp))
        self.assertEqual(code, 0, err)
        req = self.server.requests[0]
        self.assertEqual(req["path"], "/v1/images/generations")
        self.assertEqual(req["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(json.loads(req["body"]), {"model": "test-model", "prompt": "a cat"})
        result = json.loads(out)
        self.assertEqual(result["mode"], "generate")
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(Path(result["files"][0]).read_bytes(), PNG)
        self.assertRegex(Path(result["files"][0]).name, r"^\d{8}-\d{6}\.png$")

    def test_generate_optional_fields_and_numbered_output(self):
        self.server.responses.append((200, b64_items(2)))
        target = self.tmp / "out" / "hero.png"
        code, out, err = self.run_cli(
            "--prompt", "hero", "--n", "2", "--size", "1536x1024", "--transparent", "--output", str(target)
        )
        self.assertEqual(code, 0, err)
        body = json.loads(self.server.requests[0]["body"])
        self.assertEqual(
            body,
            {"model": "test-model", "prompt": "hero", "n": 2, "size": "1536x1024", "background": "transparent"},
        )
        files = [Path(p).name for p in json.loads(out)["files"]]
        self.assertEqual(files, ["hero-1.png", "hero-2.png"])

    def test_existing_file_is_not_overwritten(self):
        target = self.tmp / "a.png"
        target.write_bytes(b"old")
        self.server.responses.append((200, b64_items(1)))
        code, out, _ = self.run_cli("--prompt", "x", "--output", str(target))
        self.assertEqual(code, 0)
        self.assertEqual(target.read_bytes(), b"old")
        self.assertEqual(Path(json.loads(out)["files"][0]).name, "a-2.png")

    def test_model_flag_overrides_env(self):
        self.server.responses.append((200, b64_items(1)))
        self.run_cli("--prompt", "x", "--model", "other", "--output-dir", str(self.tmp))
        self.assertEqual(json.loads(self.server.requests[0]["body"])["model"], "other")

    def test_edit_single_image_uses_image_field(self):
        img = self.tmp / "in.png"
        img.write_bytes(PNG)
        self.server.responses.append((200, b64_items(1)))
        code, out, err = self.run_cli("--prompt", "add hat", "--input-image", str(img), "--output-dir", str(self.tmp))
        self.assertEqual(code, 0, err)
        req = self.server.requests[0]
        self.assertEqual(req["path"], "/v1/images/edits")
        self.assertIn("multipart/form-data", req["headers"]["Content-Type"])
        self.assertIn(b'name="image"; filename="in.png"', req["body"])
        self.assertIn(b'name="model"\r\n\r\ntest-model', req["body"])
        self.assertNotIn(b'name="n"', req["body"])
        self.assertNotIn(b'name="size"', req["body"])
        self.assertNotIn(b'name="background"', req["body"])
        self.assertEqual(json.loads(out)["mode"], "edit")

    def test_edit_multiple_images_uses_array_field(self):
        paths = []
        for name in ("a.png", "b.jpg"):
            path = self.tmp / name
            path.write_bytes(PNG)
            paths += ["--input_image", str(path)]
        self.server.responses.append((200, b64_items(1)))
        code, _, err = self.run_cli("--prompt", "combine", *paths, "--n", "1", "--output_dir", str(self.tmp))
        self.assertEqual(code, 0, err)
        body = self.server.requests[0]["body"]
        self.assertEqual(body.count(b'name="image[]"'), 2)
        self.assertIn(b"Content-Type: image/jpeg", body)
        self.assertIn(b'name="n"\r\n\r\n1', body)

    def test_url_response_is_downloaded_with_detected_extension(self):
        self.server.responses.append((200, {"data": [{"url": f"{self.base_url}/files/1", "revised_prompt": "rp"}]}))
        code, out, err = self.run_cli("--prompt", "x", "--output", str(self.tmp / "pic.png"))
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(Path(result["files"][0]).name, "pic.jpg")
        self.assertEqual(result["revised_prompts"], ["rp"])

    def test_api_error_message_is_surfaced(self):
        self.server.responses.append((400, {"error": {"message": "background not supported"}}))
        code, _, err = self.run_cli("--prompt", "x", "--transparent", "--output-dir", str(self.tmp))
        self.assertEqual(code, 1)
        self.assertIn("HTTP 400", err)
        self.assertIn("background not supported", err)

    def test_size_aspect_ratio_bounds(self):
        self.assertEqual(image_gen.parse_size("3072x1024"), "3072x1024")
        self.assertEqual(image_gen.parse_size("1024x3072"), "1024x3072")
        self.assertEqual(image_gen.parse_size("1000X700"), "1000x700")
        for bad in ("4096x1024", "1024x4096", "auto", "1024", "0x10"):
            with self.assertRaises(image_gen.UsageError, msg=bad):
                image_gen.parse_size(bad)
        code, _, err = self.run_cli("--prompt", "x", "--size", "4000x1000")
        self.assertEqual(code, 1)
        self.assertIn("1:3 and 3:1", err)
        self.assertEqual(self.server.requests, [])

    def test_invalid_n_and_missing_input(self):
        self.assertEqual(self.run_cli("--prompt", "x", "--n", "0")[0], 1)
        code, _, err = self.run_cli("--prompt", "x", "--input-image", str(self.tmp / "nope.png"))
        self.assertEqual(code, 1)
        self.assertIn("not found", err)

    def test_settings_come_only_from_environment(self):
        self.server.responses.append((200, b64_items(1)))
        code, _, err = self.run_cli("--prompt", "x", "--output-dir", str(self.tmp))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.server.requests[0]["headers"]["Authorization"], "Bearer test-key")

    def test_env_file_next_to_skill_is_ignored(self):
        env_file = Path(image_gen.SCRIPT_DIR).parent / ".env"
        if not env_file.is_file():
            self.skipTest("no .env beside the skill to prove it is ignored")
        code, _, err = self.run_cli("--prompt", "x", environ={"PATH": "/usr/bin"})
        self.assertEqual(code, 1)
        self.assertIn("missing environment variables", err)
        self.assertEqual(self.server.requests, [])

    def test_missing_config_is_reported(self):
        code, _, err = self.run_cli("--prompt", "x", environ={})
        self.assertEqual(code, 1)
        for name in ("IMAGE_GEN_BASE_URL", "IMAGE_GEN_API_KEY", "IMAGE_GEN_MODEL"):
            self.assertIn(name, err)

    def test_unknown_provider(self):
        code, _, err = self.run_cli("--prompt", "x", environ={**self.environ, "IMAGE_GEN_PROVIDER": "nope"})
        self.assertEqual(code, 1)
        self.assertIn("unknown provider", err)


if __name__ == "__main__":
    unittest.main()
