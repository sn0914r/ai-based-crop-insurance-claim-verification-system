# Satellite Imagery + Multimodal AI Integration

## 1. Updated System Flow

The satellite imagery component is added **before the Multimodal AI final assessment**.

```text
Farmer
  |
  |-- Claim details
  |-- Crop photos
  |-- Field boundary drawn on map
  v
+----------------------+
| Image Assessment     |
| Crop photos          |
+----------+-----------+
           |
           v
   Visual Assessment

+----------------------+
| Weather Assessment  |
| Location + weather  |
+----------+-----------+
           |
           v
   Weather Assessment

+----------------------+
| Satellite Analysis  |
| Field boundary +    |
| date + satellite    |
| imagery             |
+----------+-----------+
           |
           v
   Satellite Assessment
           |
           +-------------------+
           |                   |
           v                   v
       Image Assessment   Weather Assessment
           \                   /
            \                 /
             v               v
        +-------------------------+
        |      Multimodal AI      |
        | Image + Weather +       |
        | Satellite Evidence      |
        +------------+------------+
                     |
                     v
          Final Damage Assessment
                     |
                     v
          Fraud / Anomaly Detection
                     |
                     v
               Explainability
                     |
                     v
                 Blockchain
                     |
                     v
            Claim Decision Engine
```

## 2. What the Farmer Provides

The farmer does not need to provide technical satellite settings.

The farmer provides:

- Claim details
- Crop photos
- Field location
- Field boundary drawn on a map
- Other required agricultural/claim information

### Field Boundary

The farmer can open a map and draw the boundary around the field.

Example:

```text
        Field Boundary

        A -------- B
        |          |
        |  FIELD   |
        |          |
        D -------- C
```

The frontend converts the drawn boundary into polygon coordinates.

Example:

```text
[
  [13.601, 79.401],
  [13.603, 79.404],
  [13.600, 79.407],
  [13.598, 79.403]
]
```

These coordinates are sent to the backend.

A field boundary is better than only latitude and longitude because one latitude/longitude point does not describe the complete field.

For testing, fake polygon boundaries can be used.

## 3. Frontend Map

For a low-cost prototype:

- OpenStreetMap can provide the map data.
- Leaflet can display the map and allow the farmer to draw a polygon.

The important value sent to the backend is the field boundary polygon.

The farmer does **not** need to enter cloud filters.

## 4. Satellite Imagery Component

### Inputs

The Satellite Imagery Component receives:

1. Field boundary polygon / Area of Interest (AOI)
2. Incident date or suitable date range
3. Satellite data source
4. System-controlled cloud filtering criteria

The backend uses the field boundary to identify the exact area that should be analysed.

### Basic Pipeline

```text
Field Boundary
      |
      v
Backend
      |
      v
Satellite Data API
      |
      v
Suitable Satellite Image
      |
      v
Cloud Filtering
      |
      v
Satellite Analysis
```

## 5. Satellite Data Source

A suitable research-friendly option is **Sentinel-2** through the Copernicus ecosystem.

The system can request satellite imagery for the selected field and relevant date range.

The exact API/service can be selected during implementation.

## 6. What the Satellite Component Produces

The satellite component should produce **field-level evidence**, such as:

- Vegetation condition indicators
- NDVI or similar vegetation features
- Abnormal vegetation zones
- Image/date metadata
- Other relevant satellite-derived features

Example:

```text
Satellite Assessment

Vegetation condition: Abnormal in some areas
Vegetation anomaly: Detected
NDVI features: Available
Affected zones: Identified
Image date: [date]
```

### Important

The satellite component should not automatically say:

> "The field has exactly 50% crop damage."

Satellite imagery is evidence. The final damage percentage should be produced by the assessment model after considering multiple evidence sources.

## 7. Image Assessment

The farmer's crop photos are processed by the Image Model.

The Image Model can identify:

- Disease
- Visible crop damage
- Damage severity
- Affected-area indicators

Example:

```text
Image Assessment:
Visible crop damage detected
Estimated visible damage: 55%
```

The exact percentage must be based on the model and its validation.

## 8. Weather Assessment

The farmer's field location is used to obtain relevant weather information.

For example:

```text
Field Location
      |
      v
Weather Data
      |
      v
Recent Weather Analysis
      |
      v
Weather Assessment
```

The weather module can analyse conditions such as:

- Rainfall
- Temperature
- Drought conditions
- Flood/heavy-rain conditions
- Other relevant extreme weather

