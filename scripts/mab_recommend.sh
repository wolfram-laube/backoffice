#!/usr/bin/env bash
# =============================================================================
# MAB Recommender - Queries MAB for optimal runner tag
# =============================================================================
# Outputs a dotenv artifact with MAB_RUNNER_TAG variable
# Usage:
#   script:
#     - bash scripts/mab_recommend.sh
#   artifacts:
#     reports:
#       dotenv: mab.env
# =============================================================================

MAB_URL="${MAB_SERVICE_URL:-https://runner-bandit-m5cziijwqa-lz.a.run.app}"
JOB_TYPE="${1:-default}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  MAB Runner Recommendation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -sf "${MAB_URL}/recommend?job_type=${JOB_TYPE}" 2>&1)

if [[ -z "$RESPONSE" ]]; then
    echo "⚠️  MAB service unreachable, falling back to docker-any"
    echo "MAB_RUNNER_TAG=docker-any" > mab.env
    echo "MAB_RUNNER_NAME=fallback" >> mab.env
    exit 0
fi

RUNNER_TAG=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['recommended_tag'])" 2>/dev/null || echo "docker-any")
RUNNER_NAME=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['recommended_runner'])" 2>/dev/null || echo "unknown")
OBSERVATIONS=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin)['total_observations'])" 2>/dev/null || echo "0")

echo "  Runner: $RUNNER_NAME"
echo "  Tag:    $RUNNER_TAG"
echo "  Based on $OBSERVATIONS observations"
echo ""

# Write dotenv artifact
echo "MAB_RUNNER_TAG=${RUNNER_TAG}" > mab.env
echo "MAB_RUNNER_NAME=${RUNNER_NAME}" >> mab.env
echo "MAB_OBSERVATIONS=${OBSERVATIONS}" >> mab.env

echo "✅ Written to mab.env"
cat mab.env
