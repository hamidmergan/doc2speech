FROM python:3.12-slim

# ffmpeg joins the audio parts of a long text.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[ui]" \
    && useradd --create-home --uid 1000 app

USER app
EXPOSE 8000

# The web page: paste a text or drop a document, get an audio file back.
# Settings come from DOC2SPEECH_* environment variables, e.g. DOC2SPEECH_BASE_URL,
# DOC2SPEECH_MODEL and DOC2SPEECH_VOICE. They can also be typed into the page.
CMD ["doc2speech", "serve", "--host", "0.0.0.0", "--port", "8000"]
