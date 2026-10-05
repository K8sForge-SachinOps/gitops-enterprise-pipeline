# Global Standard Git Branching & Promotion Strategy for GitOps

---

## 1. Industry Standard Model: Trunk-Based Development with Environment Overlays

Global product companies (Google, Netflix, Meta, Red Hat) have largely moved away from complex multi-branch models (like traditional GitFlow) toward **Trunk-Based Development with Declarative Environment Overlays**.

```
APPLICATION REPOSITORY (app-source-repo):
-------------------------------------------------------------
feat/user-auth  ---> PR/Review ---> [ main ] (Trunk)
                                       |
                                       v (Automated CI Trigger)
                                    Build & Run Unit Tests
                                    Tag with Git Short SHA (e.g. 7a3c8e1)
                                    Push to Private Registry
                                       |
                                       +-----------------------+
                                                               |
GITOPS CONFIGURATION REPOSITORY (gitops-config-repo):          |
-------------------------------------------------------------  |
[ main ] branch                                                v
   ├── base/ (Shared kubernetes manifests)           Auto-Updates:
   └── environments/                                 newTag: 7a3c8e1
       ├── dev/  (Auto-deployed via GitOps Pull) <-----+
       ├── uat/  (Promoted via Pull Request)
       └── prod/ (Promoted via Release Tag / PR)
```

---

## 2. Environment Promotion Workflow (Dev -> UAT -> Prod)

### Phase 1: Dev Deployment (100% Automated)
1. Developer pushes to `main` (or a feature branch).
2. The CI pipeline compiles code, executes runtime unit tests, packages the Docker image, tags it with the short SHA (`git rev-parse --short HEAD`), and pushes to the private registry.
3. The CI engine updates `environments/dev/kustomization.yaml` and `dev-config.yaml` with the new commit SHA.
4. The in-cluster **GitOps Pull Reconciler** detects the commit and immediately rolls out the update to the `dev` cluster.

### Phase 2: Promotion to UAT (User Acceptance Testing)
When the software is validated in `dev`, promotion to `uat` occurs declaratively through Git:
```bash
# Automated promotion script or PR
cd gitops-config-repo

# Promote core-api to UAT
sed -i 's/newTag: .*/newTag: 7a3c8e1/' environments/uat/kustomization.yaml

git add environments/uat/
git commit -m "chore(promote): promote core-api 7a3c8e1 to UAT"
git push origin main
```
The GitOps agent configured for UAT applies `environments/uat` which automatically picks up `uat-config.yaml` (e.g., 2 replicas, log level INFO, UAT endpoints).

### Phase 3: Promotion to Production (State Data Centre)
For production deployment, governance rules at the State Data Centre require immutability, cryptographic signing, and explicit approval:
1. Create a Git Release Tag (e.g., `v1.2.0`) in `gitops-config-repo`.
2. Update `environments/prod/kustomization.yaml` with the release version and apply `prod-config.yaml` (3 replicas, hardened resource constraints).
3. Merge via a signed Pull Request.

---

## 3. Alternative: Environment Branches Model

If the State Data Centre requires branch-per-environment isolation instead of directory overlays, the repository supports branch-based tracking:

```
[ main ] ----------> Base development & Dev cluster
    |
    v (Merge / Fast-forward)
[ uat ] -----------> Deployed to Staging / UAT cluster
    |
    v (Signed Release Merge)
[ prod ] ----------> Deployed to Air-Gapped SDC Production Cluster
```

To switch the in-cluster GitOps Reconciler to track a different branch:
```bash
export GITOPS_TARGET_BRANCH="uat" # or "prod"
git checkout ${GITOPS_TARGET_BRANCH}
python3 gitops-cd-engine/gitops-pull-reconciler.py
```

---

## 4. Performance & Security Optimizations

1. **Docker Layer Caching:** Multi-stage builds cache OS packages and pip wheels so that compilation and testing execute in < 3 seconds on cached runs.
2. **Fail-Fast Unit Test Gates:** Tests run before any container packaging or registry push. Zero defective images can enter the artifact registry.
3. **Immutable Artifact Pinning:** Workloads are never deployed with `:latest` in production; they are strictly pinned to immutable Git commit SHAs.
4. **Rootless Security Compliance:** All microservices run as non-root users (`UID 10001`) with read-only root filesystems where applicable.
