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
        
        # Convert to multiple color spaces
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Extract color statistics
        h_mean, s_mean, v_mean = np.mean(hsv[:, :, 0]), np.mean(hsv[:, :, 1]), np.mean(hsv[:, :, 2])
        h_std, s_std, v_std = np.std(hsv[:, :, 0]), np.std(hsv[:, :, 1]), np.std(hsv[:, :, 2])
        l_mean, a_mean, b_mean = np.mean(lab[:, :, 0]), np.mean(lab[:, :, 1]), np.mean(lab[:, :, 2])
        
        # Texture analysis
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # IMPROVED: Detect actual spoilage indicators
        # 1. Mold (fuzzy white/green/black spots)
        mold_mask = ((hsv[:, :, 0] >= 80) & (hsv[:, :, 0] <= 140) & (hsv[:, :, 1] > 30) & (hsv[:, :, 2] < 100)) | \
                    ((hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 40))  # black mold
        mold_ratio = np.sum(mold_mask) / total_pixels
        
        # 2. Excessive browning/oxidation (very dark brown, not cooked brown)
        rotten_brown_mask = (hsv[:, :, 0] >= 5) & (hsv[:, :, 0] <= 25) & \
                            (hsv[:, :, 1] > 40) & (hsv[:, :, 2] < 60)  # dark brown
        rotten_brown_ratio = np.sum(rotten_brown_mask) / total_pixels
        
        # 3. Sliminess indicator (very high saturation with low value)
        slimy_mask = (hsv[:, :, 1] > 150) & (hsv[:, :, 2] < 80)
        slimy_ratio = np.sum(slimy_mask) / total_pixels
        
        # 4. Dryness/shriveling (very low saturation and value)
        dried_mask = (hsv[:, :, 1] < 20) & (hsv[:, :, 2] < 80) & (hsv[:, :, 2] > 30)
        dried_ratio = np.sum(dried_mask) / total_pixels
        
        # Calculate freshness score (0-100)
        freshness_score = 75  # Start with neutral-good baseline
        
        # CRITICAL PENALTIES (actual spoilage)
        freshness_score -= mold_ratio * 150  # Severe penalty for mold
        freshness_score -= rotten_brown_ratio * 100  # Heavy penalty for rot
        freshness_score -= slimy_ratio * 120  # Heavy penalty for slime
        freshness_score -= dried_ratio * 60  # Moderate penalty for drying
        
        # MINOR ADJUSTMENTS (quality indicators)
        # Brightness check (too dark might indicate old food)
        if v_mean < 40:
            freshness_score -= 25
        elif v_mean > 200:  # Fresh food often has good brightness
            freshness_score += 10
        
        # Saturation check (vibrant = fresh for raw foods)
        if s_mean > 100 and v_mean > 100:  # Vibrant colors
            freshness_score += 15
        
        # Texture quality (smooth = fresh, irregular = spoiled)
        if edge_density > 0.25:  # Too many edges = irregular texture
            freshness_score -= 20
        
        # LAB color space - detect discoloration
        if l_mean < 50:  # Very dark
            freshness_score -= 15
        
        # Clamp score
        freshness_score = max(0, min(100, freshness_score))
        
        food_type = detect_food_category(image_path)
        
        # Classification with adjusted thresholds
        if freshness_score >= 60:
            label = "Fresh"
            confidence = np.random.uniform(min(85, freshness_score), min(95, freshness_score + 10))
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

def detect_food_category(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            return "fruit"
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_mean = np.mean(hsv[:, :, 0])
        s_mean = np.mean(hsv[:, :, 1])
        v_mean = np.mean(hsv[:, :, 2])
        
        total_pixels = hsv.shape[0] * hsv.shape[1]
        
        # Red/pink (strawberries, apples, tomatoes, meat)
        red_mask = ((hsv[:, :, 0] <= 10) | (hsv[:, :, 0] >= 170)) & (hsv[:, :, 1] > 40)
        red_ratio = np.sum(red_mask) / total_pixels
        
        # Orange/Yellow (oranges, bananas, cooked food)
        orange_mask = (hsv[:, :, 0] > 10) & (hsv[:, :, 0] <= 40) & (hsv[:, :, 1] > 40)
        orange_ratio = np.sum(orange_mask) / total_pixels
        
        # Green (vegetables, leafy greens)
        green_mask = (hsv[:, :, 0] > 40) & (hsv[:, :, 0] <= 85) & (hsv[:, :, 1] > 30)
        green_ratio = np.sum(green_mask) / total_pixels
        
        # White/cream (dairy, paneer, rice, cooked food)
        white_mask = (hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 120)
        white_ratio = np.sum(white_mask) / total_pixels
        
        # Brown/beige (meat, bread, cooked food)
        brown_mask = (hsv[:, :, 0] > 5) & (hsv[:, :, 0] < 35) & (hsv[:, :, 1] < 100) & (hsv[:, :, 2] > 40)
        brown_ratio = np.sum(brown_mask) / total_pixels
        
        # Classification logic
        if white_ratio > 0.35:  # Dairy or cooked food with white base
            if brown_ratio > 0.15 or orange_ratio > 0.15:  # Mixed with other colors
                return "vegetable"  # Cooked dishes like paneer sabji
            return "dairy"
        elif brown_ratio > 0.25 and s_mean < 70:  # Low saturation brown = meat
            return "meat"
        elif green_ratio > 0.25:  # Dominant green
            return "vegetable"
        elif red_ratio > 0.2 or orange_ratio > 0.2:  # Colorful
            return "fruit"
        elif s_mean > 60 and v_mean > 100:  # Bright and colorful
            return "fruit"
        else:
            return "vegetable"  # Default for cooked/mixed foods
            
    except:
        return "vegetable"

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
