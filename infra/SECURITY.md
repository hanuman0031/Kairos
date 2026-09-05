# Kairos Platform — Security Architecture

This document describes the security model for the Kairos EdTech micro-feedback platform running on Google Kubernetes Engine (GKE).

---

## 1. Workload Identity Federation

Workload Identity is the **recommended** way for GKE workloads to access Google Cloud APIs. It eliminates the need to create, download, or rotate service-account key files.

### How It Works

```
┌─────────────────────────┐       IAM Policy Binding       ┌──────────────────────────────┐
│  K8s ServiceAccount     │ ◄──────────────────────────────►│  GCP Service Account         │
│  kairos-backend-sa      │   workloadIdentityUser role     │  kairos-vertex-ai@<PROJECT>  │
│  (namespace: kairos)    │                                 │  roles/aiplatform.user       │
└─────────────────────────┘                                 └──────────────────────────────┘
         │                                                            │
         │  Pod runs as this K8s SA                                   │  Token exchange via
         │  with annotation:                                          │  GKE metadata server
         │  iam.gke.io/gcp-service-account                           │
         ▼                                                            ▼
   ┌───────────┐                                              ┌──────────────┐
   │  Pod      │  ─── requests token ──────────────────────►  │  Vertex AI   │
   │  (backend)│  ◄── receives federated OIDC token ────────  │  Gemini API  │
   └───────────┘                                              └──────────────┘
```

### Setup Steps

> **Replace `<PROJECT_ID>` with your actual GCP project ID in all commands.**

#### Step 1 — Create the GCP Service Account

```bash
gcloud iam service-accounts create kairos-vertex-ai \
  --display-name="Kairos Vertex AI Service Account" \
  --project=<PROJECT_ID>
```

#### Step 2 — Grant Vertex AI Access

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:kairos-vertex-ai@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

#### Step 3 — Bind the K8s SA to the GCP SA

```bash
gcloud iam service-accounts add-iam-policy-binding \
  kairos-vertex-ai@<PROJECT_ID>.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:<PROJECT_ID>.svc.id.goog[kairos/kairos-backend-sa]"
```

#### Step 4 — Apply the Kubernetes ServiceAccount

The `k8s/backend-serviceaccount.yaml` manifest contains the required annotation:

```yaml
annotations:
  iam.gke.io/gcp-service-account: "kairos-vertex-ai@<PROJECT_ID>.iam.gserviceaccount.com"
```

Once all four steps are complete, any pod using `serviceAccountName: kairos-backend-sa` will automatically receive short-lived federated credentials for Vertex AI. **No key files are ever created or stored.**

#### Verification

```bash
# Exec into a backend pod and verify the identity
kubectl exec -it -n kairos deploy/kairos-backend -- \
  python -c "import google.auth; creds, project = google.auth.default(); print(f'Project: {project}')"
```

---

## 2. Pod Security

All Kairos containers are hardened with the following security controls:

| Control | Setting | Rationale |
|---|---|---|
| **Non-root user** | `runAsNonRoot: true` | Prevents container escape via root privileges |
| **Read-only root FS** | `readOnlyRootFilesystem: true` | Blocks malware writing to the filesystem |
| **No privilege escalation** | `allowPrivilegeEscalation: false` | Prevents `setuid`/`setgid` bit exploitation |
| **Drop all capabilities** | `capabilities.drop: [ALL]` | Removes all Linux capabilities (no raw sockets, no `chown`, etc.) |
| **tmpfs for /tmp** | `emptyDir.medium: Memory` | Provides a writable scratch space without compromising the read-only FS |

### Dockerfile-Level Hardening

- **Backend**: Runs as the `kairos` user (created via `useradd -r`). No shell access (`/sbin/nologin`).
- **Frontend**: Runs as UID 1001 (`kairos` user). Alpine-based minimal image.
- Both images use **multi-stage builds** to exclude build tools, source repos, and package caches from the final image.

---

## 3. RBAC

### Principle of Least Privilege

- The `kairos-backend-sa` ServiceAccount has **no additional Kubernetes RBAC bindings** — it cannot list pods, read secrets, or modify any cluster resources.
- Its only elevated access is the Workload Identity binding to the GCP SA for Vertex AI.
- The frontend pods use the `default` ServiceAccount with no special permissions.

