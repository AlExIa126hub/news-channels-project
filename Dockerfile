FROM python:3.12-slim

WORKDIR /app

COPY server.py .
COPY banned_words.txt .

EXPOSE 5000

CMD ["python", "server.py"]