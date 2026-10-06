# Enterprise GitOps CI/CD Implementation & Integration Blueprint
**Author & Maintainer:** `consultant.sachinbhardwaj@gmail.com`  
**Target Environment:** Local Ubuntu Dev Cluster & State Data Centre (SDC) Air-Gapped Production

---

## 1. Executive Summary & Architecture Topology

This architecture delivers a production-grade, pull-based GitOps CI/CD workflow designed for strict isolation, high security, and zero vendor lock-in.

```
+-----------------------------------------------------------------------------------------+
|                                  DEVELOPER WORKSTATION                                  |
|   Committer: consultant.sachinbhardwaj@gmail.com                                        |
|   1. git commit -m "..." && git push origin main                                         |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-------------------------------------------+---------------------------------------------+
|                                   CENTRAL GIT SERVER                                    |
|   Bare Repositories:                                                                    |
|     - git-server/app.git      (Source Code: core-api, nginx, airflow, grafana, mongodb) |
|     - git-server/gitops.git   (Declarative K8s Overlays: base, dev, uat, prod)          |
|   Triggers: post-receive server hook & Webhook Listener (Port 9000)                     |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-------------------------------------------+---------------------------------------------+
|                     AUTOMATED CI PIPELINE (PUSH-DRIVEN)                                 |
|   Gates:                                                                                |
|     [1] Code Compilation / Syntax Verification                                          |
|     [2] Runtime Unit Test Gate (pytest inside multi-stage Dockerfile)                   |
|     [3] Immutable Short Git-SHA Image Tagging (dev-registry:5000/<service>:<sha>)       |
|     [4] Push to Private Container Registry (localhost:5001 / dev-registry:5000)         |
|     [5] Update GitOps Manifests (kustomization.yaml & dev-config.yaml)                  |
|     [6] Commit Release SHA to gitops-config-repo                                        |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-------------------------------------------+---------------------------------------------+
|               GITOPS DECLARATIVE MANIFEST REPO (SINGLE SOURCE OF TRUTH)                 |
|   Directory Hierarchy:                                                                  |
|     ├── base/                 (Declarative manifests for all 5 services)                |
|     └── environments/                                                                   |
|         ├── dev/              (dev-config.yaml + pinned SHA kustomization)              |
|         ├── uat/              (uat-config.yaml + QA approval overlay)                   |
|         └── prod/             (prod-config.yaml + SDC air-gapped production overlay)    |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-------------------------------------------+---------------------------------------------+
|                      CD ENGINE (PULL-BASED RECONCILIATION)                              |
|   Option A: Native In-Cluster GitOps Reconciler (gitops-pull-reconciler.py)             |
|   Option B: ArgoCD Controller & Application Operator (argocd-repo-server)               |
|   Option C: Jenkins Continuous Delivery Pipeline (multi-branch Jenkinsfile)             |
+-------------------------------------------+---------------------------------------------+
                                            |
                                            v
+-------------------------------------------+---------------------------------------------+
|                    KUBERNETES DEV CLUSTER (5 LIVE WORKLOADS)                            |
|   1. nginx-gateway-service: Port 80 / NodePort 30080 (Reverse proxy & unified portal)   |
|   2. core-api-service:      Port 8000 (FastAPI backend + /docs + /metrics)              |
|   3. mongodb-service:       Port 27017 (Stateful database with automated schema init)   |
|   4. grafana-service:       Port 3000 (Observability & dashboard telemetry)             |
|   5. airflow-service:       Port 8080 (Batch workflow scheduler & orchestrator)         |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Live UI Testing & Verification Matrix

All 5 services are live and accessible via browser and REST clients.

| Service | UI URL (Localhost) | NodePort Direct URL | Authentication | Verification Metric |
| :--- | :--- | :--- | :--- | :--- |
| **Enterprise Portal** | `http://localhost:8080/` | `http://172.18.0.2:30080/` | Public | Status Dashboard with real-time links |
| **Swagger API Docs** | `http://localhost:8080/api/docs` | `http://172.18.0.2:30080/api/docs` | Public | Interactive OpenAPI UI |
| **Core API Service** | `http://localhost:8080/api/` | `http://172.18.0.2:30080/api/` | Public | Returns `{"status":"online","service":"Enterprise Core API"}` |
| **Database Readiness** | `http://localhost:8080/api/readyz` | `http://172.18.0.2:30080/api/readyz` | Public | Verifies live TCP connection to MongoDB replica |
| **Prometheus Metrics**| `http://localhost:8080/api/metrics` | `http://172.18.0.2:30080/api/metrics` | Public | OpenMetrics process telemetry |
| **Grafana Telemetry** | `http://localhost:3000/` or `/grafana/`| `http://172.18.0.2:30080/grafana/` | `admin` / `enterpriseAdmin123` | Active dashboards & cluster metrics |
| **Apache Airflow** | `http://localhost:8080/airflow/` | `http://172.18.0.2:30080/airflow/` | `admin` / `enterpriseAirflow123` | DAG orchestration UI |

---

## 3. ArgoCD Integration Blueprint (Drop-In GitOps Upgrade)

Because the project layout strictly follows the **Kustomize Base + Environment Overlay** standard, ArgoCD can manage this cluster natively with zero manifest changes.

### Step 3.1: Install ArgoCD in Kubernetes dev Cluster
```bash
# 1. Create dedicated namespace
kubectl create namespace argocd

# 2. Apply upstream ArgoCD manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. Wait for all ArgoCD pods to reach Running status
kubectl wait --for=condition=available deployment/argocd-server -n argocd --timeout=300s

# 4. Expose ArgoCD Web UI
kubectl port-forward svc/argocd-server -n argocd 8081:443 &
```

