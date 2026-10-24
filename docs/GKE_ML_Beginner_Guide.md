# End-to-End Google Kubernetes Engine (GKE) Machine Learning Guide for Absolute Beginners
## From Zero to Production: gcloud Setup, kubectl Plugins, Model Fine-Tuning & Autoscaled Serving

---

### Welcome!
If you have never touched Google Cloud Platform (GCP), Kubernetes, or machine learning pipelines before, this guide is written specifically for you. Every single concept, installation step, and command is explained in plain English, with explicit instructions for **Windows (PowerShell)** as well as **macOS / Linux (Bash)**.

---

## Table of Contents
1. [Understanding the Big Picture & Project Structure](#1-understanding-the-big-picture--project-structure)
2. [Prerequisites & Google Cloud Account Setup](#2-prerequisites--google-cloud-account-setup)
3. [Step 1: Installing Google Cloud SDK (gcloud CLI)](#3-step-1-installing-google-cloud-sdk-gcloud-cli)
4. [Step 2: Installing Essential Plugins (kubectl & gke-gcloud-auth-plugin)](#4-step-2-installing-essential-plugins-kubectl--gke-gcloud-auth-plugin)
5. [Step 3: Enabling Required Google Cloud APIs](#5-step-3-enabling-required-google-cloud-apis)
6. [Step 4: Creating Your GKE Cluster & Connecting kubectl](#6-step-4-creating-your-gke-cluster--connecting-kubectl)
7. [Step 5: Project Environment & Storage Setup](#7-step-5-project-environment--storage-setup)
8. [Step 6: Building the Docker Container Image with Cloud Build](#8-step-6-building-the-docker-container-image-with-cloud-build)
9. [Step 7: Fine-Tuning the Model (Kubernetes Job)](#9-step-7-fine-tuning-the-model-kubernetes-job)
10. [Step 8: Serving the Model with FastAPI (Deployment + Service)](#10-step-8-serving-the-model-with-fastapi-deployment--service)
11. [Step 9: Testing Autoscaling Under Load (HPA)](#11-step-9-testing-autoscaling-under-load-hpa)
12. [Step 10: Clean Up & Avoiding Cloud Costs](#12-step-10-clean-up--avoiding-cloud-costs)
13. [Cost Optimization Tips](#13-cost-optimization-tips)
14. [Troubleshooting & Frequently Asked Questions (FAQ)](#14-troubleshooting--frequently-asked-questions-faq)
15. [Quick Command Cheatsheet](#15-quick-command-cheatsheet)

---

## 1. Understanding the Big Picture & Project Structure

Before running any commands, let's understand what we are building and why each piece exists:

```
+-----------------------------------------------------------------------------------+
|                               GOOGLE CLOUD PLATFORM                               |
|                                                                                   |
|  +---------------------------+       +-----------------------------------------+  |
|  | Google Cloud Storage      | <---> | GKE Autopilot Cluster                   |  |
|  | Bucket: gs://$BUCKET      |       |                                         |  |
|  |                           |       |  [Training Job: train.py]               |  |
|  | - Checkpoints every 50 st |       |  Mounts bucket via GCS FUSE CSI         |  |
|  | - Final Model Weights     |       |  Runs on 4 vCPUs, saves model to GCS    |  |
|  +---------------------------+       |                                         |  |
|               ^                      |  [Serving Deployment: serve.py]         |  |
|               | Read-Only Mount      |  FastAPI server loads weights from GCS  |  |
|               +--------------------> |  Autoscales from 1 to 5 replicas (HPA)  |  |
|                                      |                                         |  |
|  +---------------------------+       |  [Service (Port 80)]                    |  |
|  | Artifact Registry         | ----> |  Routes external/internal client calls  |  |
|  | Docker Image: app:v1      |       +-----------------------------------------+  |
|  +---------------------------+                                                    |
+-----------------------------------------------------------------------------------+
```

### Detailed Project File Structure:
```text
├── app/
│   ├── Dockerfile          # Single lean container image used for both training and inference
│   ├── requirements.txt    # CPU-optimized dependencies (PyTorch CPU, Transformers, FastAPI)
│   ├── train.py            # Hugging Face fine-tuning script with automatic checkpoint resumption
│   └── serve.py            # FastAPI inference server loading model from /data/model with greedy decoding
└── k8s/
    ├── train-job.yaml      # Kubernetes Job manifest mounting GCS bucket via GCS FUSE CSI driver
    └── serve.yaml          # Kubernetes Deployment, Service (Port 80), and HorizontalPodAutoscaler (HPA)
```

### Core Concepts Explained Simply:
- **Google Cloud Platform (GCP)**: Google's global cloud computing infrastructure.
- **`gcloud` CLI**: The official command-line tool used on your local machine to create and manage GCP resources.
- **Kubernetes (K8s)**: An open-source orchestrator that automatically manages, runs, monitors, and scales containerized applications.
- **Google Kubernetes Engine (GKE)**: Google's managed Kubernetes environment. In **Autopilot** mode, Google automatically provisions, secures, and optimizes the underlying infrastructure.
- **`kubectl`**: The command-line utility used to issue instructions directly to your Kubernetes cluster.
- **`gke-gcloud-auth-plugin`**: A mandatory security plugin required by Google Cloud so `kubectl` can safely authenticate with your GKE cluster.
- **GCS FUSE CSI Driver**: A built-in driver in GKE that mounts remote Google Cloud Storage buckets as local directories (`/data`) inside your containers.
- **SmolLM2-135M**: A state-of-the-art small language model by Hugging Face (135M parameters). It trains in minutes and performs fast inference on standard **CPUs** without expensive GPUs!

---

## 2. Prerequisites & Google Cloud Account Setup

### Step 2.1: Create a Google Cloud Account
1. Visit [Google Cloud Console](https://console.cloud.google.com/).
2. Sign in with your Google account.
3. If this is your first time, sign up for the **Google Cloud Free Trial** to get **$300** in free credits for 90 days.

### Step 2.2: Create a Cloud Project & Link Billing
1. In the Google Cloud Console, click the project dropdown menu in the top navigation bar and click **New Project**.
2. Name your project (e.g. `gke-ml-demo-2026`).
3. Take note of your unique **Project ID** (e.g., `gke-ml-demo-2026-xyz`). You will use this in commands later.
4. Ensure billing is linked to your project in **Billing** > **Link a billing account**.
   > **Note**: GKE and Cloud Build require an active billing account, even when covered by free credits.

---

## 3. Step 1: Installing Google Cloud SDK (gcloud CLI)

The `gcloud` CLI gives your terminal the ability to create clusters, upload images, and control Google Cloud.

### Option A: Installation on Windows (Recommended for Beginners)
1. Download the official Windows interactive installer:
   - Link: [Google Cloud SDK Windows Installer](https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe)
2. Run `GoogleCloudSDKInstaller.exe`.
3. In the installer wizard:
   - Keep the default installation directory.
   - Ensure the boxes for **"Start Google Cloud SDK Shell"** and **"Run gcloud init"** are checked.
   - Click **Finish**.

#### Alternative: PowerShell Silent Install
If you prefer using PowerShell directly, open PowerShell as Administrator and run:
```powershell
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:TEMP\GoogleCloudSDKInstaller.exe")
Start-Process -FilePath "$env:TEMP\GoogleCloudSDKInstaller.exe" -Wait
```

### Option B: Installation on macOS
Using Homebrew:
```bash
brew install --cask google-cloud-sdk
```

### Option C: Installation on Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-cli
```

---

### Step 3.2: Verify the Installation
Open a new PowerShell or Terminal window and run:
```bash
gcloud --version
```
You should see output similar to:
```text
Google Cloud SDK 510.0.0
bq 2.1.14
core 2026.02.10
gcloud-crc32c 1.0.0
gsutil 5.34
```

---

### Step 3.3: Initialize and Authenticate gcloud
Run the interactive setup wizard:
```bash
gcloud init
```
1. It will ask: `You must log in to continue. Would you like to log in (Y/n)?` Press **Y** and Enter.
2. A web browser window will open. Select your Google account and click **Allow**.
3. Return to your terminal. It will prompt you to pick your Cloud Project:
   - Type the number corresponding to your Project ID (or create one).
4. When asked to configure a default Compute Region and Zone, pick `us-central1` (e.g. `us-central1-a` or `us-central1-c`).

---

## 4. Step 2: Installing Essential Plugins (kubectl & gke-gcloud-auth-plugin)

By default, the base `gcloud` installation does not include Kubernetes tools. You must install two crucial components: `kubectl` and `gke-gcloud-auth-plugin`.

### Step 4.1: Install `kubectl`
`kubectl` is the primary CLI to interact with Kubernetes. Install it using the `gcloud components` manager:

```bash
gcloud components install kubectl
```
- Press **Y** when prompted to confirm the installation.
- Verify `kubectl` is working:
```bash
kubectl version --client
```
Output:
```text
Client Version: v1.31.x
Kustomize Version: v5.0.x
```

---

### Step 4.2: Install `gke-gcloud-auth-plugin` (MANDATORY)
> **CRITICAL WARNING FOR BEGINNERS**:
> In modern Kubernetes (v1.26+), the old authentication provider was removed. If you try to connect to GKE without this plugin, you will get the error:
> `Error: loading auth plugin: gke-gcloud-auth-plugin is missing`.

Install the authentication plugin with:
```bash
gcloud components install gke-gcloud-auth-plugin
```
- Press **Y** to confirm.
- Verify the plugin installation:
```bash
gke-gcloud-auth-plugin --version
```
Output:
```text
Kubernetes Engine Client Authentication Plugin 0.5.x
```

*(Note for Linux package manager users: if you installed via `apt`, use `sudo apt-get install google-cloud-cli-gke-gcloud-auth-plugin kubectl`).*

---

## 5. Step 3: Enabling Required Google Cloud APIs

Google Cloud services are disabled by default until you enable their APIs for your project. Enable all required services with a single command:

```bash
gcloud services enable container.googleapis.com \
                       artifactregistry.googleapis.com \
                       cloudbuild.googleapis.com \
                       storage.googleapis.com
```

### What Each API Does:
| API | Service | Purpose in this Project |
| :--- | :--- | :--- |
| `container.googleapis.com` | Google Kubernetes Engine | Hosts our training jobs and model deployment pods |
| `artifactregistry.googleapis.com` | Artifact Registry | Securely stores our custom Docker container images |
| `cloudbuild.googleapis.com` | Cloud Build | Builds our Docker images in Google's cloud (no local Docker required!) |
| `storage.googleapis.com` | Cloud Storage | Stores model checkpoints and final weights in a bucket |

---

## 6. Step 4: Creating Your GKE Cluster & Connecting kubectl

The repository relies on two specific GKE features:
1. **Workload Identity**: Allows Kubernetes Pods to talk to Google Cloud Storage securely without storing secret password keys in files.
2. **GCS FUSE CSI Driver**: Allows Pods to mount a Google Cloud Storage bucket as a standard folder (`/data`).

Both of these features are **automatically enabled out-of-the-box** in **GKE Autopilot**!

### Step 4.1: Create the Autopilot Cluster
Run the following command to create your cluster (this takes about 5 to 7 minutes):

#### On Windows (PowerShell):
```powershell
gcloud container clusters create-auto ml-cluster `
  --region us-central1 `
  --project $PROJECT_ID
```

#### On macOS / Linux (Bash):
```bash
gcloud container clusters create-auto ml-cluster \
  --region us-central1 \
  --project $PROJECT_ID
```

> **Why GKE Autopilot?**
> In standard clusters, you pay for virtual machine instances 24/7 even when idle. In Autopilot, you only pay for the exact CPU and memory resources requested by your running pods!

---

### Step 4.2: Fetch Credentials for `kubectl`
Configure your local `kubectl` to talk to your new cluster:

#### On Windows (PowerShell):
```powershell
gcloud container clusters get-credentials ml-cluster `
  --region us-central1 `
  --project $PROJECT_ID
```

#### On macOS / Linux (Bash):
```bash
gcloud container clusters get-credentials ml-cluster \
  --region us-central1 \
  --project $PROJECT_ID
```

---

### Step 4.3: Test the Connection
Verify that `kubectl` is communicating with the cluster:
```bash
kubectl get nodes
```
You should see your cluster nodes listed with `STATUS: Ready`.

---

## 7. Step 5: Project Environment & Storage Setup

Now let's configure the storage bucket, container registry, security permissions, and uniform bucket access.

### Step 5.1: Define Variables in Your Terminal

#### On Windows (PowerShell):
```powershell
$PROJECT_ID = gcloud config get-value project
$REGION = "us-central1"
$BUCKET = "${PROJECT_ID}-ml"
$IMAGE = "${REGION}-docker.pkg.dev/${PROJECT_ID}/ml/app:v1"
$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

Write-Host "Project ID:     $PROJECT_ID"
Write-Host "Project Number: $PROJECT_NUMBER"
Write-Host "Bucket:         $BUCKET"
Write-Host "Image:          $IMAGE"
```

#### On macOS / Linux (Bash):
```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export BUCKET=${PROJECT_ID}-ml
export IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/ml/app:v1
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

echo "Project ID:     $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "Bucket:         $BUCKET"
echo "Image:          $IMAGE"
```

---

### Step 5.2: Create the Storage Bucket
Create a Google Cloud Storage bucket to store your training checkpoints and fine-tuned model:
```bash
gcloud storage buckets create gs://$BUCKET --location=$REGION
```

---

### Step 5.3: Create the Artifact Registry Repository
Create a Docker repository named `ml` inside Artifact Registry:
```bash
gcloud artifacts repositories create ml --repository-format=docker --location=$REGION
```

---

### Step 5.4: Create the Kubernetes Service Account (KSA)
Inside your cluster, create a Service Account named `ml-sa` that our training and serving pods will use:
```bash
kubectl create serviceaccount ml-sa
```

---

### Step 5.5: Bind IAM Permissions (Workload Identity)
Grant `ml-sa` permission to read and write to your Cloud Storage bucket without needing any secret JSON key files:

#### On Windows (PowerShell):
```powershell
gcloud storage buckets add-iam-policy-binding gs://$BUCKET `
  --role=roles/storage.objectUser `
  --member="principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$PROJECT_ID.svc.id.goog/subject/ns/default/sa/ml-sa"
```

#### On macOS / Linux (Bash):
```bash
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --role=roles/storage.objectUser \
  --member=principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$PROJECT_ID.svc.id.goog/subject/ns/default/sa/ml-sa
```

---

### Step 5.6: Enable Uniform Bucket-Level Access
Enable uniform bucket-level access on your GCS bucket. This is an essential best practice in Google Cloud that disables legacy individual object ACLs and ensures all access is governed cleanly by your IAM Workload Identity policy:

#### On Windows (PowerShell):
```powershell
gcloud storage buckets update gs://${PROJECT_ID}-ml --uniform-bucket-level-access
```

#### On macOS / Linux (Bash):
```bash
gcloud storage buckets update gs://${PROJECT_ID}-ml --uniform-bucket-level-access
```

---

## 8. Step 6: Building the Docker Container Image with Cloud Build

You do **not** need Docker installed on your computer! We will use **Google Cloud Build** to package the code and send it directly to your Artifact Registry.

### Step 8.1: Submit the Build
Make sure you are in the root directory of the repository (`gke-ml-min`), then run:

```bash
gcloud builds submit app --tag $IMAGE
```

### What Happens During the Build:
1. Google Cloud Build uploads the `app/` folder (containing `Dockerfile`, `requirements.txt`, `train.py`, and `serve.py`).
2. Google's cloud servers run the Docker build steps:
   - Installs PyTorch (CPU-optimized build).
   - Installs Hugging Face `transformers`, `datasets`, and `accelerate`.
   - Installs `fastapi` and `uvicorn`.
3. The resulting container image is pushed to your private Artifact Registry at `${IMAGE}`.

Build completion typically takes 2 to 4 minutes. You will see `SUCCESS` at the end of the log stream.

---

## 9. Step 7: Fine-Tuning the Model (Kubernetes Job)

A Kubernetes **Job** runs a pod to completion (unlike a web server that runs forever).

### Step 7.1: How Training Works Under the Hood
- The job runs `python train.py`.
- It loads `HuggingFaceTB/SmolLM2-135M-Instruct`.
- It fine-tunes on 500 instruction samples from the `databricks/databricks-dolly-15k` dataset.
- It mounts the GCS bucket at `/data` via GCS FUSE CSI driver.
- Every 50 training steps, it writes a checkpoint to `gs://$BUCKET/checkpoints`.
- **Fault-Tolerant Checkpointing**: If the pod dies or is killed, the Job automatically restarts it and training resumes from the last saved checkpoint!
- When training finishes, the final model is written to `gs://$BUCKET/model`. That folder is the hand-off from training to production.
- Training takes roughly **10–20 minutes** on 4 vCPUs with the default 500 samples.

---

### Step 7.2: Deploy the Training Job

We need to inject our `$IMAGE` and `$BUCKET` variables into `k8s/train-job.yaml`.

#### On Windows (PowerShell):
```powershell
(Get-Content k8s\train-job.yaml) -replace '\$\{IMAGE\}', $IMAGE -replace '\$\{BUCKET\}', $BUCKET | kubectl apply -f -
```

#### On macOS / Linux (Bash):
```bash
envsubst < k8s/train-job.yaml | kubectl apply -f -
```

---

### Step 7.3: Monitor Training Logs
Check the status of the job:
```bash
kubectl get jobs
kubectl get pods
```

Stream live training logs from the running pod:
```bash
kubectl logs -f job/train
```

You will see Hugging Face training logs showing progress, loss, and step updates:
```text
resume_from_checkpoint=False
{'loss': 2.3412, 'learning_rate': 4.5e-05, 'epoch': 0.08}
{'loss': 2.1054, 'learning_rate': 4.0e-05, 'epoch': 0.16}
...
Saving model checkpoint to /data/checkpoints/checkpoint-50
...
model saved to /data/model
```

---

### Step 7.4: Test Pod Failure Recovery (Self-Healing)
Want to verify that checkpoint recovery actually works? While the training job is running, delete the pod in another terminal:
```bash
kubectl delete pod -l job-name=train
```
Kubernetes will immediately detect the pod was terminated, spin up a new pod, and you will see:
```text
resume_from_checkpoint=True
Resuming training from /data/checkpoints/checkpoint-50
```
Training seamlessly continues without losing progress!

---

### Step 7.5: Verify Model Saved in Cloud Storage
Once the job status shows `COMPLETED`, check your bucket:
```bash
gcloud storage ls gs://$BUCKET/model/
```
You will see `config.json`, `model.safetensors`, `tokenizer.json`, etc.

---

## 10. Step 8: Serving the Model with FastAPI (Deployment + Service)

Now we deploy our fine-tuned model via a production-grade FastAPI REST API.

### Step 8.1: Deploy the Server

#### On Windows (PowerShell):
```powershell
(Get-Content k8s\serve.yaml) -replace '\$\{IMAGE\}', $IMAGE -replace '\$\{BUCKET\}', $BUCKET | kubectl apply -f -
```

#### On macOS / Linux (Bash):
```bash
envsubst < k8s/serve.yaml | kubectl apply -f -
```

---

### Step 8.2: Wait for Deployment Rollout
Wait until the server pod mounts the GCS bucket read-only, loads the weights into memory, and passes its `/health` check:
```bash
kubectl rollout status deploy/model-server
```
Output:
```text
deployment "model-server" successfully rolled out
```

---

### Step 8.3: Port-Forward and Access the API
Forward local port 8080 to the Kubernetes Service port 80:
```bash
kubectl port-forward svc/model-server 8080:80
```
*(Leave this terminal window running!).*

---

### Step 8.4: API Endpoints Reference Table

| Endpoint | Method | URL | Description / Response |
| :--- | :---: | :--- | :--- |
| **Health Check** | `GET` | `http://localhost:8080/health` | Returns `{"status":"ok"}` when the pod is ready to accept traffic. |
| **Interactive Docs** | `GET` | `http://localhost:8080/docs` | Swagger UI web interface where you can test prompts directly in your browser. |
| **Inference** | `POST` | `http://localhost:8080/generate` | Accepts prompt JSON and streams generated model completion. |

---

### Step 8.5: Send a Test Inference Request
Open a **second terminal window** to test:

#### On Windows (PowerShell):
```powershell
Invoke-RestMethod -Uri "http://localhost:8080/generate" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"prompt": "What is Kubernetes?", "max_tokens": 64}' | ConvertTo-Json
```

#### On macOS / Linux (Bash):
```bash
curl -s localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Kubernetes?", "max_tokens": 64}'
```

#### Example Response:
```json
{
  "completion": "Kubernetes is an open-source container orchestration system that automates the deployment, scaling, and management of containerized applications."
}
```

#### Test Swagger Interactive Docs in Browser:
Open your web browser and navigate to:
```text
http://localhost:8080/docs
```
You can click on `/generate` > **Try it out**, type any prompt, and click **Execute** to see live output!

---

## 11. Step 9: Testing Autoscaling Under Load (HPA)

The file `k8s/serve.yaml` includes a **HorizontalPodAutoscaler (HPA)**. When average CPU utilization exceeds **70%**, Kubernetes automatically adds replicas (up to 5 pods). On GKE Autopilot, new VM nodes appear automatically when replicas need them!

### Step 9.1: Watch the Autoscaler in Real Time
In your terminal, run:
```bash
kubectl get hpa model-server --watch
```

---

### Step 9.2: Generate Traffic Load
In another terminal, send 200 concurrent inference requests to trigger CPU usage:

#### On Windows (PowerShell):
```powershell
1..150 | ForEach-Object {
    Start-Job -ScriptBlock {
        Invoke-RestMethod -Uri "http://localhost:8080/generate" -Method Post -ContentType "application/json" -Body '{"prompt": "Explain autoscaling", "max_tokens": 64}' | Out-Null
    }
} | Out-Null
```

#### On macOS / Linux (Bash):
```bash
for i in $(seq 1 200); do
  curl -s localhost:8080/generate -H 'Content-Type: application/json' \
    -d '{"prompt":"Explain autoscaling","max_tokens":64}' >/dev/null &
done
```

### Step 9.3: Observe Replicas Scaling Up
Within 30–60 seconds, watch the `REPLICAS` column in your `kubectl get hpa` terminal change from `1` to `2`, `3`, or `4`!
Once the traffic loop completes and CPU drops below 70%, GKE Autopilot will gently scale back down to `1` replica to minimize cost.

---

## 12. Step 10: Clean Up & Avoiding Cloud Costs

Always clean up your cloud resources when you are finished practicing to avoid unexpected billing charges!

### Step 12.1: Delete Kubernetes Workloads
```bash
kubectl delete -f k8s/serve.yaml --ignore-not-found
kubectl delete job train
```

### Step 12.2: Delete the Cloud Storage Bucket
```bash
gcloud storage rm -r gs://$BUCKET
```

### Step 12.3: Delete the Artifact Registry Repository
```bash
gcloud artifacts repositories delete ml --location=$REGION --quiet
```

### Step 12.4: Delete the GKE Cluster
> **IMPORTANT**: The cluster is the primary ongoing cost if left active. Delete it when done:
```bash
gcloud container clusters delete ml-cluster --region=$REGION --quiet
```

---

## 13. Cost Optimization Tips

> **Key Takeaways for Running ML on GCP:**
> - **Pay for training only while it runs:** A Kubernetes Job's pods terminate immediately upon completion, so nothing continues to bill you once training is done.
> - **Keep the model small:** On CPU, a 135M-parameter model trains in ~15 minutes and serves fast; larger models need GPUs which cost significantly more per hour.
> - **Set `minReplicas` to what you need:** The HPA scales up on load and back down to the minimum when idle. Setting `minReplicas: 1` ensures idle servers don't consume unnecessary resources.
> - **Right-size requests:** On GKE Autopilot you are billed by pod resource requests, so match `cpu` and `memory` to what the pod actually uses. You can inspect live usage with:
>   ```bash
>   kubectl top pod
>   ```

---

## 14. Troubleshooting & Frequently Asked Questions (FAQ)

### Q1: `Error: loading auth plugin: gke-gcloud-auth-plugin is missing`
- **Why**: Modern Kubernetes requires Google's authentication plugin.
- **Fix**: Run `gcloud components install gke-gcloud-auth-plugin`. If you are using Git Bash or PowerShell, restart the terminal window so your system `PATH` is refreshed.

---

### Q2: `'envsubst' is not recognized as an internal or external command` (Windows)
- **Why**: `envsubst` is a Linux/Unix command.
- **Fix**: Use the native PowerShell replacement command provided in this guide:
  ```powershell
  (Get-Content k8s\serve.yaml) -replace '\$\{IMAGE\}', $IMAGE -replace '\$\{BUCKET\}', $BUCKET | kubectl apply -f -
  ```

---

### Q3: `PermissionDenied` when mounting GCS bucket in Pod
- **Why**: The Kubernetes Service Account (`ml-sa`) does not have the `roles/storage.objectUser` IAM role binding on the bucket, or bucket access is restricted by legacy ACLs.
- **Fix**:
  1. Re-run the IAM policy binding command in Step 5.5, ensuring `$PROJECT_NUMBER` and `$PROJECT_ID` are accurately resolved.
  2. Ensure uniform bucket-level access is enabled: `gcloud storage buckets update gs://${PROJECT_ID}-ml --uniform-bucket-level-access`.

---

### Q4: Pod status says `Pending` or `CrashLoopBackOff`
- **Check logs**: `kubectl describe pod <pod-name>` or `kubectl logs <pod-name>`.
- In GKE Autopilot, when a pod requests CPU/memory, Autopilot automatically provisions a new node. This can take 60 to 90 seconds. Run `kubectl get nodes` to see nodes appearing.

---

### Q5: How much does running this cost?
- **Compute**: Under GKE Autopilot, you only pay for pod requests while active. 4 vCPUs for 15 minutes of training costs less than **$0.15 USD**.
- **Cloud Build**: Free tier includes 120 free build-minutes per day.
- **Storage**: A few gigabytes in GCS costs a fraction of a cent per day.
- Always run the cleanup steps in Step 12 when you are done.

---

## 15. Quick Command Cheatsheet

| Step | PowerShell (Windows) | Bash (macOS / Linux) |
| :--- | :--- | :--- |
| **Install kubectl** | `gcloud components install kubectl` | `gcloud components install kubectl` |
| **Install Auth Plugin** | `gcloud components install gke-gcloud-auth-plugin` | `gcloud components install gke-gcloud-auth-plugin` |
| **Enable APIs** | `gcloud services enable container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com storage.googleapis.com` | `gcloud services enable container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com storage.googleapis.com` |
| **Create Cluster** | `gcloud container clusters create-auto ml-cluster --region us-central1 --project $PROJECT_ID` | `gcloud container clusters create-auto ml-cluster --region us-central1 --project $PROJECT_ID` |
| **Get Credentials** | `gcloud container clusters get-credentials ml-cluster --region us-central1 --project $PROJECT_ID` | `gcloud container clusters get-credentials ml-cluster --region us-central1 --project $PROJECT_ID` |
| **Uniform Bucket Access** | `gcloud storage buckets update gs://${PROJECT_ID}-ml --uniform-bucket-level-access` | `gcloud storage buckets update gs://${PROJECT_ID}-ml --uniform-bucket-level-access` |
| **Build Container** | `gcloud builds submit app --tag $IMAGE` | `gcloud builds submit app --tag $IMAGE` |
| **Run Training** | `(Get-Content k8s\train-job.yaml) -replace '\$\{IMAGE\}', $IMAGE -replace '\$\{BUCKET\}', $BUCKET \| kubectl apply -f -` | `envsubst < k8s/train-job.yaml \| kubectl apply -f -` |
| **Test Pod Recovery** | `kubectl delete pod -l job-name=train` | `kubectl delete pod -l job-name=train` |
| **Deploy Server** | `(Get-Content k8s\serve.yaml) -replace '\$\{IMAGE\}', $IMAGE -replace '\$\{BUCKET\}', $BUCKET \| kubectl apply -f -` | `envsubst < k8s/serve.yaml \| kubectl apply -f -` |
| **Port Forward** | `kubectl port-forward svc/model-server 8080:80` | `kubectl port-forward svc/model-server 8080:80` |
| **Interactive Docs** | Open `http://localhost:8080/docs` in browser | Open `http://localhost:8080/docs` in browser |
| **Delete Cluster** | `gcloud container clusters delete ml-cluster --region=$REGION --quiet` | `gcloud container clusters delete ml-cluster --region=$REGION --quiet` |
