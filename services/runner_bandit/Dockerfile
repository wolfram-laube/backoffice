FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV BANDIT_STATE_FILE=/data/bandit_state.json
ENV BANDIT_ALGORITHM=ucb1

EXPOSE 8080

CMD ["uvicorn", "src.webhook_handler:app", "--host", "0.0.0.0", "--port", "8080"]
