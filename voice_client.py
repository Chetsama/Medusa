#!/usr/bin/env python3
"""
Medusa Voice Client
A full-duplex voice client for Medusa multi-agent system running in WSL.
Pipeline: Microphone/File -> Speech-to-Text (Whisper) -> Medusa Gateway -> Text-to-Speech (F5-TTS) -> Playback
"""

import os
import sys

# Auto-switch to local .venv if available and not already inside it
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python3")
if os.path.exists(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python) and not os.environ.get("MEDUSA_VENV_ACTIVE"):
    os.environ["MEDUSA_VENV_ACTIVE"] = "1"
    os.execv(venv_python, [venv_python] + sys.argv)

import argparse
import io
import json
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from typing import List, Dict, Optional, Tuple, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.orchestrator import OrchestratorAgent
from langchain.messages import HumanMessage, AIMessage, ToolMessage

# Automatically configure WSLg PulseAudio if running under WSL
if "PULSE_SERVER" not in os.environ and os.path.exists("/mnt/wslg/PulseServer"):
    os.environ["PULSE_SERVER"] = "/mnt/wslg/PulseServer"


# Ensure user-writable HuggingFace cache
if "HF_HOME" not in os.environ:
    os.environ["HF_HOME"] = os.path.expanduser("~/.hf_cache")

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def preload_nvidia_libs():
    """Preloads pip-installed nvidia CUDA libraries into global namespace for CTranslate2."""
    try:
        import ctypes
        import site
        for sp in site.getsitepackages():
            for pkg in ["cublas", "cudnn", "cuda_nvrtc"]:
                lib_dir = os.path.join(sp, "nvidia", pkg, "lib")
                if os.path.exists(lib_dir):
                    for f in sorted(os.listdir(lib_dir)):
                        if ".so" in f:
                            try:
                                ctypes.CDLL(os.path.join(lib_dir, f), mode=ctypes.RTLD_GLOBAL)
                            except Exception:
                                pass
    except Exception:
        pass


# ANSI Color codes for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


