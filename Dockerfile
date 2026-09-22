FROM python:3.14-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./


RUN uv pip install --system .

RUN addgroup --system app && adduser --system --group app

# ---

FROM python:3.14-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


WORKDIR /app

COPY --from=base /etc/passwd /etc/passwd
COPY --from=base /etc/group /etc/group

COPY --from=base /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

COPY . .

# Note: collectstatic is run at container startup (in docker-compose.yml)
# because it needs environment variables that are only available at runtime

RUN chown -R app:app /app

USER app

EXPOSE 8000

# Gunicorn command with production settings
# Alternative: Use config file with --config gunicorn_config.py
# Run migrations and collectstatic, then start gunicorn
CMD python manage.py collectstatic --noinput && python manage.py migrate && gunicorn SVEX_Project.wsgi:application --bind 0.0.0.0:8000 --workers 5 --timeout 120 --worker-class sync --access-logfile - --error-logfile -