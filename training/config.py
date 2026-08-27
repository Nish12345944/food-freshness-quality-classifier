"""Training configuration — all hyperparameters in one place."""
import os

# Reproducibility
SEED = 42

# Dataset
DATA_DIR = os.environ.get("DATA_DIR", "data/food_freshness")
CLASSES = ["Fresh", "Okay", "Avoid"]
NUM_CLASSES = len(CLASSES)
TRAIN_SPLIT = 0.70
VAL_SPLIT = 0.15
# TEST_SPLIT = 1 - TRAIN_SPLIT - VAL_SPLIT = 0.15

# Model
MODEL_ARCH = "mobilenet_v3_small"   # lightweight, CPU-friendly
INPUT_SIZE = 224
PRETRAINED = True

# Training
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "16"))
EPOCHS = int(os.environ.get("EPOCHS", "20"))
LR = float(os.environ.get("LR", "1e-4"))
LR_STEP_SIZE = 7
LR_GAMMA = 0.1
WEIGHT_DECAY = 1e-4

# Early stopping
EARLY_STOP_PATIENCE = int(os.environ.get("EARLY_STOP_PATIENCE", "5"))

# Checkpointing
CHECKPOINT_DIR = os.environ.get("CHECKPOINT_DIR", "models")
BEST_MODEL_NAME = "food_freshness.pt"

# Class imbalance — set to True to use weighted sampler
USE_WEIGHTED_SAMPLER = False
