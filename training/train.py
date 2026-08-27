"""Train the FoodFresh AI food-freshness classifier.

Uses ImageNet-pretrained MobileNetV3-Small with transfer learning
and fine-tuning.

Classes:
    Fresh
    Okay
    Avoid
"""

import json
import logging
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from . import config
from .dataset import FoodDataset, scan_dataset
from .metrics import compute_metrics, save_metrics


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("train")


def set_seed(seed: int) -> None:
    """Make training as reproducible as possible."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(num_classes: int) -> nn.Module:
    """Build ImageNet-pretrained MobileNetV3-Small."""
    from torchvision.models import (
        MobileNet_V3_Small_Weights,
        mobilenet_v3_small,
    )

    model = mobilenet_v3_small(
        weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1
    )

    in_features = model.classifier[3].in_features

    model.classifier[3] = nn.Linear(
        in_features,
        num_classes,
    )

    return model


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer,
    criterion,
    device: torch.device,
) -> dict:
    """Train for one epoch."""

    model.train()

    total_loss = 0.0
    correct = 0

    for x, y in loader:
        x = x.to(device)
        y = y.to(device)

        optimizer.zero_grad()

        logits = model(x)
        loss = criterion(logits, y)

        loss.backward()
        optimizer.step()

        total_loss += loss.item() * x.size(0)

        predictions = torch.argmax(logits, dim=1)
        correct += (predictions == y).sum().item()

    n = len(loader.dataset)

    return {
        "loss": total_loss / n if n else 0.0,
        "acc": correct / n if n else 0.0,
    }


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion,
    device: torch.device,
) -> dict:
    """Evaluate model on validation/test data."""

    model.eval()

    total_loss = 0.0
    correct = 0

    y_true = []
    y_pred = []

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)

            logits = model(x)

            loss = criterion(logits, y)

            total_loss += loss.item() * x.size(0)

            predictions = torch.argmax(logits, dim=1)

            correct += (predictions == y).sum().item()

            y_true.extend(y.cpu().tolist())
            y_pred.extend(predictions.cpu().tolist())

    n = len(loader.dataset)

    return {
        "loss": total_loss / n if n else 0.0,
        "acc": correct / n if n else 0.0,
        "y_true": y_true,
        "y_pred": y_pred,
    }


def main() -> None:

    # --------------------------------------------------------
    # Reproducibility
    # --------------------------------------------------------

    set_seed(config.SEED)

    # --------------------------------------------------------
    # Device
    # --------------------------------------------------------

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    logger.info("Device: %s", device)

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    (
        class_to_id,
        train_paths,
        val_paths,
        test_paths,
    ) = scan_dataset()

    logger.info(
        "Dataset splits: train=%d val=%d test=%d",
        len(train_paths),
        len(val_paths),
        len(test_paths),
    )

    logger.info(
        "Classes: %s",
        class_to_id,
    )

    train_ds = FoodDataset(
        train_paths,
        class_to_id,
        is_train=True,
    )

    val_ds = FoodDataset(
        val_paths,
        class_to_id,
        is_train=False,
    )

    test_ds = FoodDataset(
        test_paths,
        class_to_id,
        is_train=False,
    )

    # --------------------------------------------------------
    # Data loaders
    # --------------------------------------------------------

    train_loader = DataLoader(
        train_ds,
        batch_size=config.BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    test_loader = DataLoader(
        test_ds,
        batch_size=config.BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = build_model(
        config.NUM_CLASSES
    ).to(device)

    logger.info(
        "Loaded ImageNet-pretrained MobileNetV3-Small"
    )

    # --------------------------------------------------------
    # Fine-tuning
    # --------------------------------------------------------
    #
    # Unlike the previous version, we DO NOT permanently
    # freeze the backbone.
    #
    # The entire network is trainable so the pretrained
    # features can adapt to food freshness.
    # --------------------------------------------------------

    for parameter in model.parameters():
        parameter.requires_grad = True

    trainable_params = sum(
        parameter.numel()
        for parameter in model.parameters()
        if parameter.requires_grad
    )

    logger.info(
        "Trainable parameters: %d",
        trainable_params,
    )

    # --------------------------------------------------------
    # Loss
    # --------------------------------------------------------

    criterion = nn.CrossEntropyLoss()

    # --------------------------------------------------------
    # Optimizer
    # --------------------------------------------------------

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.LR,
        weight_decay=config.WEIGHT_DECAY,
    )

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.3,
        patience=2,
    )

    # --------------------------------------------------------
    # Checkpoint directory
    # --------------------------------------------------------

    os.makedirs(
        config.CHECKPOINT_DIR,
        exist_ok=True,
    )

    best_path = (
        Path(config.CHECKPOINT_DIR)
        / config.BEST_MODEL_NAME
    )

    # --------------------------------------------------------
    # Training loop
    # --------------------------------------------------------

    best_val_loss = float("inf")
    epochs_without_improvement = 0

    history = []

    logger.info(
        "Starting training for up to %d epochs",
        config.EPOCHS,
    )

    for epoch in range(
        1,
        config.EPOCHS + 1,
    ):

        train_metrics = train_epoch(
            model,
            train_loader,
            optimizer,
            criterion,
            device,
        )

        val_metrics = evaluate(
            model,
            val_loader,
            criterion,
            device,
        )

        scheduler.step(
            val_metrics["loss"]
        )

        current_lr = optimizer.param_groups[0]["lr"]

        logger.info(
            "Epoch %d/%d | "
            "LR=%.6f | "
            "train_loss=%.4f | "
            "train_acc=%.4f | "
            "val_loss=%.4f | "
            "val_acc=%.4f",
            epoch,
            config.EPOCHS,
            current_lr,
            train_metrics["loss"],
            train_metrics["acc"],
            val_metrics["loss"],
            val_metrics["acc"],
        )

        history.append(
            {
                "epoch": epoch,
                "learning_rate": current_lr,
                "train_loss": train_metrics["loss"],
                "train_accuracy": train_metrics["acc"],
                "val_loss": val_metrics["loss"],
                "val_accuracy": val_metrics["acc"],
            }
        )

        # ----------------------------------------------------
        # Save best model
        # ----------------------------------------------------

        if val_metrics["loss"] < (
            best_val_loss - 1e-4
        ):

            best_val_loss = val_metrics["loss"]

            epochs_without_improvement = 0

            torch.save(
                model.state_dict(),
                best_path,
            )

            logger.info(
                "New best model saved: %s",
                best_path,
            )

        else:

            epochs_without_improvement += 1

            if (
                epochs_without_improvement
                >= config.EARLY_STOP_PATIENCE
            ):

                logger.info(
                    "Early stopping at epoch %d",
                    epoch,
                )

                break

    # --------------------------------------------------------
    # Save training history
    # --------------------------------------------------------

    history_path = (
        Path(config.CHECKPOINT_DIR)
        / "training_history.json"
    )

    history_path.write_text(
        json.dumps(
            history,
            indent=2,
        )
    )

    logger.info(
        "Training history saved to %s",
        history_path,
    )

    # --------------------------------------------------------
    # Evaluate best model
    # --------------------------------------------------------

    if not best_path.exists():

        raise RuntimeError(
            "Training completed but no model checkpoint was created."
        )

    best_model = build_model(
        config.NUM_CLASSES
    ).to(device)

    best_model.load_state_dict(
        torch.load(
            best_path,
            map_location=device,
        )
    )

    best_model.eval()

    # --------------------------------------------------------
    # Validation metrics
    # --------------------------------------------------------

    val_metrics = evaluate(
        best_model,
        val_loader,
        criterion,
        device,
    )

    metrics = compute_metrics(
        val_metrics["y_true"],
        val_metrics["y_pred"],
        config.CLASSES,
    )

    metrics["split"] = "validation"

    validation_output = save_metrics(
        metrics,
        config.CHECKPOINT_DIR,
    )

    logger.info(
        "Validation accuracy: %.4f",
        metrics["accuracy"],
    )

    logger.info(
        "Validation metrics saved to %s",
        validation_output,
    )

    # --------------------------------------------------------
    # Test metrics
    # --------------------------------------------------------

    test_metrics = evaluate(
        best_model,
        test_loader,
        criterion,
        device,
    )

    final_metrics = compute_metrics(
        test_metrics["y_true"],
        test_metrics["y_pred"],
        config.CLASSES,
    )

    final_metrics["split"] = "test"

    test_output = save_metrics(
        final_metrics,
        config.CHECKPOINT_DIR,
    )

    logger.info(
        "TEST accuracy: %.4f",
        final_metrics["accuracy"],
    )

    logger.info(
        "Test metrics saved to %s",
        test_output,
    )

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("Best model: %s", best_path)
    logger.info(
        "Test accuracy: %.2f%%",
        final_metrics["accuracy"] * 100,
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()