FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Set PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Default command
CMD ["python", "-m", "app"]
