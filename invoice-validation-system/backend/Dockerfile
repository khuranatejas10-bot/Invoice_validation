# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables to prevent Python from writing .pyc files 
# and to ensure console output is not buffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for OCR and PDF processing
# - tesseract-ocr: Core OCR engine
# - poppler-utils: Required by pdf2image to parse PDF files
# - libgl1 & libglib2.0-0: Required by OpenCV (often used in OCR pipelines)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend application code
COPY . .

# Expose the port your app will run on
EXPOSE 8000

# Command to run the application 
# Note: If your main FastAPI file is named 'app.py' instead of 'main.py', change 'main:app' to 'app:app'
CMD ["sh", "-c", "python -m database.init_db && uvicorn main:app --host 0.0.0.0 --port 8000"]
