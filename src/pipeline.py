import os
import cv2
import yaml
import time
import queue
import random
import datetime
import threading
import numpy as np
from shapely.geometry import Point, Polygon

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from src.challan_pdf import create_official_pdf, sanitize_vehicle_number

class TrafficEnforcementPipeline:
    def __init__(self, config_path):
        # Load configuration settings
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        # Parse camera enforcement FOV zone (retained for safety, though unused for detection boundaries)
        self.fov_poly = None
        if 'zones' in self.config and 'camera_fov_zone' in self.config['zones']:
            try:
                self.fov_poly = Polygon(self.config['zones']['camera_fov_zone'])
            except Exception:
                pass
        
        # Directory parameters
        self.output_dir = "C:\\Users\\Vansh\\gridlock_hackathon\\output"
        self.challan_dir = os.path.join(self.output_dir, "challans")
        self.crop_dir = os.path.join(self.output_dir, "crops")
        os.makedirs(self.challan_dir, exist_ok=True)
        os.makedirs(self.crop_dir, exist_ok=True)
        
        # Multi-threading task queue
        self.violation_queue = queue.Queue()
        self.active = True
        
        # Statistics
        self.total_violations_logged = 0
        self.total_vehicles_counted = 0
        self.compliance_rate = 100.0
        
        # Web dashboard states
        self.violations_list = []
        self.frame_count = 0
        self.track_history = {}
        
        # Start background compiling thread
        self.worker_thread = threading.Thread(target=self._challan_worker, daemon=True)
        self.worker_thread.start()
        
        # Real-time YOLOv8 tracker setup
        self.yolo_model = None
        self.helmet_model = None
        self.real_mode = False

    def draw_corner_brackets(self, img, box, color, thickness=2, length=12):
        x1, y1, x2, y2 = map(int, box)
        # Top-Left
        cv2.line(img, (x1, y1), (x1 + length, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + length), color, thickness)
        # Top-Right
        cv2.line(img, (x2, y1), (x2 - length, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + length), color, thickness)
        # Bottom-Left
        cv2.line(img, (x1, y2), (x1 + length, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - length), color, thickness)
        # Bottom-Right
        cv2.line(img, (x2, y2), (x2 - length, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - length), color, thickness)

    def draw_label(self, img, text, pt, bg_color, text_color=(255, 255, 255), scale=0.35, thickness=1):
        x, y = map(int, pt)
        (w, h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
        y_start = max(y, h + 10)
        cv2.rectangle(img, (x, y_start - h - 6), (x + w + 8, y_start + baseline - 2), bg_color, -1)
        cv2.putText(img, text, (x + 4, y_start - 3), cv2.FONT_HERSHEY_SIMPLEX, scale, text_color, thickness, cv2.LINE_AA)

    def analyze_helmet_crop(self, img, x1, y1, x2, y2):
        """
        Refined Visual Helmet Verification Engine.
        Analyzes the head crop for round shapes (Hough circles) and color/edge saturation profiles
        typical of helmets (smooth, solid colored structures) vs hair (high entropy, dark, rough textures).
        """
        # Crop head area safely
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 5 or y2 - y1 < 5:
            return 0.5 # Neutral confidence fallback
            
        crop = img[y1:y2, x1:x2]
        
        # Convert to HSV and Grayscale
        try:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        except Exception:
            return 0.5
            
        # Color distribution check
        saturation_avg = np.mean(hsv[:,:,1])
        
        # Texture check: calculate edge entropy using Canny filter
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.mean(edges > 0)
        
        # Shape check: Hough circle detector for circular helmet boundaries
        circles_detected = 0
        try:
            resized_gray = cv2.resize(gray, (40, 40))
            circles = cv2.HoughCircles(
                resized_gray, 
                cv2.HOUGH_GRADIENT, 
                dp=1.2, 
                minDist=15, 
                param1=50, 
                param2=25, 
                minRadius=10, 
                maxRadius=20
            )
            if circles is not None:
                circles_detected = len(circles[0])
        except Exception:
            pass
            
        # Combine structural indicators to compute a visual helmet compliance metric
        score = 0.5
        if circles_detected > 0:
            score += 0.25
        if edge_density < 0.15:
            score += 0.15 # Smooth helmet surface
        else:
            score -= 0.1 # Textured hair
            
        if saturation_avg > 40:
            score += 0.1 # Solid color helmet
            
        return float(np.clip(score, 0.0, 1.0))
        
    def init_yolo(self):
        if YOLO is not None:
            try:
                helmet_weights = "C:\\Users\\Vansh\\gridlock_hackathon\\helmet_best.pt"
                # If custom-trained 5-class model exists, load it directly as the primary tracker
                if os.path.exists(helmet_weights):
                    self.yolo_model = YOLO(helmet_weights)
                    self.helmet_model = self.yolo_model
                    print(f"[PIPELINE] Custom trained model loaded from '{helmet_weights}' as primary detector/tracker.")
                else:
                    weights = self.config['models']['yolo_weights']
                    self.yolo_model = YOLO(weights)
                    self.helmet_model = None
                    print(f"[PIPELINE] Standard YOLOv8 tracker loaded from '{weights}' successfully.")
                self.real_mode = True
            except Exception as e:
                print(f"[PIPELINE ERROR] YOLO loader failed: {e}. Defaulting to mock simulation.")
                self.real_mode = False
        else:
            print("[PIPELINE] Ultralytics module missing. Defaulting to mock simulation.")
            self.real_mode = False

    def enqueue_violation(self, track_id, vehicle_type, violation_type, frame, bbox_crop=None, mock_plate=""):
        """
        Saves infraction crop and appends transaction records to compiling queue.
        """
        timestamp = datetime.datetime.now()
        crop_filename = f"track_{track_id}_{violation_type.replace(' ', '_').replace('-', '_')}.jpg"
        crop_path = os.path.join(self.crop_dir, crop_filename)
        
        # Generate target bbox image
        if bbox_crop is not None and bbox_crop.size > 0:
            cv2.imwrite(crop_path, bbox_crop)
        else:
            # Generate mock plate image if no active video capture crop exists
            self._generate_mock_plate_image(mock_plate, crop_path)
            
        event = {
            'track_id': track_id,
            'vehicle_type': vehicle_type,
            'violation_type': violation_type,
            'crop_path': crop_path,
            'mock_plate': mock_plate,
            'timestamp': timestamp,
            'location': self.config['location']['junction_name']
        }
        self.violation_queue.put(event)
        self.total_violations_logged += 1
        print(f"[PIPELINE] Enqueued helmet violation: Track {track_id} | Plate: {mock_plate}")

    def _generate_mock_plate_image(self, plate_text, output_path):
        """
        Creates a high-contrast crop mockup of an IND license plate.
        """
        img = np.ones((80, 260, 3), dtype=np.uint8) * 255
        cv2.rectangle(img, (2, 2), (257, 77), (10, 37, 64), 3) # Brand Navy border
        # IND stamp
        cv2.rectangle(img, (5, 5), (35, 75), (0, 0, 255), -1)
        cv2.putText(img, "IND", (8, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        # License text
        cv2.putText(img, plate_text, (45, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.imwrite(output_path, img)

    def _challan_worker(self):
        """
        Pulls infractions, compiles official ReportLab notice,
        and saves records to the dashboard metadata list.
        """
        while self.active:
            try:
                try:
                    event = self.violation_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                if event is None:
                    break
                    
                track_id = event['track_id']
                v_type = event['violation_type']
                crop_path = event['crop_path']
                mock_plate = event['mock_plate']
                location = event['location']
                timestamp = event['timestamp']
                
                # Check fine directory configuration details
                fine_amount = 500
                section_code = "Sec 129 r/w 177 MVA"
                
                # Create unique Challan ID
                challan_no = f"TRF-{timestamp.strftime('%Y%m%d')}-{track_id}-{random.randint(100, 999)}"
                pdf_filename = f"{challan_no}_No_Helmet.pdf"
                pdf_path = os.path.join(self.challan_dir, pdf_filename)
                
                # Compile PDF Notice
                plate_text, challan_id = create_official_pdf(
                    vehicle_no=mock_plate,
                    violation_reason=v_type,
                    track_id=track_id,
                    location=location,
                    output_path=pdf_path
                )
                
                # Save metadata for web dashboard API
                self.violations_list.append({
                    'challan_no': challan_id,
                    'track_id': int(track_id),
                    'license_plate': plate_text,
                    'violation_type': v_type,
                    'fine_amount': fine_amount,
                    'section_code': section_code,
                    'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    'pdf_url': f"/api/files/challans/{pdf_filename}",
                    'crop_url': f"/api/files/crops/{os.path.basename(crop_path)}",
                    'status': 'PENDING'
                })
                
                print(f"[CHALLAN ENGINE] PDF notice compiled: {pdf_path} | Plate: {plate_text}")
                self.violation_queue.task_done()
                
            except Exception as e:
                print(f"[WORKER ERROR] Notice generation failed: {e}")

    def generate_frames(self):
        """
        Yields MJPEG processed video streams.
        Checks for root CCTV stream 'dummy.mp4'. If not found, launches
        the helmet compliance visual simulation.
        """
        video_path = "C:\\Users\\Vansh\\gridlock_hackathon\\dummy.mp4"
        processed_violations = set()
        
        # Real CCTV stream mode
        if os.path.exists(video_path):
            print(f"[PIPELINE WEB] CCTV footage detected at '{video_path}'. Instantiating YOLO tracker...")
            self.init_yolo()
            if self.real_mode and self.yolo_model is not None:
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if not fps or fps < 1:
                        fps = 30.0
                    delay = 1.0 / fps
                    
                    while cap.isOpened() and self.active:
                        loop_start = time.time()
                        self.frame_count += 1
                        ret, frame = cap.read()
                        if not ret:
                            # Loop CCTV video feed
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                            
                        frame_resized = cv2.resize(frame, (1280, 720))
                        
                        # YOLO Inference
                        results = self.yolo_model.track(
                            source=frame_resized,
                            persist=True,
                            conf=self.config['tracking']['conf_threshold'],
                            iou=self.config['tracking']['iou_threshold'],
                            tracker=self.config['tracking'].get('tracker_type', 'bytetrack.yaml'),
                            verbose=False
                        )
                        
                        # Detect if we are running the custom 5-class model
                        is_custom_model = (len(self.yolo_model.names) == 5)
                        
                        # Custom helmet validation model inference (only needed for 2-model mode)
                        helmet_results = None
                        if not is_custom_model and self.helmet_model is not None:
                            try:
                                helmet_results = self.helmet_model.predict(
                                    source=frame_resized,
                                    conf=0.12, # Low threshold for distant riders
                                    verbose=False
                                )
                            except Exception as e:
                                print(f"[PIPELINE ERROR] Helmet validation inference failed: {e}")
                        
                        # Process detections
                        if results and results[0].boxes:
                            # Safely extract boxes, classes, confidences and track IDs
                            boxes = results[0].boxes.xyxy.cpu().numpy()
                            clss = results[0].boxes.cls.cpu().numpy().astype(int)
                            confs = results[0].boxes.conf.cpu().numpy()
                            names = self.yolo_model.names
                            
                            if results[0].boxes.id is not None:
                                ids = results[0].boxes.id.cpu().numpy().astype(int)
                            else:
                                ids = [None] * len(boxes)
                                
                            motorcycles = []
                            persons = []
                            helmets_compliant = []
                            helmets_violating = []
                            
                            if is_custom_model:
                                # Custom model classes:
                                # 0: numberPlate, 1: faceWithNoHelmet, 2: faceWithGoodHelmet, 3: faceWithBadHelmet, 4: rider
                                for box, track_id, cls, conf_score in zip(boxes, ids, clss, confs):
                                    if cls == 4: # rider
                                        # Map rider to motorcycles list to reuse track and challan pipeline
                                        motorcycles.append((box, track_id))
                                    elif cls == 2: # faceWithGoodHelmet
                                        helmets_compliant.append((box, conf_score))
                                    elif cls in (1, 3): # faceWithNoHelmet, faceWithBadHelmet
                                        helmets_violating.append((box, conf_score))
                            else:
                                # Standard COCO model classes
                                for box, track_id, cls in zip(boxes, ids, clss):
                                    class_name = names.get(cls, '')
                                    if class_name == 'motorcycle':
                                        motorcycles.append((box, track_id))
                                    elif class_name == 'person':
                                        persons.append(box)
                                        
                            for m_box, track_id in motorcycles:
                                if track_id is None:
                                    continue
                                track_id = int(track_id)
                                    
                                x1, y1, x2, y2 = map(int, m_box)
                                cx = (x1 + x2) // 2
                                cy = y2
                                
                                self.total_vehicles_counted = max(self.total_vehicles_counted, track_id)
                                
                                # Update trajectory trail history
                                if track_id not in self.track_history:
                                    self.track_history[track_id] = []
                                self.track_history[track_id].append((cx, cy))
                                self.track_history[track_id] = self.track_history[track_id][-30:]
                                
                                # Search for overlapping helmet/head detection
                                is_compliant = True
                                conf = 90.0
                                detected_head_box = None
                                
                                if is_custom_model:
                                    # Search for overlapping helmet box in custom model detections
                                    best_h_conf = 0.0
                                    
                                    # Violating helmet detections take precedence for safety enforcement
                                    for h_box, h_conf in helmets_violating:
                                        hx1_det, hy1_det, hx2_det, hy2_det = map(int, h_box)
                                        overlap_x1 = max(x1, hx1_det)
                                        overlap_x2 = min(x2, hx2_det)
                                        if (overlap_x2 > overlap_x1) and (hy1_det >= y1 - 40) and (hy2_det <= y1 + int((y2 - y1) * 0.7)):
                                            x_overlap = (overlap_x2 - overlap_x1) / max(1, hx2_det - hx1_det)
                                            if x_overlap > 0.3:
                                                if h_conf > best_h_conf:
                                                    best_h_conf = h_conf
                                                    is_compliant = False
                                                    detected_head_box = (hx1_det, hy1_det, hx2_det, hy2_det)
                                                    conf = round(float(h_conf) * 100, 1)
                                                    
                                    # If no violation box is found, check for compliant helmet box
                                    if detected_head_box is None:
                                        for h_box, h_conf in helmets_compliant:
                                            hx1_det, hy1_det, hx2_det, hy2_det = map(int, h_box)
                                            overlap_x1 = max(x1, hx1_det)
                                            overlap_x2 = min(x2, hx2_det)
                                            if (overlap_x2 > overlap_x1) and (hy1_det >= y1 - 40) and (hy2_det <= y1 + int((y2 - y1) * 0.7)):
                                                x_overlap = (overlap_x2 - overlap_x1) / max(1, hx2_det - hx1_det)
                                                if x_overlap > 0.3:
                                                    if h_conf > best_h_conf:
                                                        best_h_conf = h_conf
                                                        is_compliant = True
                                                        detected_head_box = (hx1_det, hy1_det, hx2_det, hy2_det)
                                                        conf = round(float(h_conf) * 100, 1)
                                                        
                                else:
                                    # Fallback 2-model inference overlap logic
                                    if helmet_results and helmet_results[0].boxes is not None:
                                        h_boxes = helmet_results[0].boxes.xyxy.cpu().numpy()
                                        h_clss = helmet_results[0].boxes.cls.cpu().numpy().astype(int)
                                        h_confs = helmet_results[0].boxes.conf.cpu().numpy()
                                        
                                        best_h_conf = 0.0
                                        for h_box, h_cls, h_conf in zip(h_boxes, h_clss, h_confs):
                                            hx1_det, hy1_det, hx2_det, hy2_det = map(int, h_box)
                                            overlap_x1 = max(x1, hx1_det)
                                            overlap_x2 = min(x2, hx2_det)
                                            if (overlap_x2 > overlap_x1) and (hy1_det >= y1 - 30) and (hy2_det <= y1 + int((y2 - y1) * 0.6)):
                                                x_overlap = (overlap_x2 - overlap_x1) / max(1, hx2_det - hx1_det)
                                                if x_overlap > 0.35:
                                                    if h_conf > best_h_conf:
                                                        best_h_conf = h_conf
                                                        detected_head_box = (hx1_det, hy1_det, hx2_det, hy2_det)
                                                        if len(self.helmet_model.names) == 5:
                                                            if h_cls == 2: # faceWithGoodHelmet
                                                                is_compliant = True
                                                            elif h_cls in (1, 3): # faceWithNoHelmet, faceWithBadHelmet
                                                                is_compliant = False
                                                            else:
                                                                continue
                                                        else:
                                                            if h_cls == 0:
                                                                is_compliant = True
                                                            else:
                                                                is_compliant = False
                                                        conf = round(float(h_conf) * 100, 1)
                                                    
                                if detected_head_box is not None:
                                    hx1, hy1, hx2, hy2 = detected_head_box
                                else:
                                    # Fallback to top 25% of the motorcycle/rider box
                                    hx1 = max(x1, cx - int((x2 - x1) * 0.18))
                                    hx2 = min(x2, cx + int((x2 - x1) * 0.18))
                                    hy1 = max(0, y1 - 8)
                                    hy2 = y1 + int((y2 - y1) * 0.25)
                                    
                                    # Run secondary heuristic verification on the head crop area
                                    heuristics_score = self.analyze_helmet_crop(frame_resized, hx1, hy1, hx2, hy2)
                                    if heuristics_score >= 0.52:
                                        is_compliant = True
                                        conf = round(heuristics_score * 100, 1)
                                    else:
                                        is_compliant = False
                                        conf = round((1.0 - heuristics_score) * 100, 1)
                                    
                                # Ensure bounds are valid
                                hx1, hx2 = min(hx1, hx2), max(hx1, hx2)
                                hy1, hy2 = min(hy1, hy2), max(hy1, hy2)
                                if hx2 - hx1 < 4:
                                    hx1, hx2 = cx - 12, cx + 12
                                if hy2 - hy1 < 4:
                                    hy1, hy2 = y1 - 8, y1 + 25
                                    
                                # Set color scheme based on compliance
                                if is_compliant:
                                    box_color = (34, 197, 94) # Green
                                    h_label = f"HELMET [Conf: {conf}%]"
                                else:
                                    box_color = (75, 75, 255) # Bright Accent Red
                                    h_label = f"NO HELMET [Conf: {conf}%]"
                                    
                                # Draw glowing trajectory trail
                                points = self.track_history[track_id]
                                if len(points) > 1:
                                    for idx in range(len(points) - 1):
                                        pt1 = points[idx]
                                        pt2 = points[idx + 1]
                                        alpha_ratio = (idx + 1) / len(points)
                                        # Fade trail color from grey/white to state color
                                        color_val = (
                                            int(box_color[0] * alpha_ratio + 100 * (1 - alpha_ratio)),
                                            int(box_color[1] * alpha_ratio + 100 * (1 - alpha_ratio)),
                                            int(box_color[2] * alpha_ratio + 100 * (1 - alpha_ratio))
                                        )
                                        cv2.line(frame_resized, pt1, pt2, color_val, 2)
                                        
                                # Draw tracked entity bounding box and corner brackets
                                label_text = f"RIDER [ID:{track_id}]" if is_custom_model else f"MOTORCYCLE [ID:{track_id}]"
                                cv2.rectangle(frame_resized, (x1, y1), (x2, y2), (250, 204, 21), 1)
                                self.draw_corner_brackets(frame_resized, (x1, y1, x2, y2), (250, 204, 21), thickness=2, length=12)
                                self.draw_label(frame_resized, label_text, (x1, y1 - 4), (250, 204, 21), (0, 0, 0), scale=0.35, thickness=1)
                                
                                # Draw Head Rider compliance box and corners
                                cv2.rectangle(frame_resized, (hx1, hy1), (hx2, hy2), box_color, 1)
                                self.draw_corner_brackets(frame_resized, (hx1, hy1, hx2, hy2), box_color, thickness=2, length=8)
                                self.draw_label(frame_resized, h_label, (hx1, hy1 - 4), box_color, (255, 255, 255), scale=0.32, thickness=1)
                                
                                # Enqueue violation once per track
                                if not is_compliant:
                                    event_key = f"{track_id}_no_helmet"
                                    if event_key not in processed_violations:
                                        processed_violations.add(event_key)
                                        crop = frame_resized[max(0, y1):min(720, y2), max(0, x1):min(1280, x2)]
                                        mock_p = f"KA-51-HL-{1000 + track_id}"
                                        self.enqueue_violation(
                                            track_id=track_id,
                                            vehicle_type="rider" if is_custom_model else "motorcycle",
                                            violation_type="No Helmet",
                                            frame=frame_resized,
                                            bbox_crop=crop,
                                            mock_plate=mock_p
                                        )
                                        
                        # Calculate compliance rate
                        violators_set = {int(k.split('_')[0]) for k in processed_violations}
                        total_scanned = max(1, self.total_vehicles_counted)
                        violators_count = len(violators_set)
                        self.compliance_rate = round(((total_scanned - violators_count) / total_scanned) * 100, 1)
                        
                        self.draw_overlay_ui(frame_resized)
                        
                        ret, jpeg = cv2.imencode('.jpg', frame_resized)
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                        
                        elapsed = time.time() - loop_start
                        time.sleep(max(0.001, delay - elapsed))
                    cap.release()
                    return
            print("[PIPELINE] YOLO module failed. Booting Trafficly simulation...")
            
        # Helmet compliance radar simulation loop
        sim_motorcycles = [
            {'id': 1, 'x': 320.0, 'y': 80.0, 'speed': 5.5, 'color': (56, 189, 248), 'plate': 'KA-03-HL-1024', 'compliant': True, 'violations': set()},
            {'id': 2, 'x': 650.0, 'y': -150.0, 'speed': 6.0, 'color': (74, 222, 128), 'plate': 'KA-51-ER-8890', 'compliant': True, 'violations': set()},
            {'id': 3, 'x': 950.0, 'y': -300.0, 'speed': 6.5, 'color': (239, 68, 68), 'plate': 'UNKNOWN', 'compliant': False, 'violations': set()},
            {'id': 4, 'x': 345.0, 'y': -450.0, 'speed': 5.8, 'color': (167, 139, 250), 'plate': 'MH-12-PQ-9912', 'compliant': True, 'violations': set()},
            {'id': 5, 'x': 680.0, 'y': -600.0, 'speed': 7.0, 'color': (244, 63, 94), 'plate': 'UNKNOWN', 'compliant': False, 'violations': set()},
            {'id': 6, 'x': 980.0, 'y': -750.0, 'speed': 6.2, 'color': (14, 165, 233), 'plate': 'KA-04-MK-5120', 'compliant': True, 'violations': set()}
        ]
        
        self.frame_count = 0
        fps = 30
        delay = 1.0 / fps
        
        while self.active:
            loop_start = time.time()
            self.frame_count += 1
            
            # Draw slate highway
            frame = np.ones((720, 1280, 3), dtype=np.uint8) * 30
            cv2.rectangle(frame, (180, 0), (1120, 720), (50, 50, 50), -1)
            
            # Dashed lane markers
            for y_dashed in range(0, 720, 40):
                if (y_dashed // 20) % 2 == 0:
                    cv2.line(frame, (480, y_dashed), (480, y_dashed+20), (255, 255, 255), 2)
                    cv2.line(frame, (800, y_dashed), (800, y_dashed+20), (255, 255, 255), 2)
                    
            # Update and Draw Simulated Motorcycles
            for m in sim_motorcycles:
                m['y'] += m['speed']
                
                # Reset motorcycle position off screen
                if m['y'] > 750:
                    m['y'] = -random.randint(150, 450)
                    m['violations'].clear()
                    # Randomize plate and helmet state for diversity
                    m['compliant'] = random.random() > 0.35 # 65% compliance rate
                    m['plate'] = f"KA-51-HB-{random.randint(1000, 9999)}" if m['compliant'] else "UNKNOWN"
                    
                # Track counts
                self.total_vehicles_counted = max(self.total_vehicles_counted, m['id'])
                    
                # Trigger violation check once on entire frame (when vehicle is visible on screen, e.g. y >= 150)
                if m['y'] >= 150:
                    if not m['compliant'] and "No Helmet" not in m['violations']:
                        m['violations'].add("No Helmet")
                        self.enqueue_violation(
                            track_id=m['id'],
                            vehicle_type="motorcycle",
                            violation_type="No Helmet",
                            frame=frame,
                            bbox_crop=None,
                            mock_plate=m['plate']
                        )
                        
                mx, my = int(m['x']), int(m['y'])
                
                # Update trajectory trail history for simulated vehicles
                if m['id'] not in self.track_history:
                    self.track_history[m['id']] = []
                self.track_history[m['id']].append((mx, my))
                self.track_history[m['id']] = self.track_history[m['id']][-30:]
                
                is_compliant = m['compliant']
                local_rng = random.Random(m['id'])
                conf = round(local_rng.uniform(93.4, 98.9), 1) if is_compliant else round(local_rng.uniform(88.2, 94.6), 1)
                
                if is_compliant:
                    border_color = (34, 197, 94) # Green
                    h_label = f"HELMET [Conf: {conf}%]"
                else:
                    border_color = (75, 75, 255) # Red
                    h_label = f"NO HELMET [Conf: {conf}%]"
                    
                # Draw glowing trajectory trail
                points = self.track_history[m['id']]
                if len(points) > 1:
                    for idx in range(len(points) - 1):
                        pt1 = points[idx]
                        pt2 = points[idx + 1]
                        alpha_ratio = (idx + 1) / len(points)
                        color_val = (
                            int(border_color[0] * alpha_ratio + 100 * (1 - alpha_ratio)),
                            int(border_color[1] * alpha_ratio + 100 * (1 - alpha_ratio)),
                            int(border_color[2] * alpha_ratio + 100 * (1 - alpha_ratio))
                        )
                        cv2.line(frame, pt1, pt2, color_val, 2)
                        
                w, h = 30, 60
                bx1, by1, bx2, by2 = mx - w//2, my - h, mx + w//2, my
                
                # Draw motorcycle box and corner brackets
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (250, 204, 21), 1)
                self.draw_corner_brackets(frame, (bx1, by1, bx2, by2), (250, 204, 21), thickness=2, length=12)
                self.draw_label(frame, f"MOTORCYCLE [ID:{m['id']}]", (bx1, by1 - 4), (250, 204, 21), (0, 0, 0), scale=0.35, thickness=1)
                
                # Draw head rider compliance box and corner brackets
                hx1, hy1, hx2, hy2 = mx - 10, by1 - 10, mx + 10, by1 + 10
                cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), border_color, 1)
                self.draw_corner_brackets(frame, (hx1, hy1, hx2, hy2), border_color, thickness=2, length=8)
                self.draw_label(frame, h_label, (hx1, hy1 - 4), border_color, (255, 255, 255), scale=0.32, thickness=1)
                
                # Render license plate box
                cv2.rectangle(frame, (mx - 25, by2 - 12), (mx + 25, by2 - 2), (255, 255, 255), -1)
                p_text = m['plate'] if m['plate'] != 'UNKNOWN' else f"KA-MOCK-{m['id']}"
                cv2.putText(frame, p_text[:10], (mx - 22, by2 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1, cv2.LINE_AA)
                
            # Compute dynamic compliance rate percentage
            tot_scanned = max(1, self.total_vehicles_counted)
            active_violators = self.total_violations_logged
            self.compliance_rate = round(max(0.0, ((tot_scanned - active_violators) / tot_scanned) * 100), 1)
            
            self.draw_overlay_ui(frame)
            
            # Encode frame to JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                
            elapsed = time.time() - loop_start
            time.sleep(max(0.001, delay - elapsed))

    def draw_overlay_ui(self, frame):
        """
        Draws the telemetry HUD overlay.
        """
        # Draw frame target corners for the entire camera frame scope
        fh, fw = frame.shape[:2]
        c_len = 30
        c_thick = 3
        hud_color = (251, 146, 60) # Amber (BGR: 60, 146, 251)
        # Top-Left
        cv2.line(frame, (10, 10), (10 + c_len, 10), hud_color, c_thick)
        cv2.line(frame, (10, 10), (10, 10 + c_len), hud_color, c_thick)
        # Top-Right
        cv2.line(frame, (fw - 10, 10), (fw - 10 - c_len, 10), hud_color, c_thick)
        cv2.line(frame, (fw - 10, 10), (fw - 10, 10 + c_len), hud_color, c_thick)
        # Bottom-Left
        cv2.line(frame, (10, fh - 10), (10 + c_len, fh - 10), hud_color, c_thick)
        cv2.line(frame, (10, fh - 10), (10, fh - 10 - c_len), hud_color, c_thick)
        # Bottom-Right
        cv2.line(frame, (fw - 10, fh - 10), (fw - 10 - c_len, fh - 10), hud_color, c_thick)
        cv2.line(frame, (fw - 10, fh - 10), (fw - 10, fh - 10 - c_len), hud_color, c_thick)
        
        # Telemetry Control Dashboard (Top Left)
        cv2.rectangle(frame, (20, 20), (400, 185), (10, 37, 64), -1) # Trafficly Navy blue
        cv2.rectangle(frame, (20, 20), (400, 185), (51, 65, 85), 2)
        
        # Labels
        cv2.putText(frame, "TRAFFICLY ENFORCEMENT ENGINE v2.5", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (75, 75, 255), 2, cv2.LINE_AA) # Red accent (BGR: 75, 75, 255)
        cv2.line(frame, (30, 48), (390, 48), (71, 85, 105), 1)
        
        loc_str = f"Junction: {self.config['location']['junction_name'][:25]}"
        cv2.putText(frame, loc_str, (30, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (241, 245, 249), 1, cv2.LINE_AA)
        
        mode_str = f"Radar Mode: HELMET RADAR COMPLIANCE"
        cv2.putText(frame, mode_str, (30, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (56, 189, 248), 1, cv2.LINE_AA)
        
        cam_str = f"Camera Stream: {'CCTV dummy.mp4' if self.real_mode else 'Simulated Feed'}"
        cv2.putText(frame, cam_str, (30, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (241, 245, 249), 1, cv2.LINE_AA)
        
        count_str = f"Riders Logged: {self.total_vehicles_counted}"
        cv2.putText(frame, count_str, (30, 133), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (241, 245, 249), 1, cv2.LINE_AA)
        
        challan_str = f"Infractions Captured: {self.total_violations_logged}"
        cv2.putText(frame, challan_str, (30, 153), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (75, 75, 255), 2, cv2.LINE_AA)
        
        # Draw Compliance Rate metrics
        comp_color = (34, 197, 94) if self.compliance_rate >= 70.0 else (75, 75, 255)
        rate_str = f"Safety Compliance: {self.compliance_rate}%"
        cv2.putText(frame, rate_str, (30, 173), cv2.FONT_HERSHEY_SIMPLEX, 0.45, comp_color, 2, cv2.LINE_AA)
        
        # Flashes warning notice if violation occurs
        if self.total_violations_logged > 0:
            if (self.frame_count // 10) % 2 == 0:
                cv2.putText(frame, "RADAR INFRACTION ACTIVE", (480, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

    def run_simulated_pipeline(self):
        """
        Runs the simulation locally and shows the visual feed using OpenCV window.
        """
        print("[PIPELINE] Starting local simulated enforcement pipeline...")
        self.real_mode = False
        try:
            for part in self.generate_frames():
                if not self.active:
                    break
                marker = b'\r\n\r\n'
                idx = part.find(marker)
                if idx != -1:
                    jpeg_bytes = part[idx + len(marker): -2]
                    nparr = np.frombuffer(jpeg_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow("Trafficly - Local Simulated Compliance Feed", frame)
                        if cv2.waitKey(1) & 0xFF == 27: # ESC key
                            break
        except KeyboardInterrupt:
            pass
        finally:
            cv2.destroyAllWindows()

    def run_real_pipeline(self, source):
        """
        Runs the real camera/video pipeline locally and shows the visual feed using OpenCV window.
        """
        print(f"[PIPELINE] Starting local real enforcement pipeline with source: {source}...")
        self.init_yolo()
        if not self.real_mode:
            return False
        try:
            for part in self.generate_frames():
                if not self.active:
                    break
                marker = b'\r\n\r\n'
                idx = part.find(marker)
                if idx != -1:
                    jpeg_bytes = part[idx + len(marker): -2]
                    nparr = np.frombuffer(jpeg_bytes, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        cv2.imshow("Trafficly - Local Real Compliance Feed", frame)
                        if cv2.waitKey(1) & 0xFF == 27: # ESC key
                            break
            return True
        except Exception as e:
            print(f"[PIPELINE ERROR] Local real run failed: {e}")
            return False
        finally:
            cv2.destroyAllWindows()

    def shutdown(self):
        self.active = False
        self.violation_queue.put(None)
        self.worker_thread.join()
        print("[PIPELINE] Pipeline worker thread shutdown.")
