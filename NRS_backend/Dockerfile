FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app \
	PIP_DEFAULT_TIMEOUT=180 PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
	PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
WORKDIR /app
RUN apt-get update \
	&& apt-get install -y --no-install-recommends sqlite3 \
	&& rm -rf /var/lib/apt/lists/*
COPY requirements-base.txt ./
RUN pip install --no-cache-dir -r requirements-base.txt

FROM base AS runtime
ENV PYTHONPATH=/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/NRS_backend
WORKDIR /app/NRS_backend
CMD ["uvicorn", "NRS_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
