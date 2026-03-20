FROM python:3.12-slim

WORKDIR /app

# Install uv for fast installs
RUN pip install --no-cache-dir uv

# Install dependencies first (layer cache)
COPY pyproject.toml .
RUN uv pip install --system -e ".[dev]"

# Download NLTK data needed for stemming
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

COPY . .

CMD ["pytest"]
