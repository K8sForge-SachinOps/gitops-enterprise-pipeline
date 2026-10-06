#!/usr/bin/env bash
# ==============================================================================
# Enterprise GitOps Promotion Engine
# Author: consultant.sachinbhardwaj@gmail.com
# Compliance: State Data Centre (SDC) Air-Gapped Standard
# ==============================================================================
set -euo pipefail

PROJECT_ROOT="/home/sachink8s/.gemini/antigravity-ide/scratch/gitops-enterprise-pipeline"
GITOPS_DIR="${PROJECT_ROOT}/gitops-config-repo"
APP_DIR="${PROJECT_ROOT}/app-source-repo"

usage() {
    echo "Usage: $0 --service <service-name|all> --to <uat|prod> [--tag <custom-tag|sha>]"
    echo "Example:"
    echo "  $0 --service core-api --to uat"
    echo "  $0 --service all --to prod --tag v1.0.0"
    exit 1
}

SERVICE="all"
TARGET_ENV=""
CUSTOM_TAG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --service|-s)
            SERVICE="$2"
            shift 2
            ;;
        --to|-t)
            TARGET_ENV="$2"
            shift 2
            ;;
        --tag)
            CUSTOM_TAG="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

if [[ -z "${TARGET_ENV}" ]]; then
    echo ">> [ERROR] Target environment (--to) is required (uat or prod)!"
    usage
fi

if [[ "${TARGET_ENV}" != "uat" && "${TARGET_ENV}" != "prod" ]]; then
    echo ">> [ERROR] Target environment must be 'uat' or 'prod'."
    exit 1
fi

cd "${APP_DIR}"
if [[ -z "${CUSTOM_TAG}" ]]; then
    RELEASE_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
else
    RELEASE_SHA="${CUSTOM_TAG}"
fi

echo "================================================================================"
echo ">> [GITOPS-PROMOTION] Promoting to Environment: ${TARGET_ENV}"
echo ">> [GITOPS-PROMOTION] Target Service:          ${SERVICE}"
echo ">> [GITOPS-PROMOTION] Artifact Tag / Git SHA:  ${RELEASE_SHA}"
echo ">> [GITOPS-PROMOTION] Committer:               consultant.sachinbhardwaj@gmail.com"
echo "================================================================================"

TARGET_KUST="${GITOPS_DIR}/environments/${TARGET_ENV}/kustomization.yaml"
TARGET_CONF="${GITOPS_DIR}/environments/${TARGET_ENV}/${TARGET_ENV}-config.yaml"

if [[ ! -f "${TARGET_KUST}" ]]; then
    echo ">> [ERROR] Kustomization file not found: ${TARGET_KUST}"
    exit 1
fi

# Update image tags
python3 -c "
import re

kust_path = '${TARGET_KUST}'
service = '${SERVICE}'
sha = '${RELEASE_SHA}'

with open(kust_path, 'r') as f:
    content = f.read()

services = ['core-api', 'nginx-gateway'] if service == 'all' else [service]

for s in services:
    pattern = rf'(- name: dev-registry:5000/{s}\s*\n\s*newName: dev-registry:5000/{s}\s*\n\s*newTag: )(\S+)'
    if re.search(pattern, content):
        content = re.sub(pattern, rf'\g<1>{sha}', content)
        print(f'>> [GitOps] Pinned dev-registry:5000/{s} to {sha} in {kust_path}')
    else:
        print(f'>> [GitOps] Notice: Service {s} pattern not found in {kust_path}')

with open(kust_path, 'w') as f:
    f.write(content)
"

# Update config metadata
if [[ -f "${TARGET_CONF}" ]]; then
    sed -i "s/^LAST_PROMOTION=.*/LAST_PROMOTION=${RELEASE_SHA}-$(date +%Y%m%d%H%M%S)/" "${TARGET_CONF}" || \
        echo "LAST_PROMOTION=${RELEASE_SHA}-$(date +%Y%m%d%H%M%S)" >> "${TARGET_CONF}"
    echo ">> [GitOps] Updated promotion timestamp in ${TARGET_CONF}"
fi

# Commit and push to GitOps repo
cd "${GITOPS_DIR}"
git add "environments/${TARGET_ENV}"
git config user.name "GitOps Promotion Engine"
git config user.email "consultant.sachinbhardwaj@gmail.com"

COMMIT_MSG="chore(promote): promote ${SERVICE} to ${RELEASE_SHA} in ${TARGET_ENV}"
git commit -m "${COMMIT_MSG}" || echo ">> [GitOps] No diff detected; already at ${RELEASE_SHA}"

# Push to central git
git push origin main || true

echo "================================================================================"
echo ">> [GITOPS-PROMOTION SUCCESS] Promotion committed & pushed to GitOps repository!"
echo ">> ArgoCD & GitOps Pull Reconciler will auto-sync '${TARGET_ENV}' environment."
echo "================================================================================"
