FROM nvidia/cuda:12.6.0-runtime-ubuntu24.04

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ENV VENV_PATH=/opt/venv
RUN python3 -m venv "$VENV_PATH" && \
    "$VENV_PATH/bin/python" -m pip install --upgrade pip

COPY . .
RUN "$VENV_PATH/bin/pip" install --no-cache-dir -r requirements.txt

ENV PATH="$VENV_PATH/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
