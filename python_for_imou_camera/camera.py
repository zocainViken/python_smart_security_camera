# camera.py

import cv2
import time
import uuid
import hashlib
import requests
import subprocess
import numpy as np
from config import AppId, AppSecret, BASE_URL  
from detection import yolov8_detection


# ------------------- Fonctions utilitaires -------------------
def make_sign(ts, nonce, secret):
    raw = f"time:{ts},nonce:{nonce},appSecret:{secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def post(endpoint, payload):
    url = f"{BASE_URL}/{endpoint}"
    r = requests.post(url, json=payload)
    r.raise_for_status()
    return r.json()

# ------------------- Authentification -------------------
def get_access_token():
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {}
    }
    data = post("accessToken", payload)
    if data["result"]["code"] == "0":
        return data["result"]["data"]["accessToken"]
    raise Exception(f"Login failed: {data}")

# ------------------- Lister devices -------------------
def get_live_list(token, query_range="1-10"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {"token": token, "queryRange": query_range}
    }
    data = post("liveList", payload)
    if data["result"]["code"] == "0":
        return data["result"]["data"]["lives"]
    raise Exception(f"liveList failed: {data}")

# ------------------- Gestion RTMP -------------------
def create_rtmp(token, device_id, channel_id="0"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {"deviceId": device_id, "channelId": channel_id, "token": token}
    }
    data = post("createDeviceRtmpLive", payload)
    code = data["result"]["code"]
    if code == "0":
        return data["result"]["data"]["rtmp"]
    elif code == "LV1001":  # Flux RTMP existe déjà
        return query_rtmp(token, device_id, channel_id)
    else:
        raise Exception(f"createDeviceRtmpLive failed: {data}")

def query_rtmp(token, device_id, channel_id="0"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {"deviceId": device_id, "channelId": channel_id, "token": token}
    }
    data = post("queryDeviceRtmpLive", payload)
    if data["result"]["code"] == "0":
        return data["result"]["data"]["rtmp"]
    else:
        raise Exception(f"queryDeviceRtmpLive failed: {data}")

# ------------------- Lecture RTMP stable via FFmpeg -------------------
def open_rtmp_stream_ffmpeg(rtmp_url, width=640, height=480):
    """
    Lit un flux RTMP en direct via ffmpeg -> OpenCV
    width/height: dimensions du flux. Adapter si nécessaire.
    """
    command = [
        "ffmpeg",
        "-i", rtmp_url,
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-"
    ]
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**8)
    frame_count = 0
    process_every_n = 15
    try:
        prev_time = time.time()
        while True:
            raw_frame = pipe.stdout.read(width * height * 3)
            if len(raw_frame) != width * height * 3:
                break
            frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))

            # rendre le tableau writable
            frame = frame.copy()

            # Affichage FPS stable
            now = time.time()
            #fps = 1.0 / (now - prev_time)
            prev_time = now
            """cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)"""
            frame_count += 1

            if frame_count % process_every_n == 0:
                yolov8_detection(frame)  # inference YOLO seulement sur cette frame
                #yolov5_detection(frame)
                #mediapipe_detection(frame)

            cv2.imshow("Camera Live", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        pipe.terminate()
        cv2.destroyAllWindows()

# ------------------- MAIN -------------------
if __name__ == "__main__":
    token = get_access_token()
    print("✅ AccessToken:", token)

    devices = get_live_list(token)
    chosen_device = None
    chosen_rtmp = None

    # Sélection du premier flux RTMP disponible
    for dev in devices:
        for s in dev.get("streams", []):
            rtmp = s.get("rtmp")
            if rtmp:
                chosen_device = dev
                chosen_rtmp = rtmp
                print(f"✅ Device choisi: {dev.get('deviceId')}")
                print(f"✅ RTMP disponible: {rtmp}")
                break
        if chosen_rtmp:
            break

    if not chosen_rtmp:
        # Génération du flux RTMP si aucun disponible directement
        if not chosen_device:
            chosen_device = devices[0]
        device_id = chosen_device["deviceId"]
        channel_id = str(chosen_device["channelId"])
        print(f"✅ Génération flux RTMP pour {device_id}, channel {channel_id}...")
        chosen_rtmp = create_rtmp(token, device_id, channel_id)
        print(f"✅ RTMP URL: {chosen_rtmp}")

    # Lecture stable du flux RTMP
    open_rtmp_stream_ffmpeg(chosen_rtmp)



