# Project Stages Overview

This document outlines the 6 development stages of the AI Crop Insurance project. Every stage builds on top of the previous one to fulfill the mentor's research requirements step-by-step.

---

## The 6-Stage Roadmap at a Glance

```text
Stage 1: Photo Inspection (Vision AI)
   │     - Checks if crop is Healthy or Damaged
   │     - Calculates Damage Severity % (0% to 100%)
   ▼
Stage 2: Historical Weather Verification
   │     - Checks rainfall, temperature, and drought records from ERA5/NOAA
   │     - Verifies if the weather matches the claimed disaster
   ▼
Stage 3: Satellite Imagery & Field Damage Assessment
   │     - Analyzes Sentinel-2 multispectral satellite observations
   │     - Calculates NDVI vegetation drop before and after disaster
   │     - Estimates percentage of total land area damaged
   ▼
Stage 4: Multimodal AI Fusion & Fraud Detection (XGBoost)
   │     - Fuses Photo + Weather + Satellite + History into a single ML model
   │     - Spots lies, contradictions, or exaggerated claims
   │     - Outputs Claim Decision: APPROVED, REVIEW, or REJECTED
   ▼
Stage 5: Explainable AI (SHAP) & Interactive Web Dashboard
   │     - SHAP explains why the decision was made in plain English
   │     - Clean web screen with Leaflet map for drawing field boundaries
   ▼
Stage 6: Research Paper Results & Blockchain Evidence Provenance
         - Generates comparison tables and ablation study for the research paper
         - Adds Blockchain to tamper-proof claim evidence and hashes
```

---

## Stage 1: Crop Photo Damage Assessment API

- **Mentor Reference:** Section 4.1 (Visual Evidence)
- **Status:** COMPLETED & COMMITTED
- **What it does:** 
  The farmer submits a crop photo. The server runs our trained MobileNetV2 deep learning model to inspect the leaves, determine whether the crop is healthy or damaged, calculate the damage percentage, and save the claim in a SQLite database.
- **Inputs:**
  - Crop photo (from mobile camera)
  - Farmer ID, crop type (Rice, Wheat, Corn), and claimed damage %
- **Outputs:**
  - Visual Class: `HEALTHY` or `DAMAGED`
  - Damage Severity: `0% to 100%` (e.g. `68% damage`)
  - Confidence: `0.00 to 1.00`
- **Why it is needed:**
  Provides instant visual inspection instead of waiting weeks for a human surveyor to visit the field.

---

## Stage 2: Environmental & Historical Weather Verification

- **Mentor Reference:** Section 4.2 (Environmental Evidence)
- **Status:** COMPLETED & COMMITTED
- **What it does:**
  A photo alone can be faked. This stage connects to historical weather records (Rainfall, Temperature, Drought index) based on the farm location and loss date. It checks if the recorded weather actually matches the claimed disaster.
- **Inputs:**
  - Farm location (GPS coordinates)
  - Date of crop loss (`incidentDate`)
- **Outputs:**
  - Weather Score: `0.0% to 100.0%`
  - Weather Hazard: `FLOOD`, `DROUGHT`, `STORM_LODGING`, or `NORMAL`
  - Classified Damage Cause: e.g. `FLOOD` vs. `PLANT_DISEASE`
- **Why it is needed:**
  Prevents farmers from claiming flood loss during a dry period, or drought loss during heavy monsoons.

---

## Stage 3: Satellite Imagery & Field Vegetation Damage Assessment

- **Mentor Reference:** Section 4 (Multimodal AI) & Section 12 (Dataset Strategy)
- **Status:** COMPLETED & COMMITTED
- **What it does:**
  A mobile phone photo only shows 1 square meter of leaves. This stage integrates Sentinel-2 multispectral satellite observations over the farmer's field boundary polygon to calculate the Normalized Difference Vegetation Index (NDVI) before and after the disaster, measuring what percentage of the total field acreage suffered crop loss.
- **Inputs:**
  - Field boundary polygon (list of GPS coordinates)
  - Date of crop loss (`incidentDate`)
- **Outputs:**
  - Pre-Disaster NDVI (baseline health)
  - Post-Disaster NDVI (post-disaster health)
  - Vegetation Drop ($\Delta \text{NDVI}$)
  - Damaged Land Area Percentage (e.g. `64.2% of field area`)
