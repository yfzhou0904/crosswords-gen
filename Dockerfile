FROM python:3.12-slim as python-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    FLASK_APP=backend/app.py \
    FLASK_ENV=production
WORKDIR /app
COPY backend/requirements.txt /app/backend/
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install -r /app/backend/requirements.txt

FROM node:22 as frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python-base as final
COPY --from=python-base /venv /venv
WORKDIR /app
COPY backend/ /app/backend/
COPY --from=frontend-builder /app/frontend/build /app/frontend/build
RUN mkdir /app/data
EXPOSE 80
CMD ["python3", "backend/web.py"]
