ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install required packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bluez \
        bluez-tools \
        dbus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy data
COPY . /
WORKDIR /

# Set up environment
RUN pip3 install --no-cache-dir -r requirements.txt

# Create data directory
RUN mkdir -p /data

# Command to run
CMD [ "python3", "/run.py" ]
