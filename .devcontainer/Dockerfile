FROM mcr.microsoft.com/devcontainers/python:3.11

# System dependencies for dnspython, lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*