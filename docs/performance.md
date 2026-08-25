# Performance Notes

Measured locally on a consumer laptop CPU (Windows 11, Python 3.14,
PyTorch CPU build). Numbers vary by hardware — treat them as indicative,
not guarantees.

## Model loading

- MobileNetV3-Small with ImageNet backbone downloads ~9.8 MB of pretrained
  weights on first use (cached afterwards).
- Building the model and loading a trained state_dict takes on the order of
  1–3 seconds, once per process at startup (not per request).

## Inference latency

Measured via the prediction service's built-in timing
(`PredictionResult.inference_ms`) on a single 224×224 input:

- Typical single-image inference: **~100–200 ms** on CPU
- The service records actual latency for every prediction and persists it
  (`inference_ms` column) — check your own deployment's numbers there or via
  the API response field `inference_time_ms`.

## Memory

- The model artifact (state_dict) is roughly 10 MB on disk.
- Resident memory for the app process is dominated by PyTorch runtime;
  expect several hundred MB. Render free tier (512 MB) is tight but workable
  with a single gunicorn worker (`--workers 1 --threads 4` as configured).

## Design decisions that affect performance

- Model loads **once at startup**, not per request.
- Inference runs under `torch.no_grad()` with `model.eval()`.
- Image quality checks use lightweight OpenCV operations before any tensor
  work, so bad images are rejected cheaply.
- Health endpoint performs no inference — safe for frequent probes.
- Gunicorn is configured with 1 worker / 4 threads: PyTorch inference holds
  the GIL-heavy path, so threads give concurrency for I/O while serialising
  model access safely.