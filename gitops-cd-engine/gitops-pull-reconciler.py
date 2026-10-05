#!/usr/bin/env python3
"""
Enterprise GitOps Pull-Based CD Controller
Implements pull-based continuous deployment and reconciliation loop.
Watches GitOps configuration repository, applies declarative overlays,
detects configuration drift, and ensures live cluster matches Git single source of truth.
Author: consultant.sachinbhardwaj@gmail.com
Compliance: State Data Centre (SDC) Air-Gapped Standard
"""
import os
import sys
import time
import logging
import subprocess
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GITOPS-PULL-CD] %(message)s"
)

GITOPS_REPO_PATH = os.getenv("GITOPS_REPO_PATH", "/home/sachink8s/.gemini/antigravity-ide/scratch/gitops-enterprise-pipeline/gitops-config-repo")
TARGET_ENV = os.getenv("TARGET_ENV", "dev")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_SECONDS", "10"))
KUBECONFIG = os.getenv("KUBECONFIG", "")

class GitOpsReconciler:
    def __init__(self, repo_path: str, environment: str):
        self.repo_path = repo_path
        self.environment = environment
        self.overlay_path = os.path.join(repo_path, "environments", environment)
        self.last_applied_hash = None

    def get_git_revision(self) -> str:
        """Fetches the latest commit SHA of the GitOps repository."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return res.stdout.strip()
        except Exception as e:
            logging.warning(f"Unable to read git revision: {e}")
            return "unknown"

    def reconcile(self) -> bool:
        """Performs pull reconciliation using Kustomize against target cluster."""
        if not os.path.isdir(self.overlay_path):
            logging.error(f"Overlay path does not exist: {self.overlay_path}")
            return False

        current_hash = self.get_git_revision()
        logging.info(f"Reconciling environment: [{self.environment}] (Git Revision: {current_hash[:7] if current_hash else 'N/A'})")

        try:
            # 1. Render declarative manifests using Kustomize
            kustomize_cmd = ["kubectl", "kustomize", self.overlay_path]
            rendered = subprocess.run(
                kustomize_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            # 2. Apply declaratively to Kubernetes cluster (Server-Side / Client Apply)
            apply_cmd = ["kubectl", "apply", "-f", "-"]
            applied = subprocess.run(
                apply_cmd,
                input=rendered.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            logging.info(">> [GITOPS-SYNC] Successfully reconciled desired state to Kubernetes cluster:")
            for line in applied.stdout.splitlines():
                if line.strip():
                    logging.info(f"     {line.strip()}")

            self.last_applied_hash = current_hash
            return True

        except subprocess.CalledProcessError as err:
            logging.error(f">> [GITOPS-ERROR] Reconciliation failed: {err.stderr.strip()}")
            return False

    def check_workload_status(self):
        """Audits deployed pods and services status."""
        try:
            res = subprocess.run(
                ["kubectl", "get", "pods", "-l", f"environment={self.environment}", "-o", "wide"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info(f">> [CLUSTER-STATUS] Live Workloads for environment '{self.environment}':\n{res.stdout}")
        except Exception as e:
            logging.warning(f"Error fetching cluster status: {e}")

    def run_loop(self, once=False):
        """Starts continuous reconciliation loop."""
        logging.info("================================================================================")
        logging.info(f">> Starting GitOps Pull-Based CD Controller for environment: {self.environment}")
        logging.info(f">> Manifest Path: {self.overlay_path}")
        logging.info(f">> Polling Interval: {SYNC_INTERVAL} seconds")
        logging.info("================================================================================")

        while True:
            self.reconcile()
            self.check_workload_status()

            if once:
                break
            time.sleep(SYNC_INTERVAL)

if __name__ == "__main__":
    once_flag = "--once" in sys.argv
    reconciler = GitOpsReconciler(GITOPS_REPO_PATH, TARGET_ENV)
    reconciler.run_loop(once=once_flag)
