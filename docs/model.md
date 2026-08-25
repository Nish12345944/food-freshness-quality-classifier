# Model Documentation

## Architecture

| Property | Value |
|---|---|
| Architecture | MobileNetV3-Small (transfer learning) |
| Backbone weights | ImageNet-1K pretrained (`IMAGENET1K_V1`) |
| Classifier head | Replaced with `Linear(576 → 3)` |
| Input size | 224 × 224 × 3 (RGB) |
| Classes | `Fresh`, `Okay`, `Avoid` |
| Parameters | ~2.5 M (lightweight, CPU-friendly) |
| Artifact | `models/food_freshness.pt` (state_dict only) |

MobileNetV3-Small was chosen because it is small enough to run inference on
Render's free-tier CPU while retaining strong ImageNet features that transfer
well to visual texture/colour tasks like freshness estimation.

## Preprocessing (inference)

Identical to validation-time preprocessing during training:

1. Resize to 256 px on the short side
2. Center-crop to 224 × 224
3. Convert to tensor, scale to [0, 1]
4. Normalise with ImageNet statistics (`mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`)

Inference runs in `torch.no_grad()` mode with the model in `eval()`.
Deterministic: same input image always produces the same probabilities.

## Training approach

See [`training/README.md`](../training/README.md) for full instructions.

- **Transfer learning**: backbone frozen initially; classifier head trained first
- **Data split**: 70% train / 15% validation / 15% test (stratified by class)
- **Augmentation** (train only): random resized crop, horizontal flip,
  colour jitter — no augmentation on val/test
- **Class imbalance**: optional weighted random sampler (`USE_WEIGHTED_SAMPLER`)
- **Optimiser**: Adam, LR 1e-3, weight decay 1e-4
- **Scheduler**: StepLR (step 7, gamma 0.1)
- **Early stopping**: patience 5 epochs on validation loss
- **Checkpointing**: best model by validation accuracy saved to `models/food_freshness.pt`
- **Reproducibility**: fixed seed (42) for `random`, `numpy`, and `torch`

## Evaluation

`training/evaluate.py` reports metrics measured on the held-out test split:

- Overall accuracy, macro precision / recall / F1
- Per-class precision, recall, F1, support
- Confusion matrix (saved as PNG + JSON)

Metrics are written to `models/metrics.json`. Only actually-measured values are
reported — this repository does not ship a trained artifact or fabricated
accuracy numbers. Run the evaluation yourself to produce real metrics for your
dataset.

## Inference process

```
Image upload
  → file validation (extension, MIME, size, decodability)
  → image quality gate (resolution, blur, brightness)
  → preprocessing (resize/crop/normalise)
  → MobileNetV3-Small forward pass
  → softmax → class probabilities
  → argmax label + confidence
  → confidence level (High ≥ 0.70, Medium ≥ 0.50, else Low)
  → persisted with model version + inference latency
```

Confidence comes directly from softmax probabilities. Low-confidence results
are flagged and never presented as definitive.

## Explainability

Grad-CAM targets the last convolutional block of MobileNetV3's feature
extractor. The heatmap shows where the model concentrated its attention for
the predicted class. It is an attention visualisation — it does **not**
prove causality.

## Limitations

- The model estimates freshness from a single photo; it cannot smell, taste,
  or detect bacteria.
- Accuracy depends heavily on dataset quality, lighting, and food coverage.
- Food categories not represented in training data may produce unreliable
  predictions.
- Image quality issues (blur, poor exposure) reduce reliability — such images
  are rejected by the quality gate rather than guessed at.
- This is a visual estimate, not a food-safety guarantee.