### Step 3.2: Declarative ArgoCD Application CRD (`argocd-application.yaml`)
Create this manifest to register the dev environment in ArgoCD:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: enterprise-platform-dev
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    # URL of gitops configuration repository (local file path or remote Git)
    repoURL: 'https://github.com/consultant-sachinbhardwaj/gitops-config-repo.git'
    targetRevision: main
    path: environments/dev
  destination:
    server: 'https://kubernetes.default.svc'
    namespace: default
  syncPolicy:
    automated:
      prune: true      # Automatically remove resources deleted from Git
      selfHeal: true   # Automatically revert manual kubectl changes (Drift Correction)
    syncOptions:
      - CreateNamespace=true
      - ApplyOutOfSyncOnly=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Step 3.3: ArgoCD UI Verification
1. Open `http://localhost:8081` in your browser.
2. Fetch the initial admin password:
   ```bash
   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo ""
   ```
3. Login using username `admin`.
4. ArgoCD will display the tree of all 5 services with live health checks (`Healthy`, `Synced`).

---

## 4. Jenkins Multi-Repo CI/CD Pipeline (Parallel Integration)

In global product organizations, CI and CD are split into two decoupled repositories:
1. **Application Repository (`app-source-repo`):** Code, Dockerfile, unit tests.
2. **GitOps Manifest Repository (`gitops-config-repo`):** Kubernetes YAMLs, Kustomize overlays.

### Complete Production `Jenkinsfile`
Place this `Jenkinsfile` in the root of `app-source-repo`:

```groovy
pipeline {
    agent any

    environment {
        SERVICE_NAME        = 'core-api'
        REGISTRY_HOST       = 'localhost:5001'
        K8S_REGISTRY        = 'dev-registry:5000'
        GITOPS_REPO_URL     = 'https://github.com/consultant-sachinbhardwaj/gitops-config-repo.git'
        GIT_COMMIT_AUTHOR   = 'consultant.sachinbhardwaj@gmail.com'
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                checkout scm
                script {
                    env.SHORT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    echo ">> Building commit: ${env.SHORT_SHA}"
                }
            }
        }

        stage('Gate 1: Lint & Syntax Check') {
            steps {
                sh '''
                    echo ">> Validating Python compilation syntax..."
                    python3 -m py_compile services/core-api/app/*.py
                '''
            }
        }

        stage('Gate 2: Containerized Unit Tests') {
            steps {
                sh '''
                    echo ">> Executing unit tests inside test-runner stage..."
                    docker build --target test-runner -t core-api:test services/core-api
                '''
            }
        }

        stage('Gate 3: Build & Tag Image') {
            steps {
                sh '''
                    echo ">> Packaging production image with Short SHA..."
                    docker build -t ${REGISTRY_HOST}/core-api:${SHORT_SHA} -t ${REGISTRY_HOST}/core-api:latest services/core-api
                '''
            }
        }

        stage('Gate 4: Push to Private Registry') {
            steps {
                sh '''
                    echo ">> Pushing images to private Docker registry..."
                    docker push ${REGISTRY_HOST}/core-api:${SHORT_SHA}
                    docker push ${REGISTRY_HOST}/core-api:latest
                '''
            }
        }

        stage('Gate 5: Update GitOps Repository') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'git-credentials', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                    sh '''
                        echo ">> Cloning GitOps Manifest Repository..."
                        rm -rf gitops-config-repo
                        git clone https://${GIT_USER}:${GIT_PASS}@${GITOPS_REPO_URL#https://} gitops-config-repo
                        
                        cd gitops-config-repo/environments/dev
                        
                        echo ">> Pinning image tag to ${SHORT_SHA} in kustomization.yaml..."
                        sed -i "s|newTag: .*|newTag: ${SHORT_SHA}|g" kustomization.yaml
                        sed -i "s|^LAST_SYNC=.*|LAST_SYNC=${SHORT_SHA}-$(date +%Y%m%d%H%M%S)|g" dev-config.yaml
                        
                        git config user.name "Jenkins CI Bot"
                        git config user.email "${GIT_COMMIT_AUTHOR}"
                        git add kustomization.yaml dev-config.yaml
                        git commit -m "chore(gitops): Jenkins auto-promote core-api to ${SHORT_SHA} [skip ci]"
                        git push origin main
                    '''
                }
            }
        }

        stage('Trigger CD Sync') {
            steps {
                echo ">> GitOps repository updated. ArgoCD / Reconciler will pull and reconcile automatically in < 15 seconds."
            }
        }
    }

    post {
        success {
            echo ">> CI/CD Pipeline executed successfully for ${SERVICE_NAME} (SHA: ${env.SHORT_SHA})"
        }
        failure {
            echo ">> Build FAILED. Security and stability gates prevented deployment."
        }
    }
}
```

---

## 5. AIOps Sentinel & Self-Healing Daemon

The sentinel script (`aiops-agent/aiops_sentinel.py`) runs as an autonomous agent:
* Detects `CrashLoopBackOff`, `OOMKilled`, or `Unhealthy` events.
* Performs automated Root Cause Analysis (RCA).
* Automatically executes a Git rollback if consecutive failures occur, causing the GitOps reconciler to restore the last stable deployment.

Run a live health check:
```bash
python3 /home/sachink8s/.gemini/antigravity-ide/scratch/gitops-enterprise-pipeline/aiops-agent/aiops_sentinel.py
```
