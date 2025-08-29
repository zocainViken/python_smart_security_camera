import pyaudio
import wave
import time
import os
from datetime import datetime
import threading

import subprocess
import pyaudio
import threading
import time
import os
from datetime import datetime

class AudioRTMP:
    def __init__(self, rtmp_url, listen=True, record=False, output_dir="audio_recordings"):
        self.rtmp_url = rtmp_url
        self.listen = listen
        self.record = record
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.frames = []
        self.is_running = False
        self.thread = None
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.pipe = None

    def start(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.thread.start()
        print("[AUDIO] 🎙️ Audio RTMP démarré...")

    def _audio_loop(self):
        command = [
            "ffmpeg",
            "-i", self.rtmp_url,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "44100",
            "-"
        ]
        self.pipe = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=4096)

        self.stream = self.pa.open(format=pyaudio.paInt16,
                                   channels=1,
                                   rate=44100,
                                   output=self.listen)

        try:
            while self.is_running:
                data = self.pipe.stdout.read(1024)
                if not data:
                    break
                if self.listen:
                    self.stream.write(data)
                if self.record:
                    self.frames.append(data)
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pipe:
                self.pipe.terminate()
            self.pa.terminate()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)

        filename = None
        if self.record and self.frames:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.output_dir, f"audio_{timestamp}.wav")
            import wave
            wf = wave.open(filename, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            print(f"[AUDIO] 💾 Audio sauvegardé : {filename}")
        return filename


import subprocess

def play_rtmp_audio(rtmp_url):
    # ffmpeg pour sortir du PCM raw
    command = [
        "ffmpeg",
        "-i", rtmp_url,
        "-f", "s16le",     # PCM 16 bits
        "-acodec", "pcm_s16le",
        "-ac", "1",        # mono
        "-ar", "44100",    # fréquence
        "-"                # sortie stdout
    ]
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=4096)
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=44100, output=True)
    try:
        while True:
            data = pipe.stdout.read(1024)
            if not data:
                break
            stream.write(data)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        pipe.terminate()



def detect_audio_materiel():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(i, info["name"], info["maxInputChannels"], info["maxOutputChannels"])





