"""Dataset loading and splitting for food-freshness classification.

Expects a directory layout like:

    data/food_freshness/
        Fresh/
            img1.jpg ...
        Okay/
            img2.jpg ...
        Avoid/
            img3.jpg ...

Raw dataset files are NOT committed to the repository.  Users must point
DATA_DIR at their own locally-downloaded dataset.
"""

import os
import random
from collections import Counter
from pathlib import Path
from typing import List, Tuple

from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from .config import (  # noqa: E402  (same-directory import)
    CLASSES,
    DATA_DIR,
    INPUT_SIZE,
    SEED,
    TRAIN_SPLIT,
    VAL_SPLIT,
)

# ---------------------------------------------------------------------------
# Deterministic split
# ---------------------------------------------------------------------------


def _split_paths(image_paths: List[Path], rng: random.Random) -> Tuple[List[Path], List[Path], List[Path]]:
    """Split image paths into train/val/test using fixed proportions."""
    rng.shuffle(image_paths)
    n = len(image_paths)
    n_train = int(n * TRAIN_SPLIT)
    n_val = int(n * VAL_SPLIT)
    return (
        image_paths[:n_train],
        image_paths[n_train : n_train + n_val],
        image_paths[n_train + n_val :],
    )


def scan_dataset(root: str = DATA_DIR) -> Tuple[dict, List[Path], List[Path], List[Path]]:
    """Return (class_to_id, train_paths, val_paths, test_paths)."""
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(
            f"Dataset directory '{root}' not found. "
            "Point DATA_DIR at your downloaded dataset (do not commit the dataset)."
        )

    class_to_id = {name: i for i, name in enumerate(CLASSES)}
    paths = []

    for cls in CLASSES:
        cls_dir = root_path / cls
        if not cls_dir.is_dir():
            raise FileNotFoundError(f"Expected class folder '{cls_dir}' to exist.")
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            paths.extend(cls_dir.glob(ext))

    if not paths:
        raise RuntimeError(f"No images found under '{root}' for classes {CLASSES}.")

    rng = random.Random(SEED)
    train, val, test = _split_paths(paths, rng)
    return class_to_id, train, val, test


# ---------------------------------------------------------------------------
# Augmentation
# ---------------------------------------------------------------------------

def get_train_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(INPUT_SIZE, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def get_eval_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(INPUT_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


# ---------------------------------------------------------------------------
# In-memory dataset (small enough for a food image dataset)
# ---------------------------------------------------------------------------

class FoodDataset:
    def __init__(self, paths: List[Path], class_to_id: dict, is_train: bool):
        self.paths = paths
        self.class_to_id = class_to_id
        self.transform = get_train_transform() if is_train else get_eval_transform()
        self.targets = [class_to_id[p.parent.name] for p in paths]

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int):
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img), self.targets[idx]

    def class_weights(self) -> List[float]:
        """Inverse-frequency class weights for `WeightedRandomSampler`."""
        counts = Counter(self.targets)
        total = len(self.targets)
        return [total / (len(counts) * counts[c]) for c in range(len(self.class_to_id))]
