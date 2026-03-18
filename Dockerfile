FROM intel/intel-extension-for-pytorch:2.7.10-xpu

ENV USE_XETLA=OFF
ENV SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1
ENV SYCL_CACHE_PERSISTENT=1
ENV PYTHONUNBUFFERED=1

# Install system required packages
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for Flask webapp and OpenAI Whisper
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --ignore-installed blinker && \
    pip install --no-cache-dir flask werkzeug openai-whisper

# Set the working directory to /app
WORKDIR /app

# Copy the application code
COPY . /app/

# Expose the Flask port
EXPOSE 5000

# Start Flask on all interfaces
CMD ["python", "app.py"]
