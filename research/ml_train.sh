#!/bin/bash
# AGI in md — ML Training Runner (Stateful)
# Prevents cost explosions by properly handling deduplication and state management
# Usage: bash ml_train.sh [model|all] [dataset|all]
#
# Key differences from run.sh:
# - Checks for existing checkpoints before training (prevents duplicate GPU hours)
# - Maintains training state/metadata (enables resumable runs)
# - Provides cost estimation and state visibility
# - NOT suitable for stateless parallel experiments

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TRAIN_DIR="$PROJECT_DIR/output/training"
STATE_DIR="$TRAIN_DIR/state"
CHECKPOINTS_DIR="$TRAIN_DIR/checkpoints"

mkdir -p "$TRAIN_DIR" "$STATE_DIR" "$CHECKPOINTS_DIR"

MODEL="${1:-all}"
DATASET="${2:-all}"

# ---- Models and Datasets ----

declare -A MODELS
MODELS[small]="params=5M"
MODELS[medium]="params=50M"
MODELS[large]="params=500M"

declare -A DATASETS
DATASETS[tiny]="samples=10k"
DATASETS[small]="samples=100k"
DATASETS[medium]="samples=1M"

# ---- Training function ----

train_model() {
    local model_name="$1"
    local dataset_name="$2"
    local checkpoint_file="$CHECKPOINTS_DIR/${model_name}_${dataset_name}.ckpt"
    local state_file="$STATE_DIR/${model_name}_${dataset_name}.json"
    local log_file="$TRAIN_DIR/${model_name}_${dataset_name}.log"

    # ── CRITICAL GUARD: Check for existing checkpoint ──
    # This prevents the cost-explosion bug: duplicate training runs
    # Each omitted check = potential $300+ wasted GPU hours
    if [[ -f "$checkpoint_file" ]]; then
        echo "  Skipping: $model_name / $dataset_name (checkpoint exists — avoid retraining)"

        # Load training state to show progress
        if [[ -f "$state_file" ]]; then
            local status=$(grep '"status"' "$state_file" | head -1)
            echo "    Status: $status"
        fi
        return
    fi

    # Verify state file doesn't exist without checkpoint (corruption detection)
    if [[ -f "$state_file" && ! -f "$checkpoint_file" ]]; then
        echo "  WARNING: State exists but checkpoint missing for $model_name/$dataset_name"
        echo "    Possible previous failure. Investigate before retraining."
        return 1
    fi

    echo "  Training: $model_name / $dataset_name ..."

    # Initialize training state
    cat > "$state_file" <<EOF
{
    "model": "$model_name",
    "dataset": "$dataset_name",
    "status": "in_progress",
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "estimated_hours": "12",
    "estimated_cost": "\$300"
}
EOF

    # Simulate training (replace with actual training code)
    local start_time=$SECONDS
    {
        echo "Training $model_name on $dataset_name..."
        # Actual training command would go here
        # python train.py --model "$model_name" --dataset "$dataset_name" \
        #     --checkpoint "$checkpoint_file" > "$log_file" 2>&1

        # For now, just create a mock checkpoint
        touch "$checkpoint_file"
    } || {
        # On failure, preserve state for debugging
        cat >> "$state_file" <<EOF
    "error": "Training failed",
    "failed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF
        return 1
    }

    local elapsed=$(( SECONDS - start_time ))

    # Update state file on success
    cat > "$state_file" <<EOF
{
    "model": "$model_name",
    "dataset": "$dataset_name",
    "status": "completed",
    "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "completed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "elapsed_seconds": $elapsed,
    "checkpoint": "$checkpoint_file"
}
EOF

    echo "    ✓ Done (${elapsed}s) -> Checkpoint: $checkpoint_file"
}

# ---- Main loop ----

echo "========================================"
echo " ML Training Runner (Stateful)"
echo " Model filter: $MODEL"
echo " Dataset filter: $DATASET"
echo "========================================"
echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "  - This script checks for existing checkpoints before training"
echo "  - Skipped runs are NOT failures — they prevent wasted GPU hours"
echo "  - State files track training progress and enable resumable runs"
echo "  - Deleting a checkpoint to 'retry' is safe but expensive ($300+ per retry)"
echo ""

count=0
skipped=0

for model_name in "${!MODELS[@]}"; do
    if [[ "$MODEL" != "all" && "$MODEL" != "$model_name" ]]; then
        continue
    fi

    for dataset_name in "${!DATASETS[@]}"; do
        if [[ "$DATASET" != "all" && "$DATASET" != "$dataset_name" ]]; then
            continue
        fi

        if train_model "$model_name" "$dataset_name"; then
            count=$((count + 1))
        else
            skipped=$((skipped + 1))
        fi
    done
done

echo ""
echo "========================================"
echo " Training Summary"
echo " New trainings: $count"
echo " Skipped (deduped): $skipped"
echo " Results in: $TRAIN_DIR/"
echo " State tracking: $STATE_DIR/"
echo " Checkpoints: $CHECKPOINTS_DIR/"
echo "========================================"
echo ""
echo "⚠️  Cost Protection:"
echo "  - Each skipped run = ~$300 GPU time saved"
echo "  - Total savings this run: \$$(( skipped * 300 ))"
echo ""
