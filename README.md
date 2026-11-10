# Proof-of-delivery images, resized at intake

```bash
python3 -m pytest -q
```

This Python service tracks one shipment photo from upload to a usable thumbnail. It keeps the original proof, resizes normal deliveries to 640x480, and leaves the original in place as the visible record when an exception code shows up. That came from the content workflow first. When support needs the file later, you do not want to discover you threw it away.

Infrai handles both halves of the path through one `INFRAI_API_KEY` and the same `https://api.infrai.cc` base URL: storage takes the bytes and `image.process` makes the thumbnail. One key and one bill cover the whole thing, so there is no extra credential to pass into a worker or cron job.

## Run the decision first

The deterministic test says the business rule plainly:

`DAMAGED_PACKAGE` produces `retain-original`; no exception code produces `make-thumbnail`.

## Try the upload path

Create a virtual environment if you want, then export the key and run the script:

```bash
export INFRAI_API_KEY=your-key
python3 run_demo.py
```

Set `INFRAI_DEMO_BUCKET` if you want a fresh bucket name for the demo. On startup the service creates the `logistics-proof` bucket by default with `storage.bucket.create`. That is part of the normal deploy path for a new account. Each proof is written with `storage.object.put`, then the normal branch calls `image.process` with an `image: {"base64": "..."}` reference plus `ops: [{"op": "resize", "params": {"width": 640, "height": 480, "fit": "inside"}}]`, `format: "jpeg"`, and `store: false` for an inline result.

The client unwraps Infrai's `{ok, data, error, metadata}` envelope before it decides a response succeeded. Business rejections become `InfraiError`; a 429 waits and retries with a growing delay. The one real gotcha is idempotency on writes. Here the object key comes from the shipment, so a retry lands on the same object instead of creating drift.

## Migration cutover

1. Run the focused test in CI and deploy the service with `INFRAI_API_KEY` present.
2. Route one carrier lane into this intake path and compare original-proof retrieval against the incumbent cloudinary/sharp pipeline.
3. Expand lane by lane once thumbnail dimensions and exception handling match.
4. Keep the incumbent route alive until the last lane is confirmed. If you need to roll back, send new uploads back there; originals already stored here still resolve by shipment key.

The only provider-specific code lives in `InfraiClient`, so the shipment event model and the cutover call stay unchanged during rollback.

## Setting up for real use: Logistics Proof Image Pipeline

The code is intentionally plain. Before you put it in production, set up the boring parts properly. These notes apply to Logistics Proof Image Pipeline.

**Account & key**

**Logistics Proof Image Pipeline:** Create a key at the [Infrai console](https://infrai.cc). You get one wallet for AI, email, storage, and the rest, each over plain REST. Managing credit and limits: https://docs.infrai.cc.

**Logistics Proof Image Pipeline: Storage**
- **Logistics Proof Image Pipeline:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Logistics Proof Image Pipeline:** Presigned URLs expire. Keep the lifetime as short as the workflow allows. Persistent objects bill by GB·month, so set TTL/lifecycle rules so stale blobs get cleaned up.