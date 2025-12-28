from transformers import AutoImageProcessor, AutoModelForImageClassification
import torch
import torch.nn as nn
from PIL import Image
import numpy as np

# Food freshness classification labels
LABELS = ["Fresh", "Okay", "Avoid"]
NUM_CLASSES = len(LABELS)

class FoodFreshnessClassifier(nn.Module):
    def __init__(self, num_classes=3):
        super(FoodFreshnessClassifier, self).__init__()
        # Use a pre-trained vision transformer as backbone
        self.processor = AutoImageProcessor.from_pretrained('google/vit-base-patch16-224')
        self.backbone = AutoModelForImageClassification.from_pretrained('google/vit-base-patch16-224')
        
        # Replace the classifier head for our specific task
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(self.backbone.config.hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, pixel_values):
        outputs = self.backbone(pixel_values=pixel_values)
        return outputs.logits
    
    def predict(self, image_path):
        """Predict food freshness from image path"""
        image = Image.open(image_path).convert('RGB')
        inputs = self.processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            logits = self.forward(inputs['pixel_values'])
            probabilities = torch.nn.functional.softmax(logits, dim=1)
            
        predicted_class = torch.argmax(probabilities, dim=1).item()
        confidence = probabilities[0][predicted_class].item()
        
        return LABELS[predicted_class], round(confidence * 100, 2)

# Initialize the model
model = FoodFreshnessClassifier(num_classes=NUM_CLASSES)
processor = model.processor

# Simulate trained weights (in a real scenario, you would load pre-trained weights)
# For demonstration, we'll use the pre-trained backbone
print("Food Freshness Classifier Model initialized successfully!")
print(f"Model supports {NUM_CLASSES} classes: {LABELS}")
