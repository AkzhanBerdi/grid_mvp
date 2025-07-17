# Dockerfile for GridTrader Pro
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/logs data/backups test_logs

# Set permissions
RUN chmod +x run_production_tests.sh

# Create non-root user for security
RUN useradd -m -u 1000 gridtrader && \
    chown -R gridtrader:gridtrader /app
USER gridtrader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "from database.db_setup import DatabaseSetup; db = DatabaseSetup(); print('Health OK')" || exit 1

# Expose port (if needed for web interface)
EXPOSE 8080

# Environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Default command - run tests first, then start service
CMD ["sh", "-c", "python3 final_fixed_test_runner.py && python3 main.py"]
