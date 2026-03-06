#FROM python:3.12.12
FROM public.ecr.aws/docker/library/python:3.12.12-slim

# Build argument to specify which plugin examples to include dependencies for
# Comma-separated list of plugin names (e.g., "nemo" or "nemo,other_plugin")
ARG PLUGIN_DEPS=""

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

# This can be restricted to particular "built-in" example plugins
COPY plugins ./plugins/

# Install plugin-specific dependencies based on PLUGIN_DEPS argument
# This depends on plugins having requirements.txt in the directory
# and could be subject to error depending on how a plugin is structured.
# Usage: docker build --build-arg PLUGIN_DEPS="nemo" -t plugins-adapter .
# Or for multiple: docker build --build-arg PLUGIN_DEPS="nemo,other_plugin" -t plugins-adapter .
RUN if [ -n "$PLUGIN_DEPS" ]; then \
        echo "Installing dependencies for plugins: $PLUGIN_DEPS"; \
        echo "$PLUGIN_DEPS" | tr ',' '\n' | while read plugin; do \
            plugin=$(echo "$plugin" | xargs); \
            if [ -n "$plugin" ]; then \
		plugin_dir="plugins/examples/$plugin"; \
                req_file="$plugin_dir/pyproject.toml"; \
                if [ -f "$req_file" ]; then \
                    echo "Installing dependencies from $plugin_dir"; \
                    pip install --no-cache-dir $plugin_dir; \
                else \
                    echo "Warning: No pyproject.tomml found for plugin '$plugin' at $req_file"; \
                fi; \
            fi; \
        done; \
    else \
        echo "No plugin dependencies specified (use --build-arg PLUGIN_DEPS=\"plugin1,plugin2\" to include)"; \
    fi

# Expose the gRPC port
EXPOSE 50052

# Run the server
CMD ["python", "src/server.py"]
