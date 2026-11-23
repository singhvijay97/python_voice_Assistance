
import os
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

import sounddevice as sd
from scipy.io.wavfile import write
from dotenv import load_dotenv
from deepgram import DeepgramClient
import pyttsx3
import requests

load_dotenv()

API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not API_KEY:
    raise RuntimeError("Set DEEPGRAM_API_KEY in your .env file")

deepgram = DeepgramClient()
speaker = pyttsx3.init()

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


def speak(text):
    print(f"Assistant: {text}")
    speaker.say(text)
    speaker.runAndWait()


def listen_and_transcribe():
    seconds = 10
    sample_rate = 16000

    speak("I am listening. Please speak now.")

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
    )
    sd.wait()

    with tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False
    ) as temp:
        audio_path = temp.name

    try:
        write(audio_path, sample_rate, audio)

        with open(audio_path, "rb") as audio_file:
            response = deepgram.listen.v1.media.transcribe_file(
                request=audio_file.read(),
                model="nova-3",
                language="en",
            )

        transcript = (
            response.results.channels[0]
            .alternatives[0]
            .transcript
        )

        print("You:", transcript)
        return transcript.strip()

    finally:
        Path(audio_path).unlink(missing_ok=True)


def download_file(url):
    parsed = urlparse(url)

    if parsed.scheme != "https" or not parsed.hostname:
        return "Please provide a valid HTTPS download URL."

    # Basic public-host check. Production apps need stronger
    # SSRF protections, redirect checks, and size limits.
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return "Downloads from local addresses are not allowed."

    try:
        with requests.get(
            url, stream=True, timeout=20, allow_redirects=False
        ) as response:
            response.raise_for_status()

            if response.is_redirect:
                return "Redirected downloads need URL verification."

            filename = Path(parsed.path).name
            if not filename or filename in {".", ".."}:
                filename = "downloaded_file"

            # Avoid overwriting an existing file.
            destination = DOWNLOAD_DIR / filename
            if destination.exists():
                destination = DOWNLOAD_DIR / (
                    f"downloaded_{filename}"
                )

            with open(destination, "wb") as output:
                for chunk in response.iter_content(8192):
                    if chunk:
                        output.write(chunk)

        return f"Downloaded file to {destination}"

    except requests.RequestException as error:
        return f"Download failed: {error}"


def handle_command(command):
    text = command.lower().strip()

    if not text:
        return "I could not understand that. Please try again."

    if "open amazon" in text:
        webbrowser.open("https://www.amazon.in/")
        return "Opening amazon"
    

    if text.startswith("search google for "):
        query = command[len("search google for "):].strip()
        from urllib.parse import quote_plus
        webbrowser.open(
            "https://www.google.com/search?q=" + quote_plus(query)
        )
        return f"Searching Google for {query}."

    if text.startswith("download file "):
        url = command[len("download file "):].strip()
        return download_file(url)

    if text in {"exit", "quit", "stop assistant"}:
        return "Goodbye."

    return (
        "I heard your command, but I do not have an action "
        "configured for it yet."
    )


def main():
    speak("Voice assistant started.")

    while True:
        try:
            command = listen_and_transcribe()
            result = handle_command(command)
            speak(result)

            if command.lower().strip() in {
                "exit", "quit", "stop assistant"
            }:
                break

        except KeyboardInterrupt:
            speak("Assistant stopped.")
            break
        except Exception as error:
            print("Error:", error)
            speak("Something went wrong. Please check the terminal.")


if __name__ == "__main__": 
    main()
    
