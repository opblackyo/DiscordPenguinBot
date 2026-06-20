FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY apps ./apps
RUN pip install --no-cache-dir .

CMD ["python", "-m", "apps.bot.penguin_bot.main"]
