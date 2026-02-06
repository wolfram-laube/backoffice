FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# GCS persistence (set BANDIT_GCS_BUCKET to enable)
ENV BANDIT_ALGORITHM=ucb1
ENV BANDIT_STATE_FILE=/tmp/bandit_state.json
# ENV BANDIT_GCS_BUCKET=blauweiss-mab-state  ← set at deploy time

EXPOSE 8080

CMD ["uvicorn", "src.webhook_handler:app", "--host", "0.0.0.0", "--port", "8080"]
