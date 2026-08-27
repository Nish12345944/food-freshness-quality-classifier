"""Evaluate a trained FoodFresh AI model on the held-out test split.

Usage from project root:
    python -m training.evaluate

Optional:
    python -m training.evaluate --model models/food_freshness.pt

Reads the same deterministic dataset split used during training
and writes test metrics to the configured checkpoint directory.
"""

import argparse
import logging
import os
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from . import config
from .dataset import FoodDataset, scan_dataset
from .metrics import compute_metrics, save_metrics
from .train import build_model, evaluate


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("evaluate")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        default=os.path.join(
            config.CHECKPOINT_DIR,
            config.BEST_MODEL_NAME,
        ),
        help="Path to the trained model state_dict.",
    )

    args = parser.parse_args()

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    # --------------------------------------------------------
    # Model path
    # --------------------------------------------------------

    model_path = Path(args.model)

    if not model_path.exists():
        raise SystemExit(
            f"Model file not found: {model_path}"
        )

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    (
        class_to_id,
        train_paths,
        val_paths,
        test_paths,
    ) = scan_dataset()

    if not test_paths:
        raise SystemExit(
            "No test images found — cannot evaluate "
            "on a held-out test split."
        )

    test_ds = FoodDataset(
        test_paths,
        class_to_id,
        is_train=False,
    )

    test_loader = DataLoader(
        test_ds,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    logger.info(
        "Evaluating %s on %d test images",
        model_path,
        len(test_ds),
    )

    # --------------------------------------------------------
    # Load model
    # --------------------------------------------------------

    model = build_model(
        config.NUM_CLASSES
    ).to(device)

    model.load_state_dict(
        torch.load(
            model_path,
            map_location=device,
        )
    )

    model.eval()

    # --------------------------------------------------------
    # Loss function
    # --------------------------------------------------------

    criterion = nn.CrossEntropyLoss()

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    result = evaluate(
        model,
        test_loader,
        criterion,
        device,
    )

    # --------------------------------------------------------
    # Calculate metrics
    # --------------------------------------------------------

    metrics = compute_metrics(
        result["y_true"],
        result["y_pred"],
        config.CLASSES,
    )

    metrics["split"] = "test"
    metrics["n_samples"] = len(
        result["y_true"]
    )

    # --------------------------------------------------------
    # Save metrics
    # --------------------------------------------------------

    output_path = save_metrics(
        metrics,
        config.CHECKPOINT_DIR,
    )

    logger.info(
        "Test metrics saved to %s",
        output_path,
    )

    # --------------------------------------------------------
    # Display classification report
    # --------------------------------------------------------

    logger.info(
        "\n%s",
        metrics["classification_report_text"],
    )

    logger.info("=" * 60)
    logger.info("TEST EVALUATION COMPLETE")
    logger.info(
        "Test accuracy: %.2f%%",
        metrics["accuracy"] * 100,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()