### Recommended RBAC Policies

For production, consider adding:

```yaml
# Deny automounting the default SA token for pods that don't need K8s API access.
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kairos-backend-sa
  namespace: kairos
automountServiceAccountToken: false  # Add this if K8s API access is not needed
```

---

## 4. Network Policies (Recommended)

Network policies restrict pod-to-pod and pod-to-external traffic. They require a CNI plugin that supports NetworkPolicy (e.g., Calico, GKE Dataplane V2).

### Backend — Ingress Policy

Only accept traffic from the frontend pods and the ingress controller:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kairos-backend-ingress
  namespace: kairos
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: kairos-backend
  policyTypes:
    - Ingress
  ingress:
    # Allow from frontend pods
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: kairos-frontend
      ports:
        - protocol: TCP
          port: 8000
    # Allow from ingress controller (typically in a different namespace)
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx  # or gke-managed-certs namespace
      ports:
        - protocol: TCP
          port: 8000
```

### Backend — Egress Policy

Restrict outbound traffic to DNS and Vertex AI endpoints only:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kairos-backend-egress
  namespace: kairos
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: kairos-backend
  policyTypes:
    - Egress
  egress:
    # DNS resolution
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # Vertex AI / Google APIs (HTTPS)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0  # Narrow this to Google API IP ranges in production
      ports:
        - protocol: TCP
          port: 443
```

> **Note:** For tighter egress control, use [Google's published IP ranges](https://cloud.google.com/vpc/docs/configure-private-google-access) or Private Google Access.

---

## 5. Secrets Management

| Aspect | Approach |
|---|---|
| **Application config** | Non-secret values in `ConfigMap` (`backend-configmap.yaml`) |
| **GCP authentication** | Workload Identity — no keys stored anywhere |
| **Additional secrets** | Use [Google Secret Manager](https://cloud.google.com/secret-manager) with the CSI driver or SDK |
| **K8s Secrets** | If needed, enable [envelope encryption](https://cloud.google.com/kubernetes-engine/docs/how-to/encrypting-secrets) with Cloud KMS |

### Rules

1. **Never** store secrets in ConfigMaps, environment variables in YAML, or container images.
2. **Never** create or download GCP service-account key files.
3. **Always** use Workload Identity for GCP API authentication.
4. **Always** use Secret Manager or encrypted K8s Secrets for any additional credentials.

---

## 6. Image Security

| Practice | Implementation |
|---|---|
| **Minimal base images** | `python:3.12-slim` (backend), `node:22-alpine` (frontend) |
| **Multi-stage builds** | Build tools never reach the runtime image |
| **No package caches** | `--no-cache-dir` (pip), `npm ci` |
| **Vulnerability scanning** | Integrate [Artifact Registry vulnerability scanning](https://cloud.google.com/artifact-registry/docs/analysis) |
| **Image signing** | Consider [Binary Authorization](https://cloud.google.com/binary-authorization) for production |

---

## 7. TLS / Transport Security

- **External traffic**: Terminated at the GCE Ingress with a Google-managed certificate.
- **Internal traffic**: Pods communicate over the cluster network. For zero-trust, enable [Anthos Service Mesh / Istio mTLS](https://cloud.google.com/service-mesh/docs/overview).
- **HTTP → HTTPS redirect**: Enforced via the Ingress annotation `kubernetes.io/ingress.allow-http: "false"`.

---

## 8. Checklist Before Production

- [ ] Replace all `<PROJECT_ID>` placeholders in manifests
- [ ] Replace `<DOMAIN>` and `<CERTIFICATE_NAME>` in `ingress.yaml`
- [ ] Complete Workload Identity setup (Steps 1–4 above)
- [ ] Enable GKE Dataplane V2 for NetworkPolicy support
- [ ] Apply the recommended NetworkPolicy manifests
- [ ] Enable Artifact Registry vulnerability scanning
- [ ] Enable Cloud Audit Logs for the `kairos` namespace
- [ ] Consider Binary Authorization for image provenance
- [ ] Set `automountServiceAccountToken: false` if K8s API access is not needed
- [ ] Review and tune HPA thresholds after load testing
