# Enterprise GitOps Pipeline Architecture & Blueprint

---

## 1. Executive Summary

This architecture implements a cloud-native, air-gapped, pull-based GitOps CI/CD delivery platform matching the technical standards of leading product companies (Google, Netflix, Red Hat, Intuit). The platform is currently configured on an Ubuntu local development cluster (`dev`) and is designed for direct lift-and-shift installation onto bare-metal or virtualized infrastructure at a **State Data Centre (SDC)**.

---

## 2. Core Architecture Topology

```
+---------------------------------------------------------------------------------------------------+
|                                     DEVELOPER WORKSTATION                                         |
|                                                                                                   |
|  Developer: consultant.sachinbhardwaj@gmail.com                                                   |
|  Repo: app-source-repo/                                                                           |
|                                                                                                   |
|  1. Developer modifies code / config                                                              |
|  2. git commit -m "..." && git push origin main                                                   |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                                    CENTRAL GIT SERVER                                             |
|                                                                                                   |
|  Central Bare Git Repositories:                                                                   |
|   - git-server/app.git      (Application Source Code)                                             |
|   - git-server/gitops.git   (Declarative Kubernetes GitOps Manifests)                             |
|                                                                                                   |
|  Trigger: Server-Side 'post-receive' Hook / Webhook Listener (Port 9000)                          |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                           AUTOMATED CI PIPELINE (PUSH-TRIGGERED)                                  |
|                                                                                                   |
|  Script: ci/build-and-deploy.sh                                                                   |
|                                                                                                   |
|  [GATE 1] Syntax & Bytecode Compilation:                                                          |
|           python3 -m py_compile / nginx -t                                                        |
|  [GATE 2] Runtime Unit Test Execution (Inside Multi-Stage Dockerfile):                            |
|           pytest -v --tb=short tests/test_api.py                                                  |
|           (Build halts immediately if any test fails. Zero broken artifacts reach registry)       |
|  [GATE 3] Image Packaging & Short-SHA Tagging:                                                    |
|           dev-registry:5000/<service>:<short-git-sha>                                             |
|  [GATE 4] Push to Private Docker Container Registry (localhost:5001 / dev-registry:5000)          |
|  [GATE 5] Manifest Parameterization:                                                              |
|           Automatically updates target environment overlay (dev/kustomization.yaml)               |
|           Commits release tag to gitops-config-repo                                               |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                         GITOPS SINGLE SOURCE OF TRUTH (PULL-BASED)                                |
|                                                                                                   |
|  Repo: gitops-config-repo/                                                                        |
|   ├── base/                  (nginx, mongodb, grafana, airflow, core-api)                         |
|   └── environments/                                                                               |
|       ├── dev/               (dev-config.yaml + kustomization.yaml with pinned SHA)               |
|       ├── uat/               (uat-config.yaml + kustomization.yaml)                               |
|       └── prod/              (prod-config.yaml + kustomization.yaml)                              |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                   IN-CLUSTER GITOPS PULL RECONCILER (CONTINUOUS CD)                               |
|                                                                                                   |
|  Controller: gitops-cd-engine/gitops-pull-reconciler.py                                           |
|                                                                                                   |
|  - Continuous Pull Reconciliation Loop (polls GitOps repo every 10s)                              |
|  - Renders declarative state using 'kubectl kustomize environments/dev'                           |
|  - Declaratively applies state to Kubernetes cluster without developer direct kubectl access     |
|  - Automatic Configuration Drift Correction                                                       |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                       KUBERNETES DEV CLUSTER (5 CORE WORKLOADS)                                   |
|                                                                                                   |
|  1. nginx-gateway-service (Port 80 / NodePort 30080): Reverse Proxy & Status Portal                |
|  2. core-api-service      (Port 8000): FastAPI Enterprise Microservice with Prometheus metrics    |
|  3. mongodb-service       (Port 27017): Stateful Database with automated schema seeding           |
|  4. grafana-service       (Port 3000): Observability & Metrics Visualization                      |
|  5. airflow-service       (Port 8080): Workflow Scheduler & Orchestrator Standalone              |
+--------------------------------------------------+------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+------------------------------------------------+
|                           AIOPS SENTINEL & SELF-HEALING AGENT                                     |
|                                                                                                   |
|  Daemon: aiops-agent/aiops_sentinel.py                                                            |
|                                                                                                   |
|  - Real-time Kubernetes event streaming & pod health audit                                        |
|  - Automated Root Cause Analysis (RCA) on CrashLoopBackOff, Unhealthy, OOMKilled                  |
|  - Automated GitOps Self-Healing Rollback trigger on continuous workload regressions              |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. The 5 Core Enterprise Services

| Service | Category | Ports | Health Endpoints | Role |
| :--- | :--- | :--- | :--- | :--- |
| **`nginx`** | Gateway & Reverse Proxy | `80` (NodePort: `30080`) | `/healthz` | Edge ingress routing `/api/`, `/grafana/`, `/airflow/` |
| **`core-api`** | Microservice | `8000` | `/healthz`, `/readyz`, `/metrics` | Business logic with automated compilation & unit test gates |
| **`mongodb`** | Stateful Database | `27017` | TCP Socket | Stateful database with persistent storage and init scripts |
| **`grafana`** | Telemetry & Observability| `3000` | `/api/health` | Dashboard analytics and cluster monitoring |
| **`airflow`** | Orchestrator | `8080` | `/health` | Batch scheduling and data workflow pipelines |
