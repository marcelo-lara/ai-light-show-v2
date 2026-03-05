FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

RUN pip install pyyaml playwright

# Install browser
RUN playwright install chromium

COPY qa/ /app/qa/
COPY qa/tests/ /app/qa/tests/

CMD ["python", "qa/runner.py", "qa/tests/song_analysis_smoke.yaml"]