class AudioRecorder:
    """Handles audio capture using PulseAudio (parecord), FFmpeg, or SoundDevice."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def record_push_to_talk(self) -> Optional[str]:
        """Records audio starting on Enter and stopping on next Enter."""
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}Press [ENTER] to start recording...{Colors.RESET}", end="", flush=True)
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            return None

        # Check recording tool
        if shutil.which("parecord"):
            # Native WSL PulseAudio recorder (direct hardware mic access via WSLg)
            proc = subprocess.Popen(
                ["parecord", "--channels=1", f"--rate={self.sample_rate}", "--file-format=wav", temp_wav],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif shutil.which("ffmpeg"):
            # FFmpeg pulse capture
            proc = subprocess.Popen(
                ["ffmpeg", "-y", "-f", "pulse", "-i", "default", "-ac", "1", "-ar", str(self.sample_rate), temp_wav],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            print(f"\n{Colors.RED}No recording utility found (parecord or ffmpeg required).{Colors.RESET}")
            return None

        print(f"{Colors.RED}{Colors.BOLD}🔴 Recording... Speak now! Press [ENTER] when done.{Colors.RESET}", end="", flush=True)
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 2000:
            return temp_wav
        else:
            print(f"\n{Colors.YELLOW}No audio recorded or recording too short.{Colors.RESET}")
            return None

    def record_timed(self, duration: float) -> Optional[str]:
        """Records audio for a fixed duration in seconds."""
        temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        print(f"\n{Colors.RED}{Colors.BOLD}🔴 Recording for {duration} seconds...{Colors.RESET}")

        if shutil.which("parecord"):
            cmd = ["parecord", "--channels=1", f"--rate={self.sample_rate}", "--file-format=wav", temp_wav]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(duration)
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        elif shutil.which("ffmpeg"):
            cmd = ["ffmpeg", "-y", "-f", "pulse", "-i", "default", "-t", str(duration), "-ac", "1", "-ar", str(self.sample_rate), temp_wav]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print(f"{Colors.RED}No recording utility found (parecord or ffmpeg).{Colors.RESET}")
            return None

        if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 2000:
            return temp_wav
        return None


class AudioPlayer:
    """Handles audio playback in WSL via paplay, ffplay, or aplay."""

    @staticmethod
    def play(wav_path_or_bytes) -> bool:
        temp_file = None
        if isinstance(wav_path_or_bytes, (bytes, bytearray)):
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.write(wav_path_or_bytes)
            temp_file.flush()
            temp_file.close()
            wav_path = temp_file.name
        else:
            wav_path = wav_path_or_bytes

        try:
            if shutil.which("paplay"):
                # Native PulseAudio player (WSLg)
                subprocess.run(["paplay", wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            elif shutil.which("ffplay"):
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", wav_path], check=True)
                return True
            elif shutil.which("aplay"):
                subprocess.run(["aplay", wav_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            else:
                print(f"{Colors.YELLOW}No audio player found (paplay, ffplay, or aplay). Audio saved at: {wav_path}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.YELLOW}Audio playback error: {e}{Colors.RESET}")
            return False
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except OSError:
                    pass


class SpeechToText:
    """Transcribes audio using faster-whisper with automatic GPU/CPU fallback."""

    def __init__(self, model_size: str = "base.en", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self.model = None
        self._engine = None

    def _init_model(self):
        if self.model is not None:
            return

        preload_nvidia_libs()
        download_root = os.environ.get("HF_HOME", os.path.expanduser("~/.hf_cache"))
        os.makedirs(download_root, exist_ok=True)

        print(f"{Colors.DIM}Loading STT model ({self.model_size})...{Colors.RESET}", end="", flush=True)

        # 1. Try faster-whisper
        try:
            import ctranslate2
            from faster_whisper import WhisperModel

            want_cuda = (self.device == "cuda") or (self.device == "auto" and ctranslate2.get_cuda_device_count() > 0)
            
            if want_cuda:
                try:
                    self.model = WhisperModel(self.model_size, device="cuda", compute_type="float16", download_root=download_root)
                    self._engine = "faster_whisper"
                    print(f" {Colors.GREEN}Ready (CUDA/float16){Colors.RESET}")
                    return
                except Exception as cuda_err:
                    print(f" {Colors.YELLOW}[CUDA fallback: {cuda_err}]{Colors.RESET}", end="")

            # Fallback to CPU int8
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8", download_root=download_root)
            self._engine = "faster_whisper"
            print(f" {Colors.GREEN}Ready (CPU/int8){Colors.RESET}")
            return
        except Exception:
            pass

        # 2. Try openai-whisper
        try:
            import whisper
            dev = "cuda" if (self.device == "cuda" or self.device == "auto") else "cpu"
            self.model = whisper.load_model(self.model_size, device=dev, download_root=download_root)
            self._engine = "whisper"
            print(f" {Colors.GREEN}Ready (openai-whisper/{dev}){Colors.RESET}")
            return
        except Exception:
            pass

        print(f"\n{Colors.YELLOW}STT Notice: No Whisper STT engine available.{Colors.RESET}")
        print(f"To enable voice transcription, run: {Colors.BOLD}pip install faster-whisper{Colors.RESET}")
        self._engine = None

    def transcribe(self, audio_path: str) -> str:
        self._init_model()
        if not self._engine:
            raise RuntimeError("No Whisper STT engine available. Please run: pip install faster-whisper")

        if self._engine == "faster_whisper":
            segments, _ = self.model.transcribe(audio_path, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip()
            return text
        elif self._engine == "whisper":
            result = self.model.transcribe(audio_path)
            return result.get("text", "").strip()

        return ""


DEFAULT_LLM_URL = "http://llm.coffee-dev.uk/v1"
DEFAULT_TTS_URL = "http://localhost:5000/v1/audio/speech"
DEFAULT_MODEL = "qwen3.8-27b"
DEFAULT_VOICE = "jarvis"


class MedusaVoiceClient:
    """Full-duplex orchestrator for interactive voice conversation."""

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        llm_url: str = DEFAULT_LLM_URL,
        tts_url: str = DEFAULT_TTS_URL,
        model_name: str = DEFAULT_MODEL,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
        stt_model: str = "base.en",
        stt_device: str = "auto",
        stream: bool = True,
        use_tts: bool = True,
        use_stt: bool = True,
        duration: Optional[float] = None
    ):
        self.gateway_url = gateway_url
        self.llm_url = llm_url
        self.tts_url = tts_url
        self.model_name = model_name
        self.voice = voice
        self.speed = speed
        self.stream = stream
        self.use_tts = use_tts
        self.use_stt = use_stt
        self.duration = duration

        # Initialize embedded agent when running locally without external HTTP gateway
        self.agent = None
        if not self.gateway_url:
            self.agent = OrchestratorAgent(model_name=self.model_name, api_base=self.llm_url)

        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        self.stt = SpeechToText(model_size=stt_model, device=stt_device) if use_stt else None
        self.history: List[Any] = []

    def _execute_embedded_turn(self, user_text: str) -> Tuple[str, str]:
        """Executes agent turn directly with local tools in current working directory."""
        user_msg = HumanMessage(content=user_text)
        self.history.append(user_msg)

        print(f"\n{Colors.BLUE}{Colors.BOLD}Agent Workflow ({os.getcwd()}):{Colors.RESET}")

        seen_messages = len(self.history)
        last_node = None
        final_reply = ""
        last_state = None

        try:
            for state in self.agent.stream({"messages": self.history, "tool_turns": 0, "active_node": "init"}):
                last_state = state
                active_node = state.get("active_node", "init")
                new_msgs = state["messages"][seen_messages:]
                seen_messages = len(state["messages"])

                if active_node == "agent":
                    for msg in new_msgs:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                args_str = ", ".join(f"{k}={v!r}" for k, v in tc.get("args", {}).items())
                                print(f"🛠️  {Colors.YELLOW}{Colors.BOLD}Tool Call:{Colors.RESET} {Colors.CYAN}`{tc['name']}({args_str})`{Colors.RESET}")
                elif active_node == "tools":
                    for msg in new_msgs:
                        if isinstance(msg, ToolMessage):
                            out_snippet = msg.content.strip().replace("\n", " ")
                            if len(out_snippet) > 120:
                                out_snippet = out_snippet[:117] + "..."
                            print(f"   📄 {Colors.DIM}Result: {out_snippet}{Colors.RESET}")

                last_node = active_node

            if last_state and last_state.get("messages"):
                for m in reversed(last_state["messages"]):
                    if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                        final_reply = m.content.strip()
                        break
                    elif isinstance(m, AIMessage) and m.content and not m.content.strip().startswith("{") and not m.content.strip().startswith("["):
                        final_reply = m.content.strip()
                        break
                if not final_reply and last_state.get("last_result"):
                    final_reply = last_state["last_result"]

        except Exception as e:
            print(f"\n{Colors.RED}Agent execution error: {e}{Colors.RESET}")
            final_reply = f"I encountered an issue executing that command, sir: {str(e)}"

        if not final_reply:
            final_reply = "I have completed the task, sir."

        print(f"\n{Colors.GREEN}{Colors.BOLD}Jarvis:{Colors.RESET} {final_reply}\n")
        self.history.append(AIMessage(content=final_reply))

        # Clean text for TTS
        clean_text = final_reply.replace("`", "").replace("**", "").replace("##", "").replace("*", "").replace("- ", "")
        return final_reply, clean_text

    def _execute_gateway_turn(self, user_text: str) -> Tuple[str, str]:
        """Sends user message to an external Medusa HTTP gateway."""
        self.history.append({"role": "user", "content": user_text})
        payload = {
            "model": self.model_name,
            "messages": self.history,
            "stream": self.stream
        }

        full_reply = ""
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.gateway_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Authorization": "Bearer none"
                }
            )

            if not self.stream:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    full_reply = resp_data["choices"][0]["message"]["content"]
                    print(f"\n{Colors.GREEN}{Colors.BOLD}Jarvis:{Colors.RESET} {full_reply}")
            else:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    in_thought = False
                    thought_buffer = ""
                    final_buffer = ""

                    print(f"\n{Colors.BLUE}{Colors.BOLD}Agent Workflow:{Colors.RESET}")
                    for raw_line in resp:
                        if not raw_line:
                            continue
                        line_str = raw_line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data_str)
                                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")

                                if "<thought>" in content:
                                    in_thought = True
                                    continue
                                if "</thought>" in content:
                                    in_thought = False
                                    print(f"\n{Colors.GREEN}{Colors.BOLD}Jarvis:{Colors.RESET} ", end="", flush=True)
                                    continue

                                if in_thought:
                                    thought_buffer += content
                                    sys.stdout.write(f"{Colors.DIM}{content}{Colors.RESET}")
                                    sys.stdout.flush()
                                else:
                                    final_buffer += content
                                    sys.stdout.write(f"{Colors.BOLD}{content}{Colors.RESET}")
                                    sys.stdout.flush()
                            except json.JSONDecodeError:
                                continue

                    print()
                    full_reply = final_buffer.strip() if final_buffer.strip() else thought_buffer.strip()

        except urllib.error.URLError as e:
            print(f"\n{Colors.RED}Could not reach Gateway at {self.gateway_url}: {e}{Colors.RESET}")
            return "", ""
        except Exception as e:
            print(f"\n{Colors.RED}Gateway request failed: {e}{Colors.RESET}")
            return "", ""

        if full_reply:
            self.history.append({"role": "assistant", "content": full_reply})

        clean_text = full_reply.replace("`", "").replace("**", "").replace("##", "").replace("*", "")
        return full_reply, clean_text

    def send_chat_completion(self, user_text: str) -> Tuple[str, str]:
        """Routes chat turn to embedded agent or external gateway."""
        if self.gateway_url:
            return self._execute_gateway_turn(user_text)
        else:
            return self._execute_embedded_turn(user_text)

    def synthesize_and_play(self, text: str, save_path: Optional[str] = None) -> bool:
        """Sends clean text to F5-TTS and plays back audio."""
        if not text.strip() or not self.use_tts:
            return False

        print(f"{Colors.CYAN}🔊 Synthesizing speech with F5-TTS (voice: {self.voice})...{Colors.RESET}")
        payload = {
            "model": "f5-tts",
            "input": text,
            "voice": self.voice,
            "speed": self.speed,
            "response_format": "wav"
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.tts_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": DEFAULT_USER_AGENT
                }
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                audio_bytes = resp.read()
                if save_path:
                    with open(save_path, "wb") as f:
                        f.write(audio_bytes)
                    print(f"{Colors.DIM}Audio saved to: {save_path}{Colors.RESET}")
                
                self.player.play(audio_bytes)
                return True
        except urllib.error.URLError as e:
            print(f"{Colors.YELLOW}Could not reach TTS server at {self.tts_url}: {e}\nTip: Start the TTS container with: docker compose up -d{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.YELLOW}TTS synthesis error: {e}{Colors.RESET}")
            return False

    def process_turn(self, audio_file: Optional[str] = None, text_input: Optional[str] = None) -> bool:
        """Executes a single user interaction turn."""
        user_text = ""

        if text_input:
            user_text = text_input.strip()
            print(f"\n{Colors.CYAN}{Colors.BOLD}You (text):{Colors.RESET} {user_text}")
        else:
            if not audio_file:
                if self.duration:
                    audio_file = self.recorder.record_timed(self.duration)
                else:
                    audio_file = self.recorder.record_push_to_talk()

            if not audio_file or not os.path.exists(audio_file):
                return False

            print(f"{Colors.CYAN}Transcribing audio...{Colors.RESET}")
            try:
                user_text = self.stt.transcribe(audio_file)
            except Exception as e:
                print(f"{Colors.RED}Transcription error: {e}{Colors.RESET}")
                return False
            finally:
                if os.path.exists(audio_file):
                    try:
                        os.remove(audio_file)
                    except OSError:
                        pass

            if not user_text.strip():
                print(f"{Colors.YELLOW}No speech recognized.{Colors.RESET}")
                return False

            print(f"\n{Colors.CYAN}{Colors.BOLD}You (voice):{Colors.RESET} {user_text}")

        # Send to agent orchestrator
        full_reply, clean_text = self.send_chat_completion(user_text)

        # Synthesize audio response
        if clean_text and self.use_tts:
            self.synthesize_and_play(clean_text)

        return True

    def run_loop(self):
        """Interactive loop for back-and-forth voice chat."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}======================================================{Colors.RESET}")
        print(f"{Colors.HEADER}{Colors.BOLD}          Medusa Voice Assistant (WSL Client)         {Colors.RESET}")
        print(f"{Colors.HEADER}{Colors.BOLD}======================================================{Colors.RESET}")
        print(f"Workspace: {os.getcwd()}")
        print(f"LLM:       {self.llm_url} (Model: {self.model_name})")
        print(f"TTS:       {self.tts_url} (Voice: {self.voice})")
        print(f"Pulse:     {os.environ.get('PULSE_SERVER', 'Default')}")
        print(f"Mode:      {'Push-to-Talk [Enter to Start/Stop]' if not self.duration else f'Timed ({self.duration}s)'}")
        print(f"Controls:  Press Ctrl+C to exit at any time.\n")

        while True:
            try:
                success = self.process_turn()
                if not success:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print(f"\n{Colors.GREEN}Exiting voice client. Goodbye!{Colors.RESET}")
                break


