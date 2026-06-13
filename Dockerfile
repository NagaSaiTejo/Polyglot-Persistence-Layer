FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# create empty retry_queue.json to avoid mounting issues if it doesn't exist
RUN touch retry_queue.json

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
