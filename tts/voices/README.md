# Voices Directory for F5-TTS

Place reference audio files and transcripts in this directory for zero-shot voice cloning.

## How to add a Voice (e.g., J.A.R.V.I.S.):

1. **Audio File (`<voice_name>.wav` or `.mp3`)**:
   - Provide a clean 5–15 second audio clip with no background music/noise.
   - Example: `jarvis.wav`

2. **Transcript File (`<voice_name>.txt`)**:
   - Create a text file with the exact same name containing the transcript of that clip.
   - Example: `jarvis.txt`
   - Content: `At your service, sir. All systems are operational.`

## Usage:
* When you call the `/v1/audio/speech` or `/v1/tts` endpoint with `"voice": "jarvis"`, the server automatically pairs `jarvis.wav` with `jarvis.txt`.
* If no voice is specified in the request, the server will default to the first available audio file in this directory.
