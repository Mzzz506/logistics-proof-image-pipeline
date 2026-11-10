import base64
import os

from src.logistics_service import InfraiClient, receive_proof


def main() -> None:
    if "INFRAI_API_KEY" not in os.environ:
        raise SystemExit("Set INFRAI_API_KEY before running the upload demo")
    image = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a7l8AAAAASUVORK5CYII="
    )
    event = receive_proof(
        InfraiClient(), "SHP-1042", image, content_type="image/png",
        bucket=os.environ.get("INFRAI_DEMO_BUCKET", "logistics-proof"),
    )
    print({"shipment_id": event.shipment_id, "decision": event.kind, "stored": event.object_key})


if __name__ == "__main__":
    main()