def main():
    parser = argparse.ArgumentParser(description="Medusa Voice Client (WSL)")
    parser.add_argument("--gateway", default=None, help="Optional external Medusa HTTP gateway URL (e.g. http://localhost:9000/v1/chat/completions)")
    parser.add_argument("--llm", default=DEFAULT_LLM_URL, help=f"Remote LLM API Base URL (default: {DEFAULT_LLM_URL})")
    parser.add_argument("--tts", default=DEFAULT_TTS_URL, help=f"F5-TTS Server URL (default: {DEFAULT_TTS_URL})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"LLM model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="TTS Voice name (default: jarvis)")
    parser.add_argument("--speed", type=float, default=1.0, help="TTS Voice speed multiplier")
    parser.add_argument("--stt-model", default="base.en", help="Whisper model (tiny.en, base.en, small.en, medium.en)")
    parser.add_argument("--stt-device", default="auto", choices=["auto", "cpu", "cuda"], help="STT compute device")
    parser.add_argument("--duration", type=float, default=None, help="Fixed recording duration in seconds (optional)")
    parser.add_argument("--input-file", type=str, default=None, help="Path to audio file to send as input")
    parser.add_argument("--text", type=str, default=None, help="Send text directly instead of recording audio")
    parser.add_argument("--no-tts", action="store_true", help="Disable audio playback (text-only reply)")
    parser.add_argument("--no-stream", action="store_true", help="Disable real-time thought streaming")
    parser.add_argument("--once", action="store_true", help="Run a single turn and exit")

    args = parser.parse_args()

    client = MedusaVoiceClient(
        gateway_url=args.gateway,
        llm_url=args.llm,
        tts_url=args.tts,
        model_name=args.model,
        voice=args.voice,
        speed=args.speed,
        stt_model=args.stt_model,
        stt_device=args.stt_device,
        stream=not args.no_stream,
        use_tts=not args.no_tts,
        duration=args.duration
    )

    if args.input_file:
        client.process_turn(audio_file=args.input_file)
    elif args.text:
        client.process_turn(text_input=args.text)
    elif args.once:
        client.process_turn()
    else:
        client.run_loop()


if __name__ == "__main__":
    main()