Example:

```text
Weather Assessment:
Heavy rainfall detected
Condition is consistent with possible crop damage
```

The exact time window should be defined by the project methodology rather than assuming one fixed period in every situation.

## 9. Multimodal AI

This is the important part of the updated design.

The Multimodal AI receives the **results/evidence** from:

### 1. Image Assessment

What the farmer's photos show.

### 2. Weather Assessment

Whether the environmental conditions support the claimed damage.

### 3. Satellite Assessment

What the whole-field satellite evidence indicates.

The Multimodal AI combines these sources.

```text
Image Assessment
       +
Weather Assessment
       +
Satellite Assessment
       |
       v
   Multimodal AI
       |
       v
Final Damage Assessment
```

## 10. Example

Suppose:

```text
Farmer's claimed damage: 60%

Image Assessment:
55% visible damage

Weather Assessment:
Heavy rainfall detected

Satellite Assessment:
Abnormal vegetation zones detected
```

The Multimodal AI can use all three pieces of evidence to produce a final assessment.

For example:

```text
Final Estimated Crop Damage:
50% of the field area
```

This is an **example output**, not a predetermined rule.

The model must be trained and experimentally validated before using such a percentage as a reliable insurance assessment.

## 11. Why Use Satellite + Farmer Photos?

They provide different types of evidence.

### Farmer Photos

Provide:

- Local visual details
- Visible crop damage
- Disease/damage appearance

### Satellite Imagery

Provides:

- Broader field-level information
- Vegetation condition
- Spatial anomaly information

Therefore:

```text
Farmer Photos = Local Visual Evidence

Satellite = Whole-Field Evidence

Weather = Environmental Evidence
```

Combining them makes the assessment stronger than relying on only one source.

## 12. Fraud / Anomaly Detection

After the Multimodal AI creates the final assessment, the result can be passed to the Fraud/Anomaly Detection Model.

The fraud model can compare:

- Farmer's reported damage
- Image assessment
- Weather assessment
- Satellite assessment
- Final multimodal assessment
- Historical information
- Other available claim evidence

Example:

```text
Claimed damage:              90%
Image assessment:            35%
Weather evidence:            Low support
Satellite evidence:          Mostly normal
Final multimodal assessment: 40%

             |
             v

      High claim risk
```

The fraud model is therefore checking whether the different pieces of evidence are consistent.

## 13. Important Limitation

Do not assume:

```text
Satellite image = exact crop damage percentage
```

Satellite observations can be affected by:

- Spatial resolution
- Cloud cover
- Image acquisition date
- Crop growth stage
- Soil conditions
- Harvesting
- Other environmental conditions

Therefore, satellite information should be combined with farmer photos, weather information, and other agricultural evidence.

## 14. Final Updated Architecture

```text
                     FARMER
                       |
                       v
              Claim + Crop Photos
                       |
                       v
              Field Boundary Map
                       |
          +------------+------------+
          |            |            |
          v            v            v
    Image Model   Weather Model  Satellite Model
          |            |            |
          v            v            v
    Image          Weather       Satellite
   Assessment      Assessment     Assessment
          \            |            /
           \           |           /
            +----------+----------+
                       |
                       v
                Multimodal AI
                       |
                       v
            Final Damage Assessment
                       |
                       v
            Fraud / Anomaly Model
                       |
                       v
                Explainability
                       |
                       v
                  Blockchain
                       |
                       v
              Claim Decision
               /      |      \
          Approve   Review   Reject
```

## 15. Key Design Decision

The cleanest architecture is:

> **Do not give raw satellite imagery directly to the final Multimodal AI unless a satellite-capable multimodal model is specifically designed and trained for it.**

Instead:

```text
Raw Satellite Image
        |
        v
Satellite Analysis
        |
        v
Satellite-derived Evidence
        |
        +-------------------+
                            |
                            v
                    Multimodal AI
```

This keeps the system modular and makes it easier to test each component separately.

## 16. Testing Strategy

Before using real farmer data:

1. Use fake field boundaries.
2. Send the polygon coordinates from the frontend to the backend.
3. Connect the satellite data service.
4. Retrieve imagery for the polygon.
5. Apply cloud filtering.
6. Generate satellite-derived features.
7. Combine them with test image and weather assessments.
8. Test the Multimodal AI output.
9. Test the fraud detection model.

This allows the complete pipeline to be tested step by step.
