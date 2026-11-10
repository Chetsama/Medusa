import requests
import io
import soundfile as sf

# Server endpoint (change localhost to your Gaming PC's IP if querying from another machine)
API_URL = "http://localhost:5000/v1/audio/speech"

payload = {
    "model": "f5-tts",
    "input": "Good evening, sir. All diagnostic tests have completed successfully.",
    "voice": "jarvis",
    "speed": 1.0,
    "response_format": "wav"
}

print(f"Sending request to {API_URL}...")
response = requests.post(API_URL, json=payload)

if response.status_code == 200:
    output_file = "test_output.wav"
    with open(output_file, "wb") as f:
        f.write(response.content)
    print(f"Success! Audio saved to {output_file}")
else:
    print(f"Error ({response.status_code}): {response.text}")
