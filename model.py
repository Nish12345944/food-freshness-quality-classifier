from transformers import AutoImageProcessor, AutoModelForImageClassification
import torch

MODEL_NAME = "google/vit-base-patch16-224"

processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)

model.eval()
