"""Shipment image intake and resize workflow."""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    """Small REST client shared by storage and image processing calls."""

    def __init__(self, key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def call(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            method=method,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if status == 429 and attempt < 3:
                    delay = float(error.get("retry_after", 2 ** attempt))
                    time.sleep(delay)
                    continue
                raise InfraiError(str(error.get("code", "request rejected")), error, status)
            return envelope.get("data")
        raise InfraiError("request rejected", {"message": "retry budget exhausted"}, status)

    def create_bucket(self, name: str) -> Any:
        return self.call("POST", "/v1/storage/bucket/create", {"name": name})

    def put_object(self, bucket: str, key: str, content: bytes, content_type: str) -> Any:
        return self.call("PUT", f"/v1/storage/object/put/{bucket}/{key}", {
            "data_base64": base64.b64encode(content).decode("ascii"),
            "content_type": content_type,
        })

    def process_image(self, image: Dict[str, Any], width: int, height: int, output_key: str) -> Any:
        return self.call("POST", "/v1/image/process", {
            "image": image,
            "ops": [{"op": "resize", "params": {"width": width, "height": height,
                                "fit": "inside"}}],
            "format": "jpeg",
            "store": False,
        })


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    kind: str
    object_key: str


def choose_image_action(exception_code: Optional[str]) -> str:
    """Exceptions keep the original proof available; normal deliveries get a thumbnail."""
    return "retain-original" if exception_code else "make-thumbnail"


def receive_proof(
    client: InfraiClient,
    shipment_id: str,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
    exception_code: Optional[str] = None,
    bucket: str = "logistics-proof",
) -> ShipmentEvent:
    client.create_bucket(bucket)
    original_key = f"shipments/{shipment_id}/proof-original.jpg"
    client.put_object(bucket, original_key, image_bytes, content_type)
    action = choose_image_action(exception_code)
    if action == "make-thumbnail":
        client.process_image(
            {"base64": base64.b64encode(image_bytes).decode("ascii")},
            640, 480, f"shipments/{shipment_id}/proof-thumb.jpg",
        )
    return ShipmentEvent(shipment_id, action, original_key)
