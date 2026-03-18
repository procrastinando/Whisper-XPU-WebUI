import os
import sys
import torch
import whisper
import intel_extension_for_pytorch as ipex

def main():
    if len(sys.argv) < 3:
        print("Usage: python transcribe_xpu.py <audio_file_path> <model_name>")
        sys.exit(1)

    audio_file_path = sys.argv[1]
    model_name = sys.argv[2]

    # Load the Whisper model on the Intel Arc XPU using float16 for speed.
    print(f"Loading {model_name} model onto XPU...")
    model = whisper.load_model(model_name, device="xpu")
    
    # Let IPEX handle mixed precision/float16 automatically.
    # Put the model into evaluation mode for inference
    model.eval()

    # Intel Extension for PyTorch Optimization
    print("Running IPEX optimization...")
    model = ipex.optimize(model, dtype=torch.float16, optimizer=None)

    print("Transcribing...")
    
    # The default transcribe method does not provide real-time progress by default,
    # but the whole process will be much faster.
    # Note: fp16=True is explicitly passed to enforce half-precision decoding.
    result = model.transcribe(audio_file_path, fp16=True)

    # Standard Whisper CLI-like output format for time segments.
    # [00:00.000 --> 00:08.000]  Some text
    def format_timestamp(seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02}:{secs:06.3f}"

    for segment in result["segments"]:
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        text = segment['text']
        print(f"[{start} --> {end}] {text}")

if __name__ == "__main__":
    main()
