# Whisper XPU WebUI

A web application that enables you to perform Automatic Speech Recognition (ASR) transcription tasks using OpenAI's Whisper model completely accelerated by your Intel Arc Graphics (XPU).

![Intel ARC XPU Whisper WebUI](static/favicon.ico) *A minimalist web application powered by Flask and Intel Extension for PyTorch (IPEX).*
 
## Features

- **Intel Arc (XPU) Acceleration**: Offloads audio transcription completely to dedicated hardware using IPEX.
- **Queue System**: Transcriptions are processed sequentially in the background. No broken threads or unmanaged parallel execution.
- **Model Selection**: Switch seamlessly between `tiny.en`, `base`, `medium`, and `large` Whisper models.
- **Modern Minimal UI**: Built with pure HTML/CSS vanilla code and features drag-and-drop file upload.
- **Dockerized**: Fully containerized setup for ease of deployment. 
 
## Prerequisites

Make sure you have the following installed:
- `podman` or `docker` 
- `podman-compose` or `docker-compose`
- An Intel Arc GPU (or compatible integrated Graphics supporting Level Zero and SYCL)
- Required drivers: `intel-compute-runtime`, `intel-media-driver`

## Setup & Run

The application is completely containerized. Start the application by running the following command in the root folder:

```bash
# Using Podman
podman-compose up -d --build

# Or using Docker
docker compose up -d --build
```

The initial run may take some time as it downloads the `intel-extension-for-pytorch` base image.

## Usage

1. Open your web browser and go to `http://localhost:5000`.
2. Drag and drop your audio or video file (e.g., MP4, MP3, WAV) into the upload area.
3. Select your desired transcription model.
4. Click **Transcription**.
5. Wait for the queue task to fetch the model, verify the GPU, and transcribe. 
6. Once completed, a **Download SRT** button will appear automatically for you to save the generated subtitle file.

## Available Models

- `tiny`, `tiny.en`
- `base`, `base.en`
- `small`, `small.en`
- `medium`, `medium.en`
- `large`, `large-v1`, `large-v2`, `large-v3`

*Note: Models default to using CPU when GPU isn't found. Because this is hard-locked to Intel Arc (`--device xpu`), the container requires `/dev/dri` to function.*

## Volumes

By default, the `docker-compose.yaml` bounds models, outputs, and uploads to the host machine for persistence.
- `./whisper-models`: Contains all heavy downloaded PyTorch weights. 
- `./uploads`: Incoming media waiting to be processed.
- `./outputs`: Completed `.srt` transcription files.

## Troubleshooting

- **Models download every time / Space issue:** The models are saved to `~/.cache/whisper` inside the container which is mapped to `./whisper-models` on your host. If they download continuously, check permissions on that folder.
- **Performance:** For huge speedups, it requires `intel-extension-for-pytorch`. Currently, this uses the base CLI of `whisper`. Due to PyTorch overhead and float32 inference, you may experience near-realtime performance. More complex float16/SYCL `whisper.cpp` implementations are required for ultra-fast generation.
