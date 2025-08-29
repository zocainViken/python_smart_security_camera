# camera.py

import cv2
import time
import uuid
import hashlib
import requests
import subprocess
import numpy as np
from detection import yolov8_detection
from config import AppId, AppSecret, BASE_URL 
from audio import AudioRTMP 
#from motion_tracking import MotionDetector

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
    elif code == "LV1001":
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
            frame = frame.copy()

            frame_count += 1
            if frame_count % process_every_n == 0:
                yolov8_detection(frame)

            cv2.imshow("Camera Live", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        pipe.terminate()
        cv2.destroyAllWindows()

# ------------------- MAIN -------------------
if __name__ == "__main__":
    token = get_access_token()
    devices = get_live_list(token)
    chosen_device = None
    chosen_rtmp = None

    # Choisir le premier flux RTMP disponible
    for dev in devices:
        for s in dev.get("streams", []):
            rtmp = s.get("rtmp")
            if rtmp:
                chosen_device = dev
                chosen_rtmp = rtmp
                break
        if chosen_rtmp:
            break

    if not chosen_rtmp:
        if not chosen_device:
            chosen_device = devices[0]
        device_id = chosen_device["deviceId"]
        channel_id = str(chosen_device["channelId"])
        chosen_rtmp = create_rtmp(token, device_id, channel_id)

    print(f"✅ RTMP URL: {chosen_rtmp}")

    # --- 🎙️ Lancer audio RTMP en parallèle ---
    # Après avoir récupéré chosen_rtmp
    audio_manager = AudioRTMP(chosen_rtmp)
    audio_manager.start()

    try:
        open_rtmp_stream_ffmpeg(chosen_rtmp)  # ta fonction vidéo
    finally:
        audio_manager.stop()
