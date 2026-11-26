from __future__ import annotations
import asyncio, ctypes, io, os, queue, re, tempfile, threading, time, wave
import numpy as np
from PySide6.QtCore import QObject, Signal

# Ultra-realistic neural voices for Judy (powered by Azure Neural Speech via edge-tts, ElevenLabs & OpenAI)
NATURAL_VOICES = {
    # Free Neural Voices (Zero Key Needed)
    "Ava — Warm, Conversational (American, Free)": "en-US-AvaNeural",
    "Sonia — Sophisticated Luxury (British, Free)": "en-GB-SoniaNeural",
    "Natasha — Charming & Warm (Australian, Free)": "en-AU-NatashaNeural",
    "Jenny — Clear Professional (American, Free)": "en-US-JennyNeural",
    "Libby — Gentle & Articulate (British, Free)": "en-GB-LibbyNeural",
    "Aria — Dynamic Executive (American, Free)": "en-US-AriaNeural",
    # Studio-Grade Human Voices (ElevenLabs - Ultra Realistic, Breath & Emotion)
    "Rachel — Ultra-Realistic Studio Female (ElevenLabs)": "elevenlabs:21m00Tcm4TlvDq8ikWAM",
    "Sarah — Soft, Emotive & Breathy (ElevenLabs)": "elevenlabs:EXAVITQu4vr4xnSDxMaL",
    # OpenAI Human Voices
    "Nova — Warm, Playful & Natural (OpenAI)": "openai:nova",
    "Shimmer — Soft & Gentle Female (OpenAI)": "openai:shimmer",
}

