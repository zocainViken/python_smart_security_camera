# recognition.py
import cv2
import numpy as np
from pathlib import Path
import os
import cv2
import numpy as np
from pathlib import Path
import os

class FaceRecognitionOpenCV:
    def __init__(self, known_dir="known_faces", threshold=80):
        """
        known_dir: dossier contenant les sous-dossiers par personne
        threshold: seuil de confiance pour LBPH (plus petit = plus strict)
        """
        self.threshold = threshold
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.labels = {}
        self.train_recognizer(known_dir)

    def train_recognizer(self, known_dir):
        images, labels = [], []
        label_id = 0

        known_path = Path(known_dir)
        if not known_path.exists():
            raise ValueError(f"[ERROR] Dossier {known_dir} introuvable.")

        for folder in known_path.iterdir():
            if not folder.is_dir():
                continue  

            person_name = folder.name  # nom du dossier = label (ex: "moi")
            files = []
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                files.extend(folder.glob(ext))

            if not files:
                print(f"[WARN] Aucun fichier image trouvé pour {person_name}, ignoré.")
                continue

            for file_ in files:
                img = cv2.imread(str(file_))
                if img is None:
                    continue
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (200, 200))  # <-- Ajoute cette ligne
                images.append(gray)
                labels.append(label_id)

            self.labels[label_id] = person_name
            label_id += 1

            

        if not images:
            raise ValueError(f"No valid images found in {known_dir}")

        
        self.recognizer.train(images, np.array(labels))
        self.recognizer.save("lbph_model.yml")
        print(f"[INFO] {len(self.labels)} personnes entraînées: {list(self.labels.values())}")

    def recognize_face(self, face_img):
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (200, 200))  # <-- standardiser la taille
        label, confidence = self.recognizer.predict(gray)
        if confidence <= self.threshold:
            name = self.labels[label]
        else:
            name = "Unknown"
        return name, confidence

    def recognize_frame(self, frame, faces):
        """
        faces: liste de tuples (x1, y1, x2, y2)
        Retourne: liste de tuples ((x1, y1, x2, y2), name)
        """
        results = []
        for (x1, y1, x2, y2) in faces:
            person_img = frame[y1:y2, x1:x2]
            if person_img.size == 0:
                continue
            name, conf = self.recognize_face(person_img)
            results.append(((x1, y1, x2, y2), name))
        return results

    def annotate_frame(self, frame, results):
        for (x1, y1, x2, y2), name in results:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, name, (x1, y2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return frame

    def annotate_face(self, face_img, name):
        """
        Dessine juste un rectangle et un nom sur une image de visage entière.
        """
        h, w = face_img.shape[:2]
        cv2.rectangle(face_img, (0, 0), (w-1, h-1), (0, 255, 0), 2)
        cv2.putText(face_img, name, (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return face_img