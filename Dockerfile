FROM python:3.10

WORKDIR /app

# Instalace FFmpeg a závislostí
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Instalace Python závislostí
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopírování kódu
COPY . .

# Nastavení pro lepší využití paměti s velkými modely
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb=256

# Spuštění bota
CMD ["python", "bot.py"]
