# core/detection.py
import cv2
from ultralytics import YOLO
import numpy as np

class ADASDetector:
    def __init__(self, model_name='yolov8n.pt', threshold=0.5):
        self.model = YOLO(model_name)
        self.threshold = threshold
        self.prev_areas = {}  # To track object growth: {track_id: last_area}

    def process_frame(self, frame):
        """
        Processes a single frame, detects objects, and calculates danger levels.
        Returns: (processed_frame, alerts)
        """
        results = self.model.track(frame, persist=True) # Using tracking
        alerts = []
        
        # Copy frame to draw on
        annotated_frame = frame.copy()
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()

            for box, track_id, cls, conf in zip(boxes, track_ids, classes, confidences):
                if conf < self.threshold:
                    continue

                x1, y1, x2, y2 = box
                label = self.model.names[int(cls)]
                area = (x2 - x1) * (y2 - y1)
                
                # Draw Bounding Box
                color = (0, 255, 0) # Green by default
                
                # Logic: Check if area is increasing (Object getting closer)
                if track_id in self.prev_areas:
                    prev_area = self.prev_areas[track_id]
                    if area > prev_area * 1.1: # 10% increase in area
                        color = (0, 0, 255) # RED for Danger
                        alerts.append({
                            'id': int(track_id),
                            'type': label,
                            'status': 'DANGER: Approaching'
                        })
                
                self.prev_areas[track_id] = area
                
                # Visuals
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(annotated_frame, f"{label} {conf:.2f}", (int(x1), int(y1)-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return annotated_frame, alerts