FROM python:3.11-slim

# Install Samba and sudo
RUN apt-get update && \
    apt-get install -y samba samba-common-bin sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Expose port for web interface
EXPOSE 5000

# Command to run the application
CMD ["python", "run.py"]
