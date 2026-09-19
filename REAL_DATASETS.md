# Real Dataset Plan for NearGuard

NearGuard currently ships with small controlled demo videos so the full software workflow can be shown in a hackathon review. For real validation, use authorized public traffic datasets and keep their licences separate from this project ZIP.

## Why the raw datasets are not bundled

Most real traffic datasets are large, have their own licences, or require manual registration. Bundling them inside a hackathon ZIP can break dataset terms and make the project too large to share. This project therefore includes the dataset plan, source list, folder structure, and workspace script, while raw dataset files must be downloaded from the official source by the team.

## Recommended real datasets

| Dataset | Best use in NearGuard | Why it helps | Access note |
|---|---|---|---|
| BDD100K | Train or evaluate vehicle, person, bicycle, bus, truck detection | Large real driving dataset with city streets, highways, weather, and day/night variation | Manual download/registration from Berkeley DeepDrive |
| MOT17 | Test multi-object tracking stability | Provides pedestrian tracking sequences, frame rates, boxes, and IDs | Public archive download from MOTChallenge |
| CityFlow / AI City Challenge | Test vehicle tracking in multi-camera urban traffic | Traffic-camera-style vehicle videos and city-scale tracking research | Use official AI City Challenge data instructions |
| DoTA | Study traffic anomaly labels | Contains traffic anomaly videos with temporal and object-level annotation for anomaly research | Official GitHub/research dataset |
| A3D | Dashcam accident/anomaly validation reference | Useful for anomaly-detection comparison and literature support | Provided through the research GitHub workflow |
| CADP | CCTV traffic-camera accident forecasting reference | CCTV-style accident/forecasting dataset, closer to road authority use cases than dashcam-only data | Dataset release instructions from project page |

## How each dataset fits the pipeline

NearGuard has three different data needs:

1. Object detection data
   - Use BDD100K.
   - Goal: improve YOLO detection for cars, buses, trucks, people, bicycles, and motorcycles.

2. Tracking data
   - Use MOT17 and CityFlow.
   - Goal: check whether object IDs remain stable across frames.

3. Near-miss/anomaly validation data
   - Use DoTA, A3D, and CADP.
   - Goal: compare NearGuard's candidate events with known risky or abnormal moments.

## Suggested local folder structure

After downloading datasets, keep them outside the submitted ZIP:

```text
datasets/
  real/
    bdd100k/
      raw/
      yolo_export/
      notes.md
    mot17/
      raw/
      converted_tracks/
      notes.md
    cityflow/
      raw/
      converted_tracks/
      notes.md
    dota/
      raw/
      near_miss_labels/
      notes.md
    a3d/
      raw/
      anomaly_labels/
      notes.md
    cadp/
      raw/
      cctv_labels/
      notes.md
```

Run this command to create the folders:

```sh
python scripts/prepare_real_dataset_workspace.py
```

## What to say to the jury

"For the hackathon prototype, we use controlled demo footage to prove the full software workflow end to end. For real-world validation, we have mapped the project to real public datasets: BDD100K for road-user detection, MOT17 and CityFlow for tracking, and DoTA/A3D/CADP for anomaly or accident-style validation. We do not claim full real-world accuracy yet; the next step is to download these datasets legally, convert labels into our format, and evaluate detection, tracking, and near-miss ranking separately."

## Important honesty point

A normal road video is input footage. It is not automatically a training dataset. To become a training dataset, it needs labels such as bounding boxes, object IDs, and reviewed near-miss time intervals.