class VoiceService(QObject):
    wake_triggered = Signal(str)      # Emits command after "Judy"
    voice_heard = Signal(str)         # Emits transcribed speech
    status_changed = Signal(str)      # "idle", "listening", "processing", "speaking"
    error_raised = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._running = False
        self._listener_thread = None
        self._speaker = None
        self._speech_queue = queue.Queue()
        self._stop_flag = threading.Event()
        self._init_fallback_speaker()

        # Dedicated background daemon thread for natural speech synthesis
        self._speech_worker = threading.Thread(target=self._speech_loop, daemon=True)
        self._speech_worker.start()

    def _init_fallback_speaker(self):
        try:
            import win32com.client
            self._speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = self._speaker.GetVoices()
            for i in range(voices.Count):
                desc = voices.Item(i).GetDescription().lower()
                if any(k in desc for k in ["zira", "eva", "female", "samantha"]):
                    self._speaker.Voice = voices.Item(i)
                    break
        except Exception:
            self._speaker = None

    def speak(self, text: str):
        if not self.settings.voice_output_enabled or not text:
            return
        # Clean text for natural speech
        clean = re.sub(r"https?://\S+", "link", text)
        clean = re.sub(r"[*_#`~\[\]<>]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        clean = clean[:350]  # Keep spoken answer executive and concise

        # Stop previous speech and queue new speech
        self.stop_speaking()
        self._speech_queue.put(clean)

    def preview_voice(self, voice_code: str):
        """Synthesize and speak an instant high-fidelity audio preview of the chosen voice."""
        sample = "Hello! I am Judy, your AI companion. My voice is now crystal-clear, warm, and natural."
        self.stop_speaking()
        self._speech_queue.put((sample, voice_code))

    def _speech_loop(self):
        """Worker loop that synthesizes natural human neural speech and plays it."""
        while True:
            item = self._speech_queue.get()
            if not item:
                continue

            if isinstance(item, tuple):
                text, override_voice = item
            else:
                text, override_voice = item, None

            if not text:
                continue

            self._stop_flag.clear()
            self.status_changed.emit("processing")

            # 1. Attempt High-Fidelity Human Neural Speech
            played = False
            voice_code = override_voice or getattr(self.settings, "neural_voice", "en-US-AvaNeural")
            temp_mp3 = os.path.join(tempfile.gettempdir(), f"judy_speech_{int(time.time()*1000)}.mp3")

            try:
                # A. OpenAI Neural TTS (Nova, Shimmer) if selected
                if str(voice_code).startswith("openai:"):
                    voice_name = voice_code.split(":", 1)[1]
                    from .config import get_api_key, get_provider_key
                    oa_key = get_provider_key("openai") or get_api_key(self.settings) or os.environ.get("OPENAI_API_KEY", "")
                    if oa_key:
                        import requests
                        r = requests.post(
                            "https://api.openai.com/v1/audio/speech",
                            headers={"Authorization": f"Bearer {oa_key}", "Content-Type": "application/json"},
                            json={"model": "tts-1-hd", "input": text, "voice": voice_name},
                            timeout=20,
                        )
                        if r.status_code == 200 and len(r.content) > 500:
                            with open(temp_mp3, "wb") as f:
                                f.write(r.content)
                    if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 500:
                        voice_code = "en-US-AvaNeural"

                # B. ElevenLabs synthesis if configured and selected
                elif str(voice_code).startswith("elevenlabs:"):
                    voice_id = voice_code.split(":", 1)[1]
                    from .config import get_provider_key
                    el_key = get_provider_key("elevenlabs") or os.environ.get("ELEVENLABS_API_KEY", "")
                    if el_key:
                        import requests
                        r = requests.post(
                            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                            headers={"xi-api-key": el_key, "Content-Type": "application/json"},
                            json={"text": text, "model_id": "eleven_multilingual_v2"},
                            timeout=25,
                        )
                        if r.status_code == 200 and len(r.content) > 500:
                            with open(temp_mp3, "wb") as f:
                                f.write(r.content)
                    if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 500:
                        voice_code = "en-US-AvaNeural"

                # C. Microsoft Azure Neural TTS (via edge-tts) — Free, no key required
                if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 100:
                    import edge_tts
                    edge_voice = voice_code if str(voice_code).startswith("en-") else "en-US-AvaNeural"
                    async def generate_audio():
                        communicate = edge_tts.Communicate(text, edge_voice, rate="-4%", pitch="+1Hz")
                        await communicate.save(temp_mp3)
                    asyncio.run(generate_audio())

                if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 100 and not self._stop_flag.is_set():
                    mci = ctypes.windll.winmm.mciSendStringW
                    alias = f"judy_voice_{int(time.time()*1000)}"
                    mci(f'open "{temp_mp3}" type mpegvideo alias {alias}', 0, 0, 0)
                    self.status_changed.emit("speaking")
                    mci(f"play {alias} wait", 0, 0, 0)
                    mci(f"close {alias}", 0, 0, 0)
                    played = True
            except Exception:
                # If network glitch occurred on edge-tts, fallback to Jenny
                try:
                    import edge_tts
                    async def fallback_audio():
                        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
                        await communicate.save(temp_mp3)
                    asyncio.run(fallback_audio())
                    if os.path.exists(temp_mp3) and os.path.getsize(temp_mp3) > 100 and not self._stop_flag.is_set():
                        mci = ctypes.windll.winmm.mciSendStringW
                        alias = f"judy_voice_{int(time.time()*1000)}"
                        mci(f'open "{temp_mp3}" type mpegvideo alias {alias}', 0, 0, 0)
                        self.status_changed.emit("speaking")
                        mci(f"play {alias} wait", 0, 0, 0)
                        mci(f"close {alias}", 0, 0, 0)
                        played = True
                except Exception:
                    played = False
            finally:
                if os.path.exists(temp_mp3):
                    try:
                        os.remove(temp_mp3)
                    except Exception:
                        pass

            # 2. Offline fallback only if completely disconnected from internet
            if not played and not self._stop_flag.is_set():
                if self._speaker:
                    try:
                        self.status_changed.emit("speaking")
                        self._speaker.Speak(text, 0)
                    except Exception:
                        pass

            self.status_changed.emit("idle")

    def stop_speaking(self):
        """Immediately interrupts any current speech playback."""
        self._stop_flag.set()
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except Exception:
                break

        try:
            mci = ctypes.windll.winmm.mciSendStringW
            mci("stop all", 0, 0, 0)
            mci("close all", 0, 0, 0)
        except Exception:
            pass

        if self._speaker:
            try:
                self._speaker.Speak("", 2)
            except Exception:
                pass

        self.status_changed.emit("idle")

    def start_wake_listener(self):
        if self._running:
            return
        self._running = True
        self._listener_thread = threading.Thread(target=self._wake_loop, daemon=True)
        self._listener_thread.start()
        self.status_changed.emit("listening")

    def stop_wake_listener(self):
        self._running = False
        self.status_changed.emit("idle")

    def _wake_loop(self):
        """Continuous background listener looking for 'Judy'."""
        try:
            import sounddevice as sd
            import speech_recognition as sr
        except ImportError as e:
            self.error_raised.emit(f"Audio libraries missing: {e}")
            return

        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 280
        recognizer.dynamic_energy_threshold = True
        sample_rate = 16000
        chunk_seconds = 3.5

        while self._running:
            if not self.settings.wake_word_enabled:
                time.sleep(0.5)
                continue

            try:
                audio_data = sd.rec(int(chunk_seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
                sd.wait()

                # If volume is too low, skip recognition to save CPU & network
                max_amp = np.max(np.abs(audio_data))
                if max_amp < 450:
                    time.sleep(0.05)
                    continue

                # Convert to WAV in memory
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_data.tobytes())
                wav_io.seek(0)

                with sr.AudioFile(wav_io) as source:
                    audio = recognizer.record(source)

                text = recognizer.recognize_google(audio).strip()
                if not text:
                    continue

                low = text.lower()
                wake_key = self.settings.wake_word.lower()

                # Check specifically for "hey judy", "judy", or phonetic variants
                wake_variants = [wake_key, "hey judy", "judy", "judie", "judi"]
                if any(w in low for w in wake_variants):
                    command = re.sub(r"^(hey|hi|hello|ok|okay)?\s*(judy|judie|judi)\s*(please)?", "", text, flags=re.I).strip(" ,.?!")
                    self.wake_triggered.emit(command or "Hello Commander")
                    time.sleep(1.0)
            except sr.UnknownValueError:
                pass
            except Exception:
                time.sleep(0.3)

    def record_once(self, seconds: float = 4.0) -> str:
        """One-shot recording for Push-to-Talk or Mic button click."""
        try:
            import sounddevice as sd
            import speech_recognition as sr

            sample_rate = 16000
            self.status_changed.emit("listening")
            audio_data = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
            sd.wait()

            # Check if volume is non-zero
            max_amp = np.max(np.abs(audio_data))
            if max_amp < 250:
                self.status_changed.emit("idle")
                return ""

            self.status_changed.emit("processing")
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())
            wav_io.seek(0)

            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 280
            recognizer.dynamic_energy_threshold = True
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio).strip()
            except sr.UnknownValueError:
                text = ""
            except sr.RequestError as e:
                self.error_raised.emit(f"Speech recognition network error: {e}")
                text = ""

            self.status_changed.emit("idle")
            return text
        except Exception as e:
            self.error_raised.emit(f"Microphone recording error: {e}")
            self.status_changed.emit("idle")
            return ""

    def start_recording_async(self, seconds: float = 4.0):
        """Asynchronously records audio and emits `voice_heard(text)` on completion."""
        def work():
            text = self.record_once(seconds)
            if text:
                self.voice_heard.emit(text)
            else:
                self.status_changed.emit("idle")
        threading.Thread(target=work, daemon=True).start()

