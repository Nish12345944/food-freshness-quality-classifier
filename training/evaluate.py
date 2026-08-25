"""Evaluate a trained model on the test split and emit metric artifacts.

Usage:
    cd training
    python evaluate.py [--model path/to/food_freshness.pt]

Reads the same dataset split as train.py and writes metrics.json.
Only metrics that are actually measured are reported.
"""

import argparse
import logging
import os
from pathlib import Path

import torch
from torch.utils.data import DataLoader

import config
from dataset import FoodDataset, scan_dataset
from metrics import compute_metrics, save_metrics
from train import build_model, evaluate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=os.path.join(config.CHECKPOINT_DIR, config.BEST_MODEL_NAME),
        help="Path to the trained state_dict to evaluate.",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = Path(args.model)
    if not model_path.exists():
        raise SystemExit(f"Model file not found: {model_path}")

    # Use the deterministic split so test set matches train.py
    class_to_id, train_paths, val_paths, test_paths = scan_dataset()

    if not test_paths:
        raise SystemExit("No test images found — cannot evaluate on a held-out test split.")

    test_ds = FoodDataset(test_paths, class_to_id, is_train=False)
    test_loader = DataLoader(test_ds, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)
    logger.info("Evaluating %s on %d test images", model_path, len(test_ds))

    model = build_model(config.NUM_CLASSES).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    result = evaluate(model, test_loader, device)
    metrics = compute_metrics(result["y_true"], result["y_pred"], config.CLASSES)
    metrics["split"] = "test"
    metrics["n_samples"] = len(result["y_true"])

    out = save_metrics(metrics, config.CHECKPOINT_DIR)
    logger.info("Test metrics saved to %s", out)
    logger.info("\n%s", metrics["classification_report_text"])


if __name__ == "__main__":
    main()