- **Why it is needed:**
  Quantifies macro-level acreage loss across the entire field rather than relying solely on a close-up camera photo.

---

## Stage 4: Multimodal AI Fusion & Fraud Detection Engine (XGBoost)

- **Mentor Reference:** Section 4 (Multimodal AI) & Section 5 (Fraud & Anomaly Detection)
- **Status:** COMPLETED
- **What it does:** 
  This is the core multimodal fraud engine. It fuses all four evidence sources: visual leaf damage from Stage 1, weather score from Stage 2, satellite land damage from Stage 3, and agricultural field history. An XGBoost classifier evaluates cross-modal contradictions to compute a continuous fraud risk score, automated claim decision (APPROVED, MANUAL_REVIEW, REJECTED), and fair recommended payout percentage.
- **Inputs:**
  1. Farmer's claimed damage %
  2. AI's visual damage % (from Stage 1)
  3. Weather score & hazard match (from Stage 2)
  4. Satellite damaged area % (from Stage 3)
  5. Pre- vs. Post-disaster NDVI drop (from Stage 3)
  6. Discrepancy gap calculations (visual vs claim, satellite vs claim)
  7. Perceptual image hash check (dHash) for recycled photos
  8. Farmer claim frequency in the past 12 months
- **Outputs:**
  - Fraud Risk Score: `0.00 to 1.00`
  - Fraud Risk Level: `LOW_RISK`, `MEDIUM_RISK`, `HIGH_RISK`
  - Final Claim Decision:
    - `APPROVED` (Low Risk <= 0.35): Automatic payout
    - `MANUAL_REVIEW` (Medium Risk 0.36 - 0.70): Flagged for human adjuster check
    - `REJECTED` (High Risk > 0.70): Denied due to contradiction or fraud
  - Recommended Fair Payout % (verified physical ground truth)
  - Discrepancy Flags (e.g. `DAMAGE_EXAGGERATION_SUSPECTED`, `WEATHER_CONTRADICTION`, `DUPLICATE_IMAGE_DETECTED`)
- **Why it is needed:**
  Protects insurance companies from losing money to exaggerated or fraudulent claims while expediting prompt payouts to honest farmers.

---

## Stage 5: Explainable AI (SHAP) & Interactive Web Dashboard

- **Mentor Reference:** Section 6 (Explainable AI)
- **Status:** COMPLETED
- **What it does:**
  Insurance regulations require companies to explain *why* a claim was rejected or flagged. This stage uses SHAP (SHapley Additive exPlanations) to break down the risk score into plain-English cards. It also adds a clean web screen with an interactive Leaflet map where farmers can draw their field polygon and submit claims.
- **Inputs:**
  - The feature values and decision from Stage 4
- **Outputs:**
  - Clear explanations (e.g. *"Reported 85% flood damage, but weather recorded zero rainfall [+32% risk]"*)
  - User-friendly web dashboard (HTML, CSS, JavaScript, Leaflet)
- **Why it is needed:**
  Builds trust with farmers and fulfills legal transparency requirements for AI decisions.

---

## Stage 6: Research Paper Experiments & Blockchain Evidence Provenance

- **Mentor Reference:** Sections 7, 8, 13, 14, and 15
- **Status:** PLANNED (NEXT)
- **What it does:**
  Finalizes the academic contributions for the Scopus-indexed conference paper:
  1. Generates experimental evaluation tables comparing CNN vs. EfficientNet vs. XGBoost vs. Multimodal Model.
  2. Runs the 4-step Ablation Study (Image Only vs. Image+Weather vs. Image+Weather+Satellite vs. Full Multimodal).
  3. Integrates the Blockchain provenance layer to store image SHA-256 hashes, claim IDs, and decision timestamps in a tamper-proof ledger.
- **Outputs:**
  - Model Comparison Table (Accuracy, F1-Score, ROC-AUC)
  - Ablation Study Table
  - Tamper-proof blockchain transaction receipts for every claim
- **Why it is needed:**
  Guarantees evidence cannot be modified after submission and provides the exact scientific tables needed to get the research paper accepted.
