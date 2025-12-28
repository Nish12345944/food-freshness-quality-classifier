import cv2
import os
import time
from datetime import datetime

def capture_image(save_path="static/uploads"):
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise Exception("Could not open camera. Please check if camera is connected.")
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        for _ in range(5):
            ret, frame = cap.read()
            if not ret:
                break
            time.sleep(0.1)
        
        ret, frame = cap.read()
        if not ret:
            raise Exception("Failed to capture image from camera")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_{timestamp}.jpg"
        filepath = os.path.join(save_path, filename)
        
        os.makedirs(save_path, exist_ok=True)
        
        success = cv2.imwrite(filepath, frame)
        if not success:
            raise Exception("Failed to save captured image")
        
        cap.release()
        return filepath, filename
        
    except Exception as e:
        if 'cap' in locals():
            cap.release()
        raise e

def check_camera_availability():
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret
        return False
    except:
        return False
