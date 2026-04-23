FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY server.py .
COPY banned_words.txt .

EXPOSE 5000

CMD ["python", "-u", "server.py"]