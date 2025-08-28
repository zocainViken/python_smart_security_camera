

# detection.py
import cv2
from ultralytics import YOLO
from recognition import FaceRecognitionOpenCV
from config import detection_device

# Charger YOLOv8 nano (CPU)
model = YOLO("src/yolov8n.pt")
model.to(detection_device)

# Initialisation de la reconnaissance
face_recog = FaceRecognitionOpenCV(known_dir="known_faces")

# ------------------- Extraction des personnes -------------------
def yolov8_extract_persons(frame, results, conf_threshold=0.4):
    persons, boxes = [], []
    results_list = results if isinstance(results, list) else [results]

    for r in results_list:
        class_ids = r.boxes.cls.cpu().numpy()
        scores = r.boxes.conf.cpu().numpy()

        for i, cls_id in enumerate(class_ids):
            if cls_id == 0 and scores[i] >= conf_threshold:  # 0 = "person"
                x1, y1, x2, y2 = r.boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                person_img = frame[y1:y2, x1:x2]
                if person_img.size != 0:
                    persons.append(person_img)
                    boxes.append((x1, y1, x2, y2))
    return persons, boxes

# ------------------- Affichage des personnes + reconnaissance -------------------
def yolov8_display_persons(frame, results, conf_threshold=0.4):
    persons, boxes = yolov8_extract_persons(frame, results, conf_threshold)
    annotated_persons = []

    for idx, (person_img, box) in enumerate(zip(persons, boxes)):
        # Reconnaissance directe sur la mini image
        name, conf = face_recog.recognize_face(person_img)
        annotated_person_img = face_recog.annotate_face(person_img, name)

        # Affiche chaque visage reconnu
        cv2.imshow(f"Person {idx}", annotated_person_img)

        annotated_persons.append((annotated_person_img, box, name))
    return annotated_persons

# ------------------- Détection et annotation principale -------------------
def yolov8_detection(frame):
    results_list = model.predict(frame, conf=0.4)
    results = results_list[0]
    annotated_frame = results.plot()

    # Obtenir les mini images annotées et les résultats faciaux
    annotated_persons = yolov8_display_persons(frame, results, conf_threshold=0.4)

    # Annoter le flux principal avec noms
    for _, box, name in annotated_persons:
        x1, y1, x2, y2 = box
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(annotated_frame, name, (x1, y2+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

    cv2.imshow("YOLOv8 Detection", annotated_frame)




import cv2
from ultralytics import YOLO
import torch


class Yolov8Detector:
    def __init__(self, model_path="src/yolov8n.pt", conf=0.4, device=None):
        """
        :param model_path: chemin vers le modèle YOLOv8 (n = nano, s = small, m = medium, etc.)
        :param conf: seuil de confiance
        :param device: "cpu" ou "cuda", si None → auto-détection
        """
        self.model = YOLO(model_path)
        self.conf = conf

        # Choix du device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model.to(self.device)
        print(f"✅ YOLO chargé sur {self.device} avec {model_path}")

    def detect(self, frame, show=True):
        """Détecte les objets sur une frame"""
        results_list = self.model.predict(frame, conf=self.conf, device=self.device)
        results = results_list[0]

        if show:
            annotated_frame = results.plot()
            cv2.imshow("YOLOv8 Detection", annotated_frame)

        return results

    def extract_persons(self, frame, results):
        """Retourne les crops de personnes détectées"""
        persons = []
        class_ids = results.boxes.cls.cpu().numpy()
        scores = results.boxes.conf.cpu().numpy()

        for i, cls_id in enumerate(class_ids):
            if cls_id == 0 and scores[i] >= self.conf:  # 0 = "person"
                x1, y1, x2, y2 = results.boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                person_img = frame[y1:y2, x1:x2]
                persons.append(person_img)
        return persons

    def display_persons(self, frame, results):
        """Affiche chaque personne détectée"""
        persons = self.extract_persons(frame, results)
        for idx, person_img in enumerate(persons):
            cv2.imshow(f"Person {idx}", person_img)
