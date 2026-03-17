FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py report_builder.py ai_service.py database.py ./
COPY templates/ templates/

# Create the data directory (will be overridden by volume mount)
RUN mkdir -p /app/data/logs

# Ensure print() output appears immediately in docker logs
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "600", "app:app"]
