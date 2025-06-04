# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
#ARG BUILD_FROM
FROM ghcr.io/home-assistant/amd64-base-python:latest
#FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install required packages
# Add retry logic for Alpine repositories which can be unreliable
RUN apk --no-cache update || \
    (sleep 2 && apk --no-cache update) || \
    (sleep 5 && apk --no-cache update) && \
    apk add --no-cache \
        bluez \
        dbus \
    && rm -rf /var/cache/apk/*

# Copy data
COPY . /
WORKDIR /

# Set up environment
RUN pip3 install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p /data

# Command to run
CMD [ "python3", "/run.py" ]
