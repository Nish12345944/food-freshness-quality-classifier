# Training Pipeline

This directory trains and evaluates the food-freshness **image-classification** model that
powers the production prediction pipeline. No handcrafted heuristics are used for the
primary classification — predictions come from a real trained model.

## Model

- **Architecture:** MobileNetV3-Small (torchvision) with the classifier head replaced by a
  3-class `nn.Linear` head (`Fresh`, `Okay`, `Avoid`).
- **Size:** ~2.5M parameters — CPU-friendly, suitable for Render's free/small instances.
- **Pre-trained weights:** ImageNet, used for transfer learning.

## Requirements

Extra dependencies for training (not needed at runtime):

```bash
pip install torch torchvision scikit-learn matplotlib
```

## Dataset

> ⚠️ The raw dataset is **NOT** committed to the repository.

Arrange your data as:

```
data/food_freshness/          # config.DATA_DIR (override with DATA_DIR env)
    Fresh/
        img1.jpg ...
    Okay/
        img2.jpg ...
    Avoid/
        img3.jpg ...
```

The split (70/15/15 train/val/test) is **deterministic** (fixed seed) so results are
reproducible across runs.

## Train

```bash
cd training
python train.py
```

Environment variables you can set:

| Var | Default | Description |
|-----|---------|-------------|
| `DATA_DIR` | `data/food_freshness` | Path to dataset root |
| `EPOCHS` | `30` | Max epochs |
| `BATCH_SIZE` | `32` | Batch size |
| `LR` | `1e-3` | Learning rate |
| `EARLY_STOP_PATIENCE` | `5` | Early-stopping patience |
| `CHECKPOINT_DIR` | `models` | Output dir for artifact & metrics |

### What gets produced

- `models/food_freshness.pt` — the production artifact (PyTorch `state_dict` only).
- `models/training_history.json` — per-epoch loss/accuracy.
- `models/metrics.json` — validation metrics of the best model.

## Evaluate

```bash
cd training
python evaluate.py --model ../models/food_freshness.pt
```

Writes `models/metrics.json` with the held-out **test** metrics:

- accuracy
- weighted precision, recall, F1
- per-class precision/recall/F1/support
- confusion matrix (3×3)
- text classification report

Only metrics that are **actually measured** are reported — no fabricated numbers.

## Compatibility with the app

The runtime `app/services/prediction_service.py` loads `MODEL_PATH` (default
`models/food_freshness.pt`) with `torch.load(...map_location="cpu")` and expects the same
`build_model()` architecture (MobileNetV3-Small + 3-class head). Keep `training/config.CLASSES`
in sync with `app/services/prediction_service.py`'s `LABELS`.

## Reproducibility note

- Seed set via `config.SEED = 42` (applies to Python `random`, `numpy`, and `torch`).
- Weighted sampler is enabled by default for class-imbalance handling
  (`USE_WEIGHTED_SAMPLER = True` in `config.py`).