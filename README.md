# NeuroVision AI

A web platform for brain tumour segmentation on MRI. A user uploads brain MRI scans, a deep-learning model
segments the tumour into three regions, and the user reviews the result slice by slice and downloads a PDF report.

- **Whole tumour (WT)** – all tumour tissue
- **Tumour core (TC)** – necrotic core + enhancing tumour
- **Enhancing tumour (ET)** – contrast-enhancing tumour

> **For research and education only.** NeuroVision AI is not a medical device and must not be used for diagnosis.

COMP6016 Computer Science Project 2 · Curtin University · Group 02 · Supervisor: Dr Chayan Mondal
Team: Ahnaf Shahriar Ifti, Zaha Usmani, Md Rezaunnabi

---

## Contents

1. [What is in this repository](#1-what-is-in-this-repository)
2. [Quick start on macOS](#2-quick-start-on-macos)
3. [Quick start on Windows](#3-quick-start-on-windows)
4. [Run with Docker](#4-run-with-docker)
5. [Using the web app](#5-using-the-web-app)
6. [Configuration (.env)](#6-configuration-env)
7. [The models](#7-the-models)
8. [Testing](#8-testing)
9. [Data management](#9-data-management)
10. [Troubleshooting](#10-troubleshooting)
11. [Known issues and future work](#11-known-issues-and-future-work)

---

## 1. What is in this repository

| Folder / file | What it is |
|---|---|
| `config/` | Django settings, URLs, WSGI/ASGI |
| `accounts/` | Login, logout, password change, optional registration |
| `analysis/` | Upload, analysis queue, worker, results viewer, PDF report, scan history |
| `analysis/services/` | NIfTI validation, preprocessing, model loading, inference, slice images, reports |
| `analysis/management/commands/` | `run_analysis_worker` (background worker) and `recover_analysis` |
| `dashboard/` | Overview dashboard, Model insights page, Settings page |
| `performance/` | Model performance page (reads `data/benchmarks/notebook_results.csv`) |
| `ml_models/` | Model definition and `checkpoints/` (trained weights) |
| `templates/`, `static/` | HTML templates, CSS (Tailwind), JavaScript (upload, viewer, charts) |
| `tools/` | Front-end gateway, Windows launcher, browser check, benchmark extractor |
| `deploy/nginx.conf` | nginx gateway used by Docker Compose |
| `Dockerfile`, `compose.yaml` | Container setup (backend, worker, nginx, PostgreSQL) |
| `requirements.txt` | Python packages (pinned versions) |
| `requirements-dev.txt` | Extra packages for browser testing (Playwright) |

**How it works:** the browser talks to a small gateway (port 9130), which forwards requests to the Django
web server (port 9131). An upload is saved and queued in the database at once, and a separate **worker**
process picks up the job, runs the model, and saves the results. The page shows live progress and then the
interactive viewer.

```
Browser ──► Gateway :9130 ──► Django :9131 ──► Database (job queue)
                                   │                    ▲
                                   ▼                    │ polls
                           Media storage ◄──── Analysis worker ──► model checkpoint
```

---

## 2. Quick start on macOS

**Needs:** Git, Python **3.13** (macOS ships with Python 3.9, which is too old; install 3.13 from
[python.org](https://www.python.org/downloads/)), and about 5 GB of free disk space.

### Step 1 – Check the tools
```bash
git --version
python3.13 --version
```

### Step 2 – Get the code
```bash
git clone https://github.com/AhnafIfti/Web-Platform-for-Brain-Tumor-Detection-and-Predictive-Outcome-Modeling.git
cd Web-Platform-for-Brain-Tumor-Detection-and-Predictive-Outcome-Modeling
```

### Step 3 – Download the model weights
The trained weights (`swin_tiny_unet.pth`, about 121 MB) are too large for GitHub, so they are shared on Google Drive.

1. Download the file from: https://drive.google.com/file/d/1RsuG0QU-mJIJem6j9w-H88kl_pwxvdCI/view?usp=sharing
   (it is saved to your **Downloads** folder; if Drive says it cannot scan the file for viruses, click **Download anyway**).
2. Move it into the project's checkpoint folder and check it is there:
   ```bash
   mkdir -p ml_models/checkpoints
   mv ~/Downloads/swin_tiny_unet.pth ml_models/checkpoints/
   ls -lh ml_models/checkpoints/
   ```
   You should see `swin_tiny_unet.pth` of about 121 MB. The name must stay exactly `swin_tiny_unet.pth`.

Without this file the website still opens, but analyses stay disabled ("Model unavailable").

### Step 4 – Create the virtual environment and install the packages (5–10 minutes)
```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5 – Create the local settings file
`DEBUG=true` is required for local `http://` use; without it the app forces HTTPS.
```bash
cat > .env <<EOF
DEBUG=true
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
REGISTRATION_ENABLED=false
EOF
```

### Step 6 – Create the database and the first account
```bash
python manage.py migrate
python manage.py createsuperuser
```
Enter a username and password (the password is not shown while you type).

### Step 7 – Start the three services, one per Terminal tab
Open two more tabs with **Cmd+T**. In each new tab, go to the project folder and activate the environment first:
```bash
cd ~/Desktop/Web-Platform-for-Brain-Tumor-Detection-and-Predictive-Outcome-Modeling   # your project folder
source .venv/bin/activate
```

| Tab | Command | Service |
|---|---|---|
| 1 | `python manage.py runserver 127.0.0.1:9131 --noreload` | Django web server |
| 2 | `python tools/frontend_server.py --port 9130 --backend-port 9131` | Gateway (open this one) |
| 3 | `python manage.py run_analysis_worker` | Analysis worker (runs the model) |

### Step 8 – Open the website
Go to **http://127.0.0.1:9130/** and sign in with the account from step 6.

Stop everything with **Ctrl+C** in each tab. Next time, only steps 7 and 8 are needed.

---

## 3. Quick start on Windows

1. Install Python 3.12/3.13 and create the virtual environment in the project folder:
   ```bat
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Create `.env` with the same three lines as in section 2 (`DEBUG=true`, a long random `SECRET_KEY`,
   `REGISTRATION_ENABLED=false`).
3. `python manage.py migrate` and `python manage.py createsuperuser`
4. Double-click **`Launch NeuroVision.bat`**. It starts the web server (9131), the gateway (9130) and the worker,
   then opens the browser. Logs are written to `tmp/launcher/`.

---

## 4. Run with Docker

**Needs:** Docker Desktop (running), about 15–20 GB free disk space. The first build takes 10–30 minutes.

1. Add a `.dockerignore` so local files are not copied into the image:
   ```
   .venv
   node_modules
   *.zip
   db.sqlite3
   media
   tmp
   .env
   ```
2. Create `.env` (Docker also needs a database password):
   ```bash
   cat > .env <<EOF
   DEBUG=true
   SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
   POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(20))")
   REGISTRATION_ENABLED=false
   EOF
   ```
3. Build and start the four services (backend, worker, nginx, PostgreSQL):
   ```bash
   docker compose up --build -d
   docker compose ps
   ```
4. Create the database tables and an account (the Docker database is separate from the local one):
   ```bash
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```
5. Open **http://127.0.0.1:9130/**.

| Task | Command |
|---|---|
| Stop | `docker compose down` |
| Start again | `docker compose up -d` |
| Worker logs | `docker compose logs -f worker` |
| Rebuild after code changes | `docker compose up --build -d` |

**Tip for laptops without an NVIDIA GPU:** the default PyTorch download for Linux includes large CUDA
libraries. To build faster, install the CPU-only PyTorch first by replacing the `pip install` line in the
`Dockerfile` with:
```dockerfile
RUN pip install --no-cache-dir torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
```
Keep the original line on a GPU server.

---

## 5. Using the web app

1. **Sign in.** Public registration is off by default; an administrator creates accounts
   (http://127.0.0.1:9130/admin/ → Users → Add user, or `python manage.py createsuperuser`).
2. **New analysis.** Choose a co-registered, skull-stripped **FLAIR** and **T1ce** volume (`.nii` or `.nii.gz`,
   same size and position), tick the consent box and click **Run AI analysis**.
   Example input: `BraTS2021_00000_flair.nii.gz` and `BraTS2021_00000_t1ce.nii.gz`.
3. **Wait for the result.** The page shows the stage and slice progress. You can leave and come back from
   **Scan history**. On a laptop CPU an analysis takes a few minutes.
4. **Review.** Switch between Overlay / Original / Mask, toggle WT / TC / ET, change opacity, zoom,
   move through slices with the slider or arrow keys, and click a chart to jump to a slice.
5. **Report.** Download the PDF report or the current slice as PNG. Delete the analysis to remove its scans
   and results.

Other pages: **Dashboard** (totals, average inference time, recent analyses), **Scan history** (search,
status filter, pages), **Model performance** (benchmark table and Dice charts), **Model insights**
(architecture, pipeline, regions, limitations) and **Settings** (account and model configuration).

---

## 6. Configuration (.env)

All settings are environment variables, read from `.env` in the project folder. Never commit `.env`.

| Setting | Default | What it controls |
|---|---|---|
| `DEBUG` | `false` | `true` for local use. With `false` the app forces HTTPS and secure cookies. |
| `SECRET_KEY` | — (required when `DEBUG=false`) | Django secret key; use a long random value |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Host names the server answers |
| `CSRF_TRUSTED_ORIGINS` | empty | Needed when serving from a real domain (e.g. `https://example.org`) |
| `DATABASE_URL` | SQLite (`db.sqlite3`) | e.g. `postgres://user:pass@host:5432/neurovision` |
| `MEDIA_ROOT` | `media/` | Where uploads and results are stored |
| `MODEL_CHECKPOINT_PATH` | `ml_models/checkpoints/swin_tiny_unet.pth` | Trained weights loaded by the worker |
| `MODEL_VERSION` | `swin-tiny-unet-v2` | Name recorded with each analysis |
| `MODEL_DEVICE` | `auto` | `auto` = GPU if available, otherwise CPU; or `cpu` / `cuda` |
| `SEGMENTATION_THRESHOLD` | `0.5` | Probability cut-off for the saved masks (between 0 and 1) |
| `MAX_UPLOAD_SIZE_MB` | `128` | Largest file per scan |
| `MAX_UNCOMPRESSED_MRI_MB` | `256` | Limit on the unpacked `.nii.gz` size |
| `MAX_VOLUME_VOXELS` / `MAX_VOLUME_SLICES` | `16777216` / `512` | Limits on volume size |
| `REGISTRATION_ENABLED` | `false` | `true` shows a public sign-up page at `/register/` |
| `BENCHMARK_CSV` | `data/benchmarks/notebook_results.csv` | Table shown on the Model performance page |
| `POSTGRES_PASSWORD` | — | Required by Docker Compose |

**Before any real deployment:** set `DEBUG=false`, a new `SECRET_KEY`, `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`, put TLS (HTTPS) in front of nginx, and back up the `database_data` and `mri_data` volumes.
Restart the worker after changing the model.

---

## 7. The models

### Current model in the web app: Swin-Tiny U-Net (2D)
- File: `ml_models/checkpoints/swin_tiny_unet.pth` (download from Google Drive, see section 2 step 3; definition in `ml_models/model_definition.py`)
- Inputs: FLAIR + T1ce, one axial slice at a time, resized to 224 × 224
- Output: three sigmoid maps (WT, TC, ET), thresholded at `SEGMENTATION_THRESHOLD`

### Final research model: combined nnU-Net (3D) — integration in progress
- nnU-Net v2 (2.8.1), Residual Encoder U-Net (ResEnc M), region-based training (WT, TC, ET)
- Combined settings from an ablation study: Batch Dice + BCE loss, stronger augmentation (DA5),
  50 % tumour-centred patches, 128 × 160 × 160 patches, 70 % sliding-window overlap, flip test-time augmentation
- Post-processing tuned on validation: remove tumour outside the brain, and small pieces
  (ET < 25, TC < 50, WT < 100 voxels)
- Trained on BraTS 2021 (fold 0: 1,000 training / 251 validation patients)
- **Validation (251 patients): mean Dice 0.9208** (ET 0.8993, TC 0.9227, WT 0.9404), mean HD95 5.19 mm
- Also tested on 219 unseen BraTS 2023 validation patients
- Inputs: **4 scans** (FLAIR, T1ce, T1, T2) as full 3D volumes; outputs a BraTS-format mask
  (0, 1 NCR, 2 ED, 4 ET) and tumour volumes in mL

To use it, the model package (`model_package/` or `model_package_5fold/`, made with `make_model_package.py`)
is loaded by `brain_seg_model.py`:
```python
from brain_seg_model import BrainTumourSegmenter
seg_model = BrainTumourSegmenter("model_package_5fold")      # load once
result = seg_model.predict(flair, t1ce, t1, t2, out_dir="media/results", case_id="BraTS2021_00000")
```
Connecting it to the web app needs four upload fields instead of two and a single 3D prediction
instead of the 2D slice loop (see the project report for the full list of changes).

---

## 8. Testing

**Automated tests** (Django test runner, model and web views):
```bash
python manage.py test --settings=config.test_settings
```
Tests are in `analysis/tests/` (`test_pipeline.py`, `test_web.py`, `test_browser.py`).
Browser tests run only with `RUN_BROWSER_TESTS=1` and need Playwright:
```bash
pip install -r requirements-dev.txt
playwright install chromium
RUN_BROWSER_TESTS=1 python manage.py test --settings=config.test_settings
```

**Visual check of the running app** (start the three services first; needs Google Chrome):
```bash
python tools/browser_check.py
```
It signs in with a local test account (saved in `.local-access.txt`), opens the main pages, checks the
benchmark filter, rejects an invalid upload, checks layouts at desktop, tablet and mobile widths, and saves
screenshots to `docs/screenshots/`.

**Model testing:** per-patient Dice and HD95 for ET, TC and WT on 251 validation patients, plus testing on
219 unseen patients (see section 7).

---

## 9. Data management

- **Training data:** BraTS 2021 (1,251 patients), anonymised, used under the BraTS data terms.
  It cannot be redistributed and is **not** in this repository; download it from the official source.
- **Uploads:** stored under random UUID names in `MEDIA_ROOT`, private to the account that uploaded them.
- **Results:** masks, slice images, per-slice statistics, inference time and model version, stored in the
  database and media folder. Deleting an analysis removes its scans and results.
- **Not in the repository:** `.env`, `db.sqlite3`, `media/`, `.venv/`, and the model checkpoint (download it from the Google Drive link in section 2, step 3).

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `No matching distribution found for Django==6.1.1` | Python is too old. Use 3.12/3.13 and recreate `.venv`. |
| The site keeps redirecting to `https://` | Set `DEBUG=true` in `.env` for local use. |
| `That port is already in use` | Another copy is running. Stop it, or use other ports (e.g. 9141 / 9140). |
| Upload page says **Model unavailable** | Download `swin_tiny_unet.pth` from the Google Drive link in section 2 (step 3), put it in `ml_models/checkpoints/`, then restart the worker. |
| Analysis stays **Queued** | The worker is not running. Start `python manage.py run_analysis_worker`. |
| An analysis was interrupted | Stop the worker, then `python manage.py recover_analysis <analysis-id> --worker-stopped`, then start the worker again. |
| Pages look unstyled | Make sure `static/` is next to `manage.py`. To rebuild Tailwind: `npm install` then `npm run build:css`. |
| Docker: `failed to connect to the docker API` | Start Docker Desktop and wait until it says "running". |
| Docker build is very slow | Use the CPU-only PyTorch tip in section 4. |

---

## 11. Known issues and future work

**Known issues**
- The web app still runs the 2D Swin-Tiny model; the combined 3D nnU-Net model is not yet connected.
- The Model insights and Model performance pages describe the Swin-Tiny model and older 2D benchmarks.
- The viewer shows axial slices only.
- Uploaded scans must already be co-registered and skull-stripped; the app does not do this.
- Cross-browser and screen-reader testing have not been done.

**Future work**
1. Connect the combined nnU-Net model (four-scan upload, 3D prediction, volumes in mL).
2. Report 5-fold results for the combined model and test on more independent data (e.g. BraTS-Africa).
3. Add sagittal and coronal views and a 3D view.
4. Run the tests in continuous integration.
5. Before any real use: TLS, a data retention policy, encrypted storage, an audit log, and ethics and clinical review.

## 12. Using the web app
Sample MRI scan for testing

To try the app without your own data, download one sample patient: https://drive.google.com/file/d/1oA71Yqpil9hfVZTg_74-3PtoxxjwcbAT/view?usp=drive_link
