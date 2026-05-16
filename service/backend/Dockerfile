FROM python:3.11-slim

WORKDIR /app

# Configure apt to use Aliyun mirrors (Chinese mirror for faster downloads)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# Install system dependencies for Playwright
# These libraries are required for Chromium to run in headless mode
RUN apt-get update && apt-get install -y \
    # Basic utilities
    wget \
    gnupg \
    curl \
    # Node.js for Playwright CLI
    nodejs \
    npm \
    # GTK and graphics libraries
    libglib2.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    # Audio and D-Bus
    libasound2 \
    libatspi2.0-0 \
    libdbus-1-3 \
    # Network and security
    libnss3 \
    libnspr4 \
    # X11 libraries
    libx11-6 \
    libxcb1 \
    libexpat1 \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Try installing with retry logic and fallback to default PyPI
RUN pip install --no-cache-dir -r requirements.txt || \
    pip config set global.index-url https://pypi.org/simple/ && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers as root (system deps already installed above)
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
RUN playwright install chromium

# Install Claude Code CLI (for Zhipu AI compatibility via HTTP API)
# Install to system-wide location accessible to all users including appuser
# Use npm prefix to install directly to /usr/local
RUN npm config set prefix '/usr/local' && \
    npm install -g @anthropic-ai/claude-code

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser/.cache/ms-playwright

# Switch to non-root user
USER appuser

# Copy application code
COPY . --chown=appuser:appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
