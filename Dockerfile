#FROM python:3.12.12
FROM public.ecr.aws/docker/library/python:3.12.12-slim

# Set shell options for safer script execution
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Build argument to specify which plugin examples to include dependencies for
# Comma-separated list of plugin names (e.g., "nemo" or "nemo,other_plugin")
ARG PLUGIN_DEPS=""

RUN apt-get update \
    && apt-get install -y --no-install-recommends git gcc g++ \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/*

COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

# Create non-root user for running the application with home directory
# Using UID/GID 1000 to match Kubernetes securityContext
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies and source
COPY pyproject.toml .
RUN uv sync --no-dev
RUN mkdir -p src/resources

COPY src/ ./src/
COPY resources ./src/resources/

# This can be restricted to particular "built-in" example plugins
COPY plugins ./plugins/

# Install plugin-specific dependencies based on PLUGIN_DEPS argument
# Plugins must have a pyproject.toml in their directory.
# Usage: docker build --build-arg PLUGIN_DEPS="nemo" -t plugins-adapter .
# Or for multiple: docker build --build-arg PLUGIN_DEPS="nemo,other_plugin" -t plugins-adapter .
RUN if [ -n "$PLUGIN_DEPS" ]; then \
        echo "Installing dependencies for plugins: $PLUGIN_DEPS"; \
        echo "$PLUGIN_DEPS" | tr ',' '\n' | while read -r plugin; do \
            plugin=$(echo "$plugin" | xargs); \
            if [ -n "$plugin" ]; then \
                plugin_dir="plugins/examples/$plugin"; \
                req_file="$plugin_dir/pyproject.toml"; \
                if [ -f "$req_file" ]; then \
                    echo "Installing dependencies from $plugin_dir"; \
                    uv pip install --no-cache "$plugin_dir"; \
                else \
                    echo "ERROR: No pyproject.toml found for plugin '$plugin' at $req_file"; \
                    echo "Available plugins:"; \
                    find plugins/examples/ -maxdepth 1 -type d ! -name examples -exec basename {} \; | sort; \
                    exit 1; \
                fi; \
            fi; \
        done; \
    else \
        echo "No plugin dependencies specified (use --build-arg PLUGIN_DEPS=\"plugin1,plugin2\" to include)"; \
    fi

# Change ownership of app directory and home directory to non-root user
RUN chown -R appuser:appuser /app && \
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Set environment variable for uv cache
ENV UV_CACHE_DIR=/home/appuser/.cache/uv

# Expose the gRPC port
EXPOSE 50052

# Run the server
CMD ["uv", "run", "python", "src/server.py"]
