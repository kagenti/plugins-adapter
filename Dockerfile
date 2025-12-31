# Super simple Dockerfile
#FROM python:3.12.12
FROM public.ecr.aws/docker/library/python:3.12.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gcc g++ \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy Python dependencies and source
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p src/resources

COPY src/ ./src/
COPY resources ./src/resources/
RUN mkdir resources
RUN mkdir src
RUN mkdir contextforge-plugins-python
RUN mkdir nemo

COPY src/ ./src/
COPY resources ./resources/
COPY plugins ./plugins/
COPY contextforge-plugins-python ./contextforge-plugins-python/
COPY nemo ./nemo/

WORKDIR /app/src
# Expose the gRPC port
EXPOSE 50052

# Run the server
CMD ["python", "server.py"]
