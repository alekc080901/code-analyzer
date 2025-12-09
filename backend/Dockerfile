FROM python:3.9-slim

WORKDIR /app

# Set unbuffered output to see logs immediately
ENV PYTHONUNBUFFERED=1

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use python -m uvicorn to ensure it's found in path
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
