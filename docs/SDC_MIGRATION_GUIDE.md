# State Data Centre (SDC) On-Premise Installation & Migration Guide

---

## 1. Overview & SDC Constraints

State Data Centres (SDC) operate with strict security mandates:
* **Air-gapped / Isolated Network:** Servers frequently do not have direct access to the public internet.
* **On-Premise Private Registry:** All container images must reside on internal registries (Harbor, Docker Registry v2, or Nexus).
* **Strict Role-Based Access Control (RBAC):** Developers do not have direct `kubectl` cluster admin access. Deployments are executed exclusively through GitOps pull controllers.

This implementation was engineered so that every component running locally on your Ubuntu workstation can be packaged, transferred, and executed on the SDC server with 100% parity.

---

## 2. Pre-Requisites on the SDC Server

1. **Operating System:** Ubuntu Server 22.04 LTS / 24.04 LTS.
2. **Container Engine:** Docker Engine 24.x+ or Containerd.
3. **Kubernetes Cluster:** Upstream Kubernetes, Kind, K3s, MicroK8s, or RKE2.
4. **Tools:** `git`, `kubectl`, `python3`.

---

## 3. Step-by-Step Migration Process

### Step 1: Package Local Images for Air-Gapped Transfer
On your local machine, export the base images and verified service images into a tar archive:
```bash
docker save \
    registry:2 \
    dev-registry:5000/core-api:latest \
    dev-registry:5000/nginx-gateway:latest \
    mongo:7.0 \
    grafana/grafana:11.2.0 \
    apache/airflow:2.10.2-python3.12 \
    -o sdc-enterprise-images.tar
```

Transfer `sdc-enterprise-images.tar` and the project directory `gitops-enterprise-pipeline/` to the SDC server via authorized media / secure SCP.

### Step 2: Load Images & Initialize SDC Private Registry
On the SDC server:
```bash
# Load images into host docker
docker load -i sdc-enterprise-images.tar

# Run the private container registry
docker run -d -p 5000:5000 --restart=always --name sdc-registry registry:2

# Retag and push images to the SDC internal registry
docker tag dev-registry:5000/core-api:latest localhost:5000/core-api:latest
docker push localhost:5000/core-api:latest

docker tag dev-registry:5000/nginx-gateway:latest localhost:5000/nginx-gateway:latest
docker push localhost:5000/nginx-gateway:latest
```

### Step 3: Configure SDC Kubernetes Cluster for Insecure / Private Registry
Configure Containerd on the SDC cluster nodes:
```toml
# /etc/containerd/certs.d/sdc-registry:5000/hosts.toml
server = "http://sdc-registry:5000"

[host."http://sdc-registry:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
```

### Step 4: Deploy the Git Repositories
Set up the central bare repositories on the SDC Git server:
```bash
cd /opt/gitops-enterprise-pipeline/git-server
git init --bare app.git
git init --bare gitops.git

# Copy hooks
cp app-source-repo/ci/build-and-deploy.sh app.git/hooks/post-receive
chmod +x app.git/hooks/post-receive
```

### Step 5: Run the GitOps Pull CD Controller as a Systemd Service
Create a persistent daemon on the SDC server so GitOps reconciliation runs 24/7 in the background:
```ini
# /etc/systemd/system/gitops-reconciler.service
[Unit]
Description=Enterprise GitOps Pull CD Controller
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gitops-enterprise-pipeline
Environment=TARGET_ENV=prod
Environment=SYNC_INTERVAL_SECONDS=15
ExecStart=/usr/bin/python3 /opt/gitops-enterprise-pipeline/gitops-cd-engine/gitops-pull-reconciler.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gitops-reconciler.service
```

### Step 6: Verify Deployment Status
```bash
kubectl get pods -A
python3 /opt/gitops-enterprise-pipeline/aiops-agent/aiops_sentinel.py
```
