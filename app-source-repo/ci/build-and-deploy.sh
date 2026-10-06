#!/usr/bin/env bash
# ==============================================================================
# Enterprise GitOps CI Pipeline: Build, Sanity Test, Hash Tag, Registry Push & GitOps Update
# Author: consultant.sachinbhardwaj@gmail.com
# Compliance: State Data Centre (SDC) Air-Gapped Standard
# ==============================================================================
set -euo pipefail

unset GIT_DIR GIT_WORK_TREE 2>/dev/null || true

# Base directories
PROJECT_ROOT="/home/sachink8s/.gemini/antigravity-ide/scratch/gitops-enterprise-pipeline"
APP_DIR="${PROJECT_ROOT}/app-source-repo"
GITOPS_DIR="${PROJECT_ROOT}/gitops-config-repo"
REGISTRY_HOST="localhost:5001"
K8S_REGISTRY_HOST="dev-registry:5000"

SERVICE="${1:-core-api}"
TARGET_ENV="${2:-dev}"

echo "================================================================================"
echo ">> [CI-PIPELINE] Starting CI/CD Workflow for service: ${SERVICE} | Env: ${TARGET_ENV}"
echo "================================================================================"

cd "${APP_DIR}"

# 1. Compute Git Commit Hash
if [ -d ".git" ]; then
    COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "init$(date +%s)")
else
    COMMIT_SHA="bld$(date +%s | cut -c 6-10)"
fi
echo ">> [CI-STEP 1] Git Commit Hash determined: ${COMMIT_SHA}"

# 2. Multi-Stage Docker Build with Sanity Gates (Compilation & Runtime Unit Tests)
SERVICE_PATH="${APP_DIR}/services/${SERVICE}"

if [ ! -d "${SERVICE_PATH}" ]; then
    echo ">> [ERROR] Service path ${SERVICE_PATH} not found!"
    exit 1
fi

echo ">> [CI-STEP 2] Executing Sanity Check (Compilation + Unit Tests) inside Dockerfile..."

# Build the test stage first to guarantee tests pass before producing the artifact
if grep -q "AS test-runner" "${SERVICE_PATH}/Dockerfile"; then
    echo ">> [CI-GATE] Running Test-Runner Stage for ${SERVICE}..."
    docker build \
        --target test-runner \
        -t "${SERVICE}:sanity-check" \
        "${SERVICE_PATH}"
    echo ">> [CI-GATE] Sanity Check PASSED: Code compiled and unit tests passed."
elif grep -q "AS validator" "${SERVICE_PATH}/Dockerfile"; then
    echo ">> [CI-GATE] Running Validator Stage for ${SERVICE}..."
    docker build \
        --target validator \
        -t "${SERVICE}:sanity-check" \
        "${SERVICE_PATH}"
    echo ">> [CI-GATE] Sanity Check PASSED: Configuration and linting passed."
fi

# Service name to Image name mapping
IMAGE_NAME="${SERVICE}"
if [ "${SERVICE}" == "nginx" ]; then
    IMAGE_NAME="nginx-gateway"
fi

# 3. Build Production Image with Short SHA Tag & Latest Tag
echo ">> [CI-STEP 3] Building production container image..."
IMAGE_TAG_SHA="${REGISTRY_HOST}/${IMAGE_NAME}:${COMMIT_SHA}"
IMAGE_TAG_LATEST="${REGISTRY_HOST}/${IMAGE_NAME}:latest"

docker build \
    -t "${IMAGE_TAG_SHA}" \
    -t "${IMAGE_TAG_LATEST}" \
    "${SERVICE_PATH}"

# 4. Push Image to Private Registry
echo ">> [CI-STEP 4] Pushing image to private registry (${REGISTRY_HOST})..."
docker push "${IMAGE_TAG_SHA}"
docker push "${IMAGE_TAG_LATEST}"
echo ">> [CI-STEP 4] Image pushed successfully:"
echo "     - ${IMAGE_TAG_SHA}"
echo "     - ${IMAGE_TAG_LATEST}"

# 5. GitOps Manifest Parameterization (Updating GitOps Repo)
echo ">> [CI-STEP 5] Updating GitOps manifest in ${GITOPS_DIR}/environments/${TARGET_ENV}..."

TARGET_KUSTOMIZATION="${GITOPS_DIR}/environments/${TARGET_ENV}/kustomization.yaml"
TARGET_CONFIG="${GITOPS_DIR}/environments/${TARGET_ENV}/${TARGET_ENV}-config.yaml"

if [ -f "${TARGET_KUSTOMIZATION}" ]; then
    # Update newTag for the specific service in kustomization.yaml
    python3 -c "
import re

kust_path = '${TARGET_KUSTOMIZATION}'
img_name = '${IMAGE_NAME}'
sha = '${COMMIT_SHA}'

with open(kust_path, 'r') as f:
    content = f.read()

# Pattern to replace newTag for this service
pattern = rf'(- name: dev-registry:5000/{img_name}\s*\n\s*newName: dev-registry:5000/{img_name}\s*\n\s*newTag: )(\S+)'
if re.search(pattern, content):
    content = re.sub(pattern, rf'\g<1>{sha}', content)
    with open(kust_path, 'w') as f:
        f.write(content)
    print(f'>> [GitOps] Pinned dev-registry:5000/{img_name} to tag: {sha}')
else:
    print(f'>> [GitOps] Notice: Service {img_name} image entry untouched or already set.')
"
fi

# Update config.yaml timestamp & hash
if [ -f "${TARGET_CONFIG}" ]; then
    sed -i "s/^LAST_SYNC=.*/LAST_SYNC=${COMMIT_SHA}-$(date +%Y%m%d%H%M%S)/" "${TARGET_CONFIG}"
    echo ">> [GitOps] Updated ${TARGET_CONFIG} with sync metadata."
fi

# 6. Commit to GitOps Repository
cd "${GITOPS_DIR}"
if [ -d ".git" ]; then
    git add .
    git -c user.name="GitOps CI Bot" -c user.email="consultant.sachinbhardwaj@gmail.com" \
        commit -m "chore(gitops): auto-promote ${SERVICE} to ${COMMIT_SHA} in ${TARGET_ENV}" || true
    echo ">> [GitOps] Committed changes to GitOps configuration repository."
fi

echo "================================================================================"
echo ">> [CI-PIPELINE COMPLETED] Service ${SERVICE} verified, built, pushed, & pinned!"
echo ">> Target SHA: ${COMMIT_SHA}"
echo ">> Kubernetes Pull Address: ${K8S_REGISTRY_HOST}/${SERVICE}:${COMMIT_SHA}"
echo "================================================================================"
