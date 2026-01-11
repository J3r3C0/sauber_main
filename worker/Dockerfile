FROM python:3.11-slim

WORKDIR /worker

# Unbuffered Python output for Docker logs
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker_loop.py .

CMD ["python", "-u", "worker_loop.py"]
