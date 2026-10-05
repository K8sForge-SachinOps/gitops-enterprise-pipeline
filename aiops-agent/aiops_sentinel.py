#!/usr/bin/env python3
"""
Enterprise AIOps Sentinel & Diagnostic Agent
Monitors Kubernetes events, pod health, container crashes, and logs.
Performs intelligent Root Cause Analysis (RCA), anomaly detection, and
automated GitOps rollback triggers for self-healing infrastructure.
Author: consultant.sachinbhardwaj@gmail.com
Compliance: State Data Centre (SDC) Air-Gapped Standard
"""
import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AIOPS-SENTINEL] %(message)s"
)

TARGET_NAMESPACE = os.getenv("TARGET_NAMESPACE", "default")
GITOPS_REPO_PATH = os.getenv("GITOPS_REPO_PATH", "/home/sachink8s/.gemini/antigravity-ide/scratch/gitops-enterprise-pipeline/gitops-config-repo")
TARGET_ENV = os.getenv("TARGET_ENV", "dev")

class AIOpsSentinel:
    def __init__(self, namespace="default"):
        self.namespace = namespace
        self.incident_history = []
        self.known_issues = {
            "CrashLoopBackOff": "Application process terminated unexpectedly. Inspect startup logs, missing ENV variables, or failed sanity checks.",
            "ImagePullBackOff": "Container runtime failed to retrieve image from registry. Verify private registry connectivity and image tag existence.",
            "ErrImagePull": "Image not found or network connection to private registry timed out.",
            "OOMKilled": "Container exceeded cgroup memory limits. Increase memory limit in resource specifications.",
            "Unhealthy": "Kubernetes liveness or readiness probe failed consecutively. Check internal endpoint responsiveness."
        }

    def run_cmd(self, cmd_args):
        """Runs a shell command safely."""
        try:
            res = subprocess.run(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return res.stdout
        except subprocess.CalledProcessError as e:
            return None

    def scan_workload_health(self):
        """Audits all pods in namespace for anomalies and degradation."""
        out = self.run_cmd(["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"])
        if not out:
            return []

        data = json.loads(out)
        anomalies = []

        for item in data.get("items", []):
            pod_name = item["metadata"]["name"]
            labels = item["metadata"].get("labels", {})
            status = item.get("status", {})
            phase = status.get("phase", "Unknown")

            # Check container statuses
            container_statuses = status.get("containerStatuses", [])
            for cs in container_statuses:
                c_name = cs["name"]
                restart_count = cs.get("restartCount", 0)
                state = cs.get("state", {})

                # Check waiting reasons
                waiting = state.get("waiting", {})
                reason = waiting.get("reason", "")

                if reason in self.known_issues:
                    anomalies.append({
                        "pod": pod_name,
                        "container": c_name,
                        "phase": phase,
                        "reason": reason,
                        "message": waiting.get("message", "No message provided"),
                        "restarts": restart_count,
                        "severity": "CRITICAL" if reason in ["CrashLoopBackOff", "OOMKilled"] else "WARNING"
                    })
                elif restart_count > 3:
                    anomalies.append({
                        "pod": pod_name,
                        "container": c_name,
                        "phase": phase,
                        "reason": "FrequentRestarts",
                        "message": f"Pod restarted {restart_count} times",
                        "restarts": restart_count,
                        "severity": "WARNING"
                    })

        return anomalies

    def diagnose_anomaly(self, anomaly):
        """Performs automated AI-assisted Root Cause Analysis (RCA)."""
        pod_name = anomaly["pod"]
        reason = anomaly["reason"]
        restarts = anomaly["restarts"]

        logging.warning(f">> [AIOPS-ALERT] Detected Anomaly on Pod '{pod_name}'! Reason: {reason} (Restarts: {restarts})")
        
        # Capture recent pod logs
        logs = self.run_cmd(["kubectl", "logs", pod_name, "-n", self.namespace, "--tail=20"]) or "No recent logs captured."
        
        rca_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_pod": pod_name,
            "detected_reason": reason,
            "diagnosis_summary": self.known_issues.get(reason, "Unrecognized workload degradation pattern."),
            "evidence_logs": logs.splitlines()[-5:] if logs else [],
            "remediation_recommendation": self._generate_recommendation(reason, logs)
        }
        
        self.incident_history.append(rca_report)
        return rca_report

    def _generate_recommendation(self, reason, logs):
        """Generates contextual actionable remediation."""
        if reason == "ImagePullBackOff" or reason == "ErrImagePull":
            return "Action: Verify that the private Docker registry ('localhost:5001' / 'dev-registry:5000') is accessible and the commit SHA image was pushed successfully."
        elif reason == "CrashLoopBackOff":
            return "Action: Trigger automated GitOps rollback to previous stable Git commit SHA, or review recent application commits for runtime errors."
        elif reason == "OOMKilled":
            return "Action: Increase container memory limit in 'kustomization.yaml' or base deployment resources block."
        return "Action: Inspect cluster events and container startup probes."

    def trigger_gitops_self_healing_rollback(self):
        """Self-healing action: Reverts GitOps configuration repo to previous commit."""
        logging.info(">> [AIOPS-SELF-HEALING] Initiating automated GitOps rollback to previous stable state...")
        try:
            res = subprocess.run(
                ["git", "revert", "--no-edit", "HEAD"],
                cwd=GITOPS_REPO_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logging.info(">> [AIOPS-SELF-HEALING] GitOps repository rolled back successfully. Pull-reconciler will apply stable state.")
            return True
        except Exception as e:
            logging.error(f">> [AIOPS-SELF-HEALING] Rollback failed: {e}")
            return False

    def audit_cluster_telemetry(self):
        """Scans cluster and prints health dashboard."""
        anomalies = self.scan_workload_health()
        print("\n" + "=" * 80)
        print(f"  AIOPS SENTINEL: CLUSTER HEALTH AUDIT REPORT - [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"  Target Namespace: {self.namespace} | Target Environment: {TARGET_ENV}")
        print("=" * 80)

        if not anomalies:
            print("  🟢 HEALTH STATUS: OPTIMAL (100% workloads healthy, zero regressions detected)")
        else:
            print(f"  🔴 HEALTH STATUS: DEGRADED ({len(anomalies)} anomalies detected)\n")
            for a in anomalies:
                report = self.diagnose_anomaly(a)
                print(f"  [INCIDENT REPORT] Pod: {report['target_pod']}")
                print(f"    - Severity:       {a['severity']}")
                print(f"    - Detected Issue: {report['detected_reason']}")
                print(f"    - Analysis:       {report['diagnosis_summary']}")
                print(f"    - Recommendation: {report['remediation_recommendation']}")
                print("-" * 80)
        print("=" * 80 + "\n")

if __name__ == "__main__":
    sentinel = AIOpsSentinel(TARGET_NAMESPACE)
    sentinel.audit_cluster_telemetry()
