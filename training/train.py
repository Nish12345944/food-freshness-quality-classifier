"""Train the food-freshness classifier (MobileNetV3-Small transfer learning).

Usage:
    cd training
    python train.py            # uses config.py defaults / env vars

Produces the production artifact at CHECKPOINT_DIR/BEST_MODEL_NAME
(only the state_dict is saved).  Also writes metrics.json for the
best model on the validation set.
"""

import json
import logging
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, WeightedRandomSampler

import config
from dataset import FoodDataset, scan_dataset
from metrics import compute_metrics, save_metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(num_classes: int) -> nn.Module:
    """MobileNetV3-Small with a 3-class head (matches prediction_service)."""
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, num_classes)
    return model


def freeze_backbone(model: nn.Module, freeze: bool) -> None:
    """Freeze (or unfreeze) all layers except the classifier head."""
    for name, param in model.named_parameters():
        if "classifier" not in name:
            param.requires_grad = not freeze


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> dict:
    """Return {loss, acc, y_true, y_pred} on the given loader."""
    model.eval()
    total_loss = 0.0
    correct = 0
    y_true: list = []
    y_pred: list = []
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            y = y.to(device)
            logits = model(x)
            loss = criterion(logits, y)
            total_loss += loss.item() * x.size(0)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == y).sum().item()
            y_true.extend(y.cpu().tolist())
            y_pred.extend(preds.cpu().tolist())

    n = len(loader.dataset)
    return {"loss": total_loss / n if n else 0.0, "acc": correct / n if n else 0.0, "y_true": y_true, "y_pred": y_pred}


def train_epoch(model: nn.Module, loader: DataLoader, optimizer, device: torch.device) -> dict:
    model.train()
    total = 0.0
    correct = 0
    criterion = nn.CrossEntropyLoss()
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total += loss.item() * x.size(0)
        correct += (torch.argmax(logits, dim=1) == y).sum().item()
    n = len(loader.dataset)
    return {"loss": total / n if n else 0.0, "acc": correct / n if n else 0.0}


def main() -> None:
    set_seed(config.SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Device: %s", device)

    # Data
    class_to_id, train_paths, val_paths, test_paths = scan_dataset()
    logger.info("Splits: train=%d val=%d test=%d", len(train_paths), len(val_paths), len(test_paths))

    train_ds = FoodDataset(train_paths, class_to_id, is_train=True)
    val_ds = FoodDataset(val_paths, class_to_id, is_train=False)

    sampler = None
    if config.USE_WEIGHTED_SAMPLER:
        weights = torch.tensor(train_ds.class_weights(), dtype=torch.float)
        sampler = WeightedRandomSampler(
            weights.repeat(len(train_ds)), num_samples=len(train_ds), replacement=True
        )
        logger.info("Using weighted sampler (class imbalance handling)")

    train_loader = DataLoader(
        train_ds, batch_size=config.BATCH_SIZE, shuffle=(sampler is None), sampler=sampler, num_workers=0
    )
    val_loader = DataLoader(val_ds, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = None
    if test_paths:
        test_ds = FoodDataset(test_paths, class_to_id, is_train=False)
        test_loader = DataLoader(test_ds, batch_size=config.BATCH_SIZE, shuffle=False, num_workers=0)

    # Model
    model = build_model(config.NUM_CLASSES).to(device)
    freeze_backbone(model, True)  # start with frozen backbone

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=config.LR, weight_decay=config.WEIGHT_DECAY
    )
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=config.LR_STEP_SIZE, gamma=config.LR_GAMMA)

    os.makedirs(config.CHECKPOINT_DIR, exist_ok=True)
    best_path = Path(config.CHECKPOINT_DIR) / config.BEST_MODEL_NAME

    best_val_loss = float("inf")
    epochs_no_improve = 0
    records: list = []

    logger.info("Starting training for up to %d epochs", config.EPOCHS)
    for epoch in range(1, config.EPOCHS + 1):
        train_m = train_epoch(model, train_loader, optimizer, device)
        scheduler.step()

        val_m = evaluate(model, val_loader, device)
        logger.info(
            "Epoch %d/%d train_loss=%.4f train_acc=%.4f val_loss=%.4f val_acc=%.4f",
            epoch, config.EPOCHS, train_m["loss"], train_m["acc"], val_m["loss"], val_m["acc"],
        )
        records.append(
            {
                "epoch": epoch,
                "train_loss": train_m["loss"],
                "train_acc": train_m["acc"],
                "val_loss": val_m["loss"],
                "val_acc": val_m["acc"],
            }
        )

        # Checkpoint if improved
        if val_m["loss"] < best_val_loss - 1e-4:
            best_val_loss = val_m["loss"]
            epochs_no_improve = 0
            torch.save(model.state_dict(), best_path)  # only state_dict
            logger.info("New best model saved to %s (val_loss=%.4f)", best_path, best_val_loss)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= config.EARLY_STOP_PATIENCE:
                logger.info(
                    "Early stopping at epoch %d (no improvement for %d epochs)",
                    epoch, config.EARLY_STOP_PATIENCE,
                )
                break

    # Save training history
    history_path = Path(config.CHECKPOINT_DIR) / "training_history.json"
    history_path.write_text(json.dumps(records, indent=2))
    logger.info("Training history saved to %s", history_path)

    # Metrics for best model on validation split
    if best_path.exists():
        model = build_model(config.NUM_CLASSES).to(device)
        model.load_state_dict(torch.load(best_path, map_location=device))
        model.eval()
        val_m = evaluate(model, val_loader, device)
        metrics = compute_metrics(val_m["y_true"], val_m["y_pred"], config.CLASSES)
        metrics["split"] = "validation"
        out = save_metrics(metrics, config.CHECKPOINT_DIR)
        logger.info("Validation metrics saved to %s — accuracy: %.4f", out, metrics["accuracy"])

    # Metrics for best model on test split (if any)
    if test_loader is not None and best_path.exists():
        model = build_model(config.NUM_CLASSES).to(device)
        model.load_state_dict(torch.load(best_path, map_location=device))
        model.eval()
        test_m = evaluate(model, test_loader, device)
        test_metrics = compute_metrics(test_m["y_true"], test_m["y_pred"], config.CLASSES)
        test_metrics["split"] = "test"
        test_out = save_metrics(test_metrics, config.CHECKPOINT_DIR)
        logger.info("Test metrics saved to %s — accuracy: %.4f", test_out, test_metrics["accuracy"])


if __name__ == "__main__":
    main()