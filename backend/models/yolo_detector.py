import cv2
import numpy as np
from ultralytics import YOLO
import os
from backend.config import Config

class YOLODetector:
    """YOLOv8-based crowd detection model"""
    
    def __init__(self, model_path=None):
        """Initialize YOLO model"""
        if model_path is None:
            model_path = Config.YOLO_MODEL
        
        self.model = YOLO(model_path)
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        
    def detect_people(self, frame):
        """
        Detect people in a frame
        
        Args:
            frame: Input image/frame (numpy array)
            
        Returns:
            dict: {
                'count': number of people detected,
                'boxes': list of bounding boxes [(x1, y1, x2, y2), ...],
                'confidences': list of confidence scores,
                'centers': list of person centers [(x, y), ...]
            }
        """
        # Run YOLO detection with higher resolution and explicit confidence
        results = self.model(frame, verbose=False, imgsz=1280, conf=self.confidence_threshold)[0]
        
        people_boxes = []
        confidences = []
        centers = []
        
        # Filter for person class (class 0 in COCO dataset)
        for box in results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls == 0 and conf >= self.confidence_threshold:  # Person class
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                people_boxes.append((int(x1), int(y1), int(x2), int(y2)))
                confidences.append(conf)
                
                # Calculate center point
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                centers.append((center_x, center_y))
        
        return {
            'count': len(people_boxes),
            'boxes': people_boxes,
            'confidences': confidences,
            'centers': centers
        }
    
    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes on frame
        
        Args:
            frame: Input frame
            detections: Detection results from detect_people()
            
        Returns:
            Annotated frame
        """
        annotated_frame = frame.copy()
        
        for i, (box, conf) in enumerate(zip(detections['boxes'], detections['confidences'])):
            x1, y1, x2, y2 = box
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw confidence score
            label = f'Person: {conf:.2f}'
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Draw center point
            center = detections['centers'][i]
            cv2.circle(annotated_frame, center, 3, (255, 0, 0), -1)
        
        # Draw total count
        count_text = f'People Count: {detections["count"]}'
        cv2.putText(annotated_frame, count_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return annotated_frame
    
    def calculate_density_grid(self, frame_shape, centers, grid_size=50):
        """
        Calculate crowd density on a grid
        
        Args:
            frame_shape: Shape of the frame (height, width)
            centers: List of person center coordinates
            grid_size: Size of each grid cell in pixels
            
        Returns:
            2D numpy array representing density grid
        """
        height, width = frame_shape[:2]
        grid_h = height // grid_size
        grid_w = width // grid_size
        
        density_grid = np.zeros((grid_h, grid_w), dtype=np.float32)
        
        # Early return if no centers to prevent errors
        if not centers:
            return density_grid
        
        for center_x, center_y in centers:
            grid_x = min(center_x // grid_size, grid_w - 1)
            grid_y = min(center_y // grid_size, grid_h - 1)
            density_grid[grid_y, grid_x] += 1
        
        return density_grid
