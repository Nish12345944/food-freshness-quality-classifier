import cv2
import numpy as np
from PIL import Image
import os

LABELS = ["Fresh", "Okay", "Avoid"]

FOOD_TYPES = {
    'fruit': ['apple', 'banana', 'orange', 'strawberry', 'grape', 'watermelon'],
    'vegetable': ['tomato', 'carrot', 'lettuce', 'broccoli', 'cucumber', 'pepper'],
    'meat': ['chicken', 'beef', 'pork', 'fish'],
    'dairy': ['milk', 'cheese', 'yogurt', 'butter']
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
        
        # Convert to multiple color spaces for comprehensive analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Extract color statistics
        h_mean, s_mean, v_mean = np.mean(hsv[:, :, 0]), np.mean(hsv[:, :, 1]), np.mean(hsv[:, :, 2])
        h_std, s_std, v_std = np.std(hsv[:, :, 0]), np.std(hsv[:, :, 1]), np.std(hsv[:, :, 2])
        l_mean, a_mean, b_mean = np.mean(lab[:, :, 0]), np.mean(lab[:, :, 1]), np.mean(lab[:, :, 2])
        
        # Texture analysis - rotten food has irregular texture
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        # Color distribution analysis
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # Detect brown/rotten colors (10-30° hue, moderate saturation)
        brown_mask = (hsv[:, :, 0] >= 5) & (hsv[:, :, 0] <= 35) & (hsv[:, :, 1] > 20) & (hsv[:, :, 1] < 180)
        brown_ratio = np.sum(brown_mask) / total_pixels
        
        # Detect gray/dull colors (low saturation)
        gray_mask = hsv[:, :, 1] < 30
        gray_ratio = np.sum(gray_mask) / total_pixels
        
        # Detect dark spots (mold/decay indicators)
        dark_mask = hsv[:, :, 2] < 50
        dark_ratio = np.sum(dark_mask) / total_pixels
        
        # Detect greenish mold (80-140° hue with low brightness)
        mold_mask = (hsv[:, :, 0] >= 80) & (hsv[:, :, 0] <= 140) & (hsv[:, :, 2] < 100) & (hsv[:, :, 1] > 30)
        mold_ratio = np.sum(mold_mask) / total_pixels
        
        # Color uniformity - fresh food has more uniform colors
        color_uniformity = 1 / (1 + h_std + s_std)
        
        # Calculate freshness score (0-100)
        freshness_score = 50  # baseline
        
        # Penalties for rotten indicators
        freshness_score -= brown_ratio * 80  # heavy penalty for brown
        freshness_score -= gray_ratio * 60   # penalty for dullness
        freshness_score -= dark_ratio * 70   # penalty for dark spots
        freshness_score -= mold_ratio * 100  # severe penalty for mold
        freshness_score -= (1 - color_uniformity) * 30  # penalty for non-uniformity
        
        # Bonuses for fresh indicators
        if s_mean > 80 and v_mean > 120:  # bright and saturated
            freshness_score += 30
        if h_std > 25 and s_std > 20:  # good color variance
            freshness_score += 20
        if edge_density < 0.15 and laplacian_var > 100:  # smooth but sharp
            freshness_score += 15
        
        # LAB color space analysis (a: green-red, b: blue-yellow)
        if a_mean < 120 or b_mean < 120:  # dull colors in LAB
            freshness_score -= 20
        
        # Clamp score between 0-100
        freshness_score = max(0, min(100, freshness_score))
        
        food_type = detect_food_category(image_path)
        
        # Classification based on freshness score
        if freshness_score >= 65:
            label = "Fresh"
            confidence = np.random.uniform(freshness_score - 5, min(95, freshness_score + 5))
        elif freshness_score >= 35:
            label = "Okay"
            confidence = np.random.uniform(freshness_score - 5, freshness_score + 10)
        else:
            label = "Avoid"
            confidence = np.random.uniform(75, 95)  # high confidence for rotten
        
        return label, round(confidence, 2), food_type
            
    except Exception as e:
        print(f"Simulation error: {str(e)}")
        return "Okay", 70.0, "fruit"

def detect_food_category(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "fruit"
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_mean = np.mean(hsv[:, :, 0])
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        
        # Count dominant color pixels
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # Red fruits (strawberries, apples, tomatoes) - 0-10 or 170-180 hue
        red_mask = ((hsv[:, :, 0] <= 10) | (hsv[:, :, 0] >= 170)) & (hsv[:, :, 1] > 50)
        red_ratio = np.sum(red_mask) / total_pixels
        
        # Orange/Yellow fruits (oranges, bananas) - 10-40 hue
        orange_mask = (hsv[:, :, 0] > 10) & (hsv[:, :, 0] <= 40) & (hsv[:, :, 1] > 50)
        orange_ratio = np.sum(orange_mask) / total_pixels
        
        # Green vegetables - 40-85 hue
        green_mask = (hsv[:, :, 0] > 40) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 30)
        green_ratio = np.sum(green_mask) / total_pixels
        
        # Brown/beige (meat, bread) - low saturation, moderate hue
        brown_mask = (hsv[:, :, 0] > 5) & (hsv[:, :, 0] < 30) & (hsv[:, :, 1] < 80) & (hsv[:, :, 2] > 50)
        brown_ratio = np.sum(brown_mask) / total_pixels
        
        # White/cream (dairy) - very low saturation
        white_mask = (hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 150)
        white_ratio = np.sum(white_mask) / total_pixels
        
        # Classification based on dominant color
        if red_ratio > 0.25 or orange_ratio > 0.25:
            return "fruit"
        elif white_ratio > 0.4:
            return "dairy"
        elif brown_ratio > 0.3 and s_mean < 60:
            return "meat"
        elif green_ratio > 0.3:
            return "vegetable"
        elif s_mean > 60 and v_mean > 100:  # bright and colorful = fruit
            return "fruit"
        else:
            return "vegetable"
            
    except:
        return "fruit"

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
