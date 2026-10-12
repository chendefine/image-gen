"""OpenAI Images API: POST /images/generations and /images/edits."""

from __future__ import annotations

import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid

from .base import GeneratedImage, ImageRequest, Provider, ProviderError

RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}
USER_AGENT = "image-gen-skill/1.0"


class OpenAIProvider(Provider):
    name = "openai"

    def generate(self, request: ImageRequest) -> list[GeneratedImage]:
        body = json.dumps(self._fields(request)).encode()
        payload = self._post("/images/generations", body, "application/json")
        return self._parse(payload)

    def edit(self, request: ImageRequest) -> list[GeneratedImage]:
        field = "image" if len(request.images) == 1 else "image[]"
        files = [(field, path.name, path.read_bytes()) for path in request.images]
        body, content_type = _multipart(self._fields(request), files)
        payload = self._post("/images/edits", body, content_type)
        return self._parse(payload)

    def _fields(self, request: ImageRequest) -> dict:
        # Only send what the caller set; the server applies its own defaults otherwise.
        fields: dict = {"model": request.model, "prompt": request.prompt}
        if request.n is not None:
            fields["n"] = request.n
        if request.size is not None:
            fields["size"] = request.size
        if request.transparent:
            fields["background"] = "transparent"
        return fields

    def _post(self, path: str, body: bytes, content_type: str) -> dict:
        url = self.config.base_url.rstrip("/") + path
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": content_type,
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        attempt = 0
        while True:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as err:
                detail = _error_message(err.read())
                if err.code in RETRY_STATUS and attempt < self.config.max_retries:
                    attempt += 1
                    time.sleep(2**attempt)
                    continue
                raise ProviderError(f"HTTP {err.code} from {path}: {detail}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
                if attempt < self.config.max_retries:
                    attempt += 1
                    time.sleep(2**attempt)
                    continue
                reason = getattr(err, "reason", err)
                raise ProviderError(f"request to {url} failed: {reason}") from None
            except json.JSONDecodeError:
                raise ProviderError(f"non-JSON response from {path}") from None

    def _parse(self, payload: dict) -> list[GeneratedImage]:
        items = payload.get("data") or []
        if not items:
            raise ProviderError(f"response contains no images: {json.dumps(payload)[:500]}")
        images = []
        for item in items:
            if item.get("b64_json"):
                data = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                data = self._download(item["url"])
            else:
                raise ProviderError("image entry has neither b64_json nor url")
            images.append(GeneratedImage(data=data, revised_prompt=item.get("revised_prompt")))
        return images

    def _download(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as err:
            raise ProviderError(f"failed to download image from {url}: {err}") from None


def _multipart(fields: dict, files: list[tuple[str, str, bytes]]) -> tuple[bytes, str]:
    boundary = f"----image-gen-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for name, filename, data in files:
        filename = filename.replace('"', "_")
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        )
        parts.append(header.encode() + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _error_message(raw: bytes) -> str:
    text = raw.decode("utf-8", "replace").strip()
    try:
        err = json.loads(text).get("error")
    except (json.JSONDecodeError, AttributeError):
        return text[:1000] or "(empty body)"
    if isinstance(err, dict) and err.get("message"):
        return err["message"]
    if isinstance(err, str):
        return err
    return text[:1000]
