# Enterprise AIOps & Autonomous AI Agent Integration Guide

---

## 1. Role of AIOps in Modern Cloud-Native Delivery

In modern tier-1 engineering organizations, GitOps manages **declarative intent** (what should be running), while **AIOps** manages **runtime telemetry and autonomous remediation** (how it is actually behaving).

The AIOps Agent (`aiops_sentinel.py`) implemented in this project acts as an autonomous cluster reliability engineer:
1. **Event Streaming:** Continuously intercepts Kubernetes events (`Warning`, `Unhealthy`, `CrashLoopBackOff`, `OOMKilled`).
2. **Root Cause Analysis (RCA):** Extracts log buffers, configuration diffs, and container exit codes to determine exact failure vectors.
3. **Automated Rollback & Self-Healing:** When repeated fatal regressions occur following a new GitOps promotion, the agent automatically executes a Git-level rollback, triggering the pull reconciler to restore the cluster to the last verified stable state.

---

## 2. AIOps Sentinel Architecture

```
                  +--------------------------------+
                  |  Kubernetes API Server (dev)   |
                  +---------------+----------------+
                                  |
                                  | Event & Telemetry Stream
                                  v
                  +--------------------------------+
                  |     AIOPS SENTINEL DAEMON      |
                  |  (aiops-agent/aiops_sentinel)  |
                  +---------------+----------------+
                                  |
            +---------------------+---------------------+
            |                                           |
            v                                           v
[Diagnostic Classification]                 [Self-Healing Reconciler]
  - CrashLoopBackOff: Code/ENV error          - If consecutive crashes:
  - ImagePullBackOff: Registry sync failure     git revert HEAD
  - Probe Unhealthy: Timing/Init bottleneck   - GitOps CD Reconciler auto-syncs
```

---

## 3. Extending with AI Agents (LLM & Antigravity Agent Kit)

The architecture is built with clean JSON I/O hooks so that an LLM agent (e.g., using Gemini API or Antigravity SDK) can interact with it via natural language:

### Sample AI Agent Slash Commands / Capabilities:
* `/cluster-health`: Queries `aiops_sentinel.py` and returns a human-readable telemetry summary.
* `/diagnose <pod>`: Performs deep log extraction and semantic analysis on recent crashes.
* `/suggest-tuning`: Analyzes CPU/Memory requests vs. live cgroup metrics and outputs optimized resource patches for `kustomization.yaml`.
* `/emergency-rollback`: Instructs the agent to safely revert the GitOps repository to a known good release tag.

### Running AIOps Sentinel
To run a one-time audit:
```bash
python3 aiops-agent/aiops_sentinel.py
```

To run as a continuous background daemon:
```bash
python3 aiops-agent/aiops_sentinel.py --daemon --interval 30
```
