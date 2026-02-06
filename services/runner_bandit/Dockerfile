FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Configuration via environment
ENV BANDIT_ALGORITHM=ucb1
ENV BANDIT_STATE_FILE=/tmp/bandit_state.json
# Set at deploy time:
# ENV BANDIT_GCS_BUCKET=blauweiss-mab-state
# ENV GITLAB_API_TOKEN=glpat-...
# ENV GCP_PROJECT=myk8sproject-207017
# ENV GCP_ZONE=europe-north2-a
# ENV GCP_INSTANCE=gitlab-runner-nordic

EXPOSE 8080

CMD ["uvicorn", "src.webhook_handler:app", "--host", "0.0.0.0", "--port", "8080"]
