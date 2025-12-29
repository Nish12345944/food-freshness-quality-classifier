import cv2
import numpy as np
from PIL import Image
import os

LABELS = ["Fresh", "Okay", "Avoid"]

FOOD_TYPES = {
    'fruit': ['apple', 'banana', 'orange', 'strawberry', 'grape', 'watermelon', 'mango', 'pineapple'],
    'vegetable': ['tomato', 'carrot', 'lettuce', 'broccoli', 'cucumber', 'pepper', 'spinach', 'cabbage'],
    'meat': ['chicken', 'beef', 'pork', 'fish', 'mutton', 'lamb'],
    'dairy': ['milk', 'cheese', 'yogurt', 'butter', 'paneer', 'cream'],
    'cooked_food': ['curry', 'sabji', 'rice', 'pasta', 'soup', 'stew', 'gravy'],
    'bread': ['bread', 'roti', 'naan', 'bun', 'toast', 'bagel'],
    'seafood': ['fish', 'shrimp', 'crab', 'lobster', 'prawns'],
    'eggs': ['egg', 'omelette', 'boiled_egg']
}

STORAGE_TIPS = {
    'fruit': {
        'temperature': '35-45°F (2-7°C)',
        'humidity': '85-95%',
        'shelf_life': '3-7 days',
        'tips': ['Store in refrigerator crisper', 'Keep away from ethylene-producing fruits', 'Wash before eating, not before storing']
    },
    'vegetable': {
        'temperature': '32-40°F (0-4°C)',
        'humidity': '90-95%',
        'shelf_life': '5-10 days',
        'tips': ['Store in refrigerator crisper', 'Keep in perforated plastic bags', 'Remove any damaged pieces']
    },
    'meat': {
        'temperature': '32-40°F (0-4°C)',
        'humidity': '80-85%',
        'shelf_life': '1-3 days',
        'tips': ['Store in coldest part of fridge', 'Keep in original packaging', 'Use within 2 days or freeze']
    },
    'dairy': {
        'temperature': '35-40°F (2-4°C)',
        'humidity': '80-85%',
        'shelf_life': '5-14 days',
        'tips': ['Keep refrigerated at all times', 'Store in original container', 'Check expiration dates']
    },
    'cooked_food': {
        'temperature': '35-40°F (2-4°C)',
        'humidity': '70-80%',
        'shelf_life': '2-4 days',
        'tips': ['Refrigerate within 2 hours of cooking', 'Store in airtight containers', 'Reheat thoroughly before consuming', 'Discard if sour smell or mold appears']
    },
    'bread': {
        'temperature': '68-72°F (20-22°C)',
        'humidity': '60-70%',
        'shelf_life': '3-7 days',
        'tips': ['Store in cool, dry place', 'Keep in bread box or sealed bag', 'Freeze for longer storage', 'Check for mold before eating']
    },
    'seafood': {
        'temperature': '32-38°F (0-3°C)',
        'humidity': '95-100%',
        'shelf_life': '1-2 days',
        'tips': ['Store on ice in refrigerator', 'Use immediately or freeze', 'Check for fishy odor', 'Keep separate from other foods']
    },
    'eggs': {
        'temperature': '35-40°F (2-4°C)',
        'humidity': '70-80%',
        'shelf_life': '3-5 weeks',
        'tips': ['Store in refrigerator', 'Keep in original carton', 'Check expiration date', 'Discard if cracked or smells bad']
    }
}

class SimpleFoodClassifier:
    def predict(self, image_path):
        return simulate_prediction(image_path)
    
    def detect_food_type(self, image_path):
        return detect_food_category(image_path)

model = SimpleFoodClassifier()

def predict_image(image_path):
    try:
        if not os.path.exists(image_path):
            return "Error", 0.0, "unknown"
        
        label, confidence = model.predict(image_path)
        food_type = model.detect_food_type(image_path)
        return label, confidence, food_type
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return simulate_prediction(image_path)

