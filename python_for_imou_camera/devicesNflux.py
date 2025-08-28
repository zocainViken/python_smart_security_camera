import time
import uuid
import hashlib
import requests
import subprocess
from config import AppId, AppSecret, BASE_URL  # Assure-toi que ces constantes existent

# ---------- Réglages ----------
QUERY_RANGE = "1-50"  # Nombre d'items à parcourir côté API
CHECK_URLS = True     # Vérifie que les URLs répondent

# ---------- Utilitaires ----------
def make_sign(time_stamp, nonce, secret):
    raw = f"time:{time_stamp},nonce:{nonce},appSecret:{secret}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def post(endpoint, payload):
    url = f"{BASE_URL}/{endpoint}"
    r = requests.post(url, json=payload, timeout=15)
    r.raise_for_status()
    return r.json()

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
    if data.get("result", {}).get("code") == "0":
        return data["result"]["data"]["accessToken"]
    raise RuntimeError(f"Login failed: {data}")

# ---------- Vérifications d’URL ----------
def check_hls(url):
    if not CHECK_URLS:
        return True
    try:
        r = requests.get(url, stream=True, timeout=5)
        return 200 <= r.status_code < 400
    except requests.RequestException:
        return False

def check_rtmp(url):
    if not CHECK_URLS:
        return True
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 1935  # Port RTMP par défaut
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((hostname, port))
        s.close()
        return True
    except Exception:
        return False

# ---------- Gestion RTMP ----------
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
    if data.get("result", {}).get("code") == "0":
        return data["result"]["data"]["rtmp"]
    return None

# ---------- Listing principal ----------
def list_devices_and_streams(token, query_range=QUERY_RANGE):
    ts = int(time.time())
    nonce = str(uuid.uuid4())
    sign = make_sign(ts, nonce, AppSecret)
    payload = {
        "system": {"ver": "1.0", "appId": AppId, "sign": sign, "time": ts, "nonce": nonce},
        "id": str(uuid.uuid4()),
        "params": {"token": token, "queryRange": query_range}
    }
    data = post("liveList", payload)
    if data.get("result", {}).get("code") != "0":
        raise RuntimeError(f"liveList failed: {data}")

    devices = data["result"]["data"].get("lives", [])
    if not devices:
        print("⚠️ Aucun device trouvé.")
        return

    print(f"📋 {len(devices)} device(s) trouvé(s)\n")
    for idx, device in enumerate(devices):
        print("=" * 80)
        device_id = device.get("deviceId", "N/A")
        channel_id = str(device.get("channelId", "0"))
        print(f"Device {idx}: {device_id} (Channel: {channel_id})")

        # Lister les flux disponibles
        working_hls = []
        working_rtmp = None
        if "streams" in device and device["streams"]:
            print("Flux disponibles :")
            for stream in device["streams"]:
                hls_url = stream.get("hls")
                rtmp_url = stream.get("rtmp")

                if hls_url:
                    ok = check_hls(hls_url)
                    status = "✅" if ok else "❌"
                    print(f"  - HLS: {status} {hls_url}")
                    if ok:
                        working_hls.append(hls_url)

                if rtmp_url:
                    ok = check_rtmp(rtmp_url)
                    status = "✅" if ok else "❌"
                    print(f"  - RTMP: {status} {rtmp_url}")
                    if ok:
                        working_rtmp = rtmp_url

        # Si aucun flux RTMP n'est disponible, essayer d'en créer un
        if not working_rtmp:
            print("  ➡️ Tentative de création d'un flux RTMP...")
            rtmp_url = query_rtmp(token, device_id, channel_id)
            if rtmp_url:
                ok = check_rtmp(rtmp_url)
                status = "✅" if ok else "❌"
                print(f"  - RTMP (créé): {status} {rtmp_url}")
                if ok:
                    working_rtmp = rtmp_url
            else:
                print("  - Impossible de créer un flux RTMP.")

        # Résumé des flux utilisables
        if working_hls:
            print(f"\n  🔹 Utilise ce flux HLS: {working_hls[0]}")
        if working_rtmp:
            print(f"  🔹 Utilise ce flux RTMP: {working_rtmp}")
        print()

# ---------- MAIN ----------
if __name__ == "__main__":
    try:
        token = get_access_token()
        print("✅ AccessToken obtenu.")
        list_devices_and_streams(token)

        print("""Quel flux choisir ?
Utiliser le flux HLS (recommandé pour la stabilité)
Pourquoi ?
HLS est plus stable sur les réseaux instables.
Moins sensible aux coupures.
Fonctionne directement avec OpenCV et FFmpeg.
                   
Utiliser le flux RTMP (si nécessaire)
Pourquoi ?
Latence plus faible que HLS.
Utile si tu as besoin d'une interaction en temps réel.
""")
    except Exception as e:
        print(f"❌ Erreur: {e}")
