FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --system neurovision && useradd --system --gid neurovision neurovision
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DEBUG=true python manage.py collectstatic --noinput && mkdir -p /app/media && chown -R neurovision:neurovision /app
USER neurovision
EXPOSE 9131
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:9131", "--workers", "2", "--timeout", "180", "--access-logfile", "-"]
