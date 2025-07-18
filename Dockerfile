# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080"]
