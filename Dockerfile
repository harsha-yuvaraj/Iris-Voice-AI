# Use the official Python 3.13 slim image
FROM python:3.13-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Expose the port the app will run on
EXPOSE ${PORT}

# Run the application using Daphne (ASGI server)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8080", "IrisVoiceAI.asgi:application"]

