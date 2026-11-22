FROM python:3.12-slim

# Optional PyPI mirror for air-gapped builds. Build args are kept in the image
# history, so the URL must not contain credentials.
ARG PIP_INDEX_URL=""

WORKDIR /app

# Runtime dependencies only: requirements.txt lists dev tools after the
# "# Development" header.
COPY requirements.txt .
RUN [ -n "$PIP_INDEX_URL" ] || unset PIP_INDEX_URL; \
    sed '/^# Development/,$d' requirements.txt > runtime-requirements.txt \
    && pip install --no-cache-dir -r runtime-requirements.txt \
    && rm runtime-requirements.txt

COPY src ./src

USER 1001
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port \"${COMPLIANCE_PORT:-8000}\" --log-level \"$(echo \"${COMPLIANCE_LOG_LEVEL:-info}\" | tr A-Z a-z)\""]
