"""Metrics: accuracy, precision, recall, F1, per-class metrics, confusion matrix."""

import json
from pathlib import Path
from typing import Dict, List, Sequence

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


def compute_metrics(y_true: Sequence[int], y_pred: Sequence[int], class_names: List[str]) -> dict:
    """Compute all evaluation metrics from true/predicted class indices."""
    labels = list(range(len(class_names)))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "per_class": _per_class(y_true, y_pred, class_names),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "classification_report_text": classification_report(
            y_true, y_pred, target_names=class_names, zero_division=0
        ),
    }


def _per_class(y_true: Sequence[int], y_pred: Sequence[int], names: Sequence[str]) -> Dict[str, dict]:
    rows = []
    for i, name in enumerate(names):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == i and p == i)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != i and p == i)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == i and p != i)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = sum(1 for t in y_true if t == i)
        rows.append({
            "class": name,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        })
    return rows


def save_metrics(metrics: dict, out_dir: str) -> str:
    """Write metrics to JSON and return the path."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out = Path(out_dir) / "metrics.json"
    out.write_text(json.dumps(metrics, indent=2))
    return str(out)