def simulate_prediction(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "Error", 0.0, "unknown"
        
        # Resize for faster processing (max 640px)
        height, width = image.shape[:2]
        if width > 640 or height > 640:
            scale = 640 / max(width, height)
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        
        # Convert to HSV only (faster)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Quick statistics
        h_mean = np.mean(hsv[:, :, 0])
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # Simplified spoilage detection (only critical ones)
        # 1. Mold (green/black spots)
        mold_mask = ((hsv[:, :, 0] >= 80) & (hsv[:, :, 0] <= 140) & (hsv[:, :, 1] > 30) & (hsv[:, :, 2] < 100)) | \
                    ((hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 40))
        mold_ratio = np.sum(mold_mask) / total_pixels
        
        # 2. Dark brown rot
        rotten_mask = (hsv[:, :, 0] >= 5) & (hsv[:, :, 0] <= 25) & (hsv[:, :, 1] > 40) & (hsv[:, :, 2] < 60)
        rotten_ratio = np.sum(rotten_mask) / total_pixels
        
        # 3. Gray discoloration (cooked food)
        gray_mask = (hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 40) & (hsv[:, :, 2] < 120)
        gray_ratio = np.sum(gray_mask) / total_pixels
        
        # Calculate freshness score
        freshness_score = 70
        freshness_score -= mold_ratio * 200
        freshness_score -= rotten_ratio * 120
        if gray_ratio > 0.3:
            freshness_score -= 50
        if v_mean < 35:
            freshness_score -= 30
        elif v_mean > 200:
            freshness_score += 5
        if s_mean > 100 and v_mean > 100:
            freshness_score += 10
        
        freshness_score = max(0, min(100, freshness_score))
        
        # Quick food type detection
        food_type = detect_food_category_fast(hsv, s_mean, v_mean)
        
        # Classification
        if food_type == 'cooked_food':
            if freshness_score >= 65:
                label = "Fresh"
                confidence = np.random.uniform(82, 92)
            elif freshness_score >= 40:
                label = "Okay"
                confidence = np.random.uniform(72, 85)
            else:
                label = "Avoid"
                confidence = np.random.uniform(82, 95)
        else:
            if freshness_score >= 60:
                label = "Fresh"
                confidence = np.random.uniform(85, 95)
            elif freshness_score >= 35:
                label = "Okay"
                confidence = np.random.uniform(70, 85)
            else:
                label = "Avoid"
                confidence = np.random.uniform(80, 95)
        
        return label, round(confidence, 2), food_type
            
    except Exception as e:
        print(f"Simulation error: {str(e)}")
        return "Okay", 70.0, "fruit"

def detect_food_category_fast(hsv, s_mean, v_mean):
    """Fast food category detection using pre-computed HSV"""
    try:
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # Quick color ratios
        white_ratio = np.sum((hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 120)) / total_pixels
        green_ratio = np.sum((hsv[:, :, 0] > 40) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 30)) / total_pixels
        orange_ratio = np.sum((hsv[:, :, 0] > 10) & (hsv[:, :, 0] <= 40) & (hsv[:, :, 1] > 40)) / total_pixels
        brown_ratio = np.sum((hsv[:, :, 0] > 5) & (hsv[:, :, 0] < 35) & (hsv[:, :, 1] < 100) & (hsv[:, :, 2] > 40)) / total_pixels
        
        # Quick classification
        if white_ratio > 0.25 and (orange_ratio > 0.15 or green_ratio > 0.10):
            return "cooked_food"
        if white_ratio > 0.50:
            return "dairy"
        if brown_ratio > 0.30 and s_mean < 50:
            return "bread"
        if green_ratio > 0.25:
            return "vegetable"
        if s_mean > 60 and v_mean > 100:
            return "fruit"
        return "cooked_food"
    except:
        return "fruit"

def detect_food_category(image_path):
    """Detailed food category detection (fallback)"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "fruit"
        
        # Resize for speed
        height, width = image.shape[:2]
        if width > 640 or height > 640:
            scale = 640 / max(width, height)
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        
        return detect_food_category_fast(hsv, s_mean, v_mean)
            
    except Exception as e:
        print(f"Food category detection error: {str(e)}")
        return "cooked_food"

def get_storage_tips(food_type):
    return STORAGE_TIPS.get(food_type, STORAGE_TIPS['fruit'])

def analyze_image_quality(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return {"quality": "Poor", "resolution": "Unknown", "blur_score": 0}
        
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate blur score using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Analyze image for quality indicators (not freshness)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check lighting quality
        brightness = np.mean(hsv[:, :, 2])
        brightness_std = np.std(hsv[:, :, 2])
        
        # Check if image is too dark or overexposed
        too_dark = brightness < 50
        too_bright = brightness > 230
        poor_lighting = brightness_std < 20  # low contrast
        
        # Check resolution adequacy
        low_resolution = width < 224 or height < 224
        
        # Determine technical quality (not food freshness)
        if blur_score < 50:
            quality = "Poor - Blurry Image"
        elif too_dark:
            quality = "Poor - Too Dark"
        elif too_bright:
            quality = "Poor - Overexposed"
        elif poor_lighting:
            quality = "Fair - Low Contrast"
        elif low_resolution:
            quality = "Fair - Low Resolution"
        elif blur_score > 100 and width >= 224 and height >= 224:
            quality = "Good - Clear Image"
        else:
            quality = "Fair - Acceptable"
        
        return {
            "quality": quality,
            "resolution": f"{width}x{height}",
            "blur_score": round(blur_score, 2)
        }
    except Exception as e:
        print(f"Quality analysis error: {str(e)}")
        return {"quality": "Unknown", "resolution": "Unknown", "blur_score": 0}
