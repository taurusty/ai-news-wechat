FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for lxml, Pillow, fonts
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
     curl \
     ca-certificates \
     libxml2-dev \
     libxslt1-dev \
     zlib1g-dev \
     libjpeg62-turbo-dev \
     libpng-dev \
     fontconfig \
     fonts-dejavu \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY config /app/config

RUN mkdir -p /app/output /app/logs /app/db

CMD ["python", "-m", "app.main", "--date", "today"]
