import time
import uuid
import hashlib
import requests
from config import AppId, AppSecret, BASE_URL

# ------------------- Utilitaires -------------------
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

# ------------------- Liste des devices -------------------
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

# ------------------- Mouvement PTZ -------------------
OPERATIONS = {
    "up": 0,
    "down": 1,
    "left": 2,
    "right": 3
}

def move_ptz(token, device_id, operation, duration_ms=200, channel_id="0"):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {
            "token": token,
            "deviceId": device_id,
            "channelId": channel_id,
            "operation": str(OPERATIONS[operation]),
            "duration": str(duration_ms)
        }
    }
    return post("controlMovePTZ", payload)

# Fonctions pratiques
def move_up(token, device_id, channel_id="0"): return move_ptz(token, device_id, "up", channel_id=channel_id)
def move_down(token, device_id, channel_id="0"): return move_ptz(token, device_id, "down", channel_id=channel_id)
def move_left(token, device_id, channel_id="0"): return move_ptz(token, device_id, "left", channel_id=channel_id)
def move_right(token, device_id, channel_id="0"): return move_ptz(token, device_id, "right", channel_id=channel_id)

# ------------------- MAIN -------------------
if __name__ == "__main__":
    token = get_access_token()
    print("✅ AccessToken:", token)

    # Récupération automatique du premier device et channelId
    devices = get_live_list(token)
    if not devices:
        raise Exception("Aucun device trouvé.")
    
    device = devices[0]
    device_id = device["deviceId"]
    channel_id = str(device.get("channelId", "0"))

    print(f"✅ Device choisi: {device_id}, ChannelId: {channel_id}")

    # Test des mouvements PTZ
    print("⬆ Déplacement haut")
    print(move_up(token, device_id, channel_id=channel_id))

    print("⬇ Déplacement bas")
    print(move_down(token, device_id, channel_id=channel_id))

    print("⬅ Déplacement gauche")
    print(move_left(token, device_id, channel_id=channel_id))

    print("➡ Déplacement droite")
    print(move_right(token, device_id, channel_id=channel_id))
