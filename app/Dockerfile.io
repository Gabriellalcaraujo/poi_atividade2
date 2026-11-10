FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY io_app.py .

ENV IO_DIR=/data

VOLUME ["/data"]

EXPOSE 8003

CMD ["python", "io_app.py"]
