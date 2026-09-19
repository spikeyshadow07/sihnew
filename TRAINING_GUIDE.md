# NearGuard: what was actually trained

Team BITHAWK · 2026-09-16

A five-epoch YOLO11n fine-tuning experiment was completed on CPU. This trains an **object detector**, not a near-miss classifier. NearGuard continues to derive conflict candidates from tracked positions and explicit camera calibration.

## Dataset and scope

We downloaded the official Ultralytics COCO128 archive: 128 real images with existing human-labelled object boxes. Source: https://docs.ultralytics.com/datasets/detect/coco128/ and https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip . COCO source and terms: https://cocodataset.org/ . Original archive notices are included under training_results/.

The script creates **90 training / 19 validation / 19 test images**, with no identical image shared between these fine-tuning splits. Rare road-user classes are allocated first, then the remaining images are shuffled with seed 42. The source archive's default train=validation configuration is not used. The exact image IDs, SHA-256 hashes and box counts are in training_results/dataset_manifest.json. Retaining the 80 original classes preserves the checkpoint's label vocabulary; NearGuard filters inference to person, bicycle, car, motorcycle, bus and truck.

| Road-user boxes | Training | Validation | Test |
|---|---:|---:|---:|
| Person | 212 | 17 | 25 |
| Bicycle | 2 | 3 | 1 |
| Car | 27 | 13 | 6 |
| Motorcycle | 1 | 1 | 3 |
| Bus | 4 | 2 | 1 |
| Truck | 8 | 3 | 1 |

These tiny counts, especially one motorcycle training example, are inadequate for robust traffic learning. COCO128 is a training-pipeline starter, **not a CCTV traffic or near-miss dataset**. The pretrained COCO model can already have seen all of these images. Even the separate fine-tuning test split therefore does **not** establish independent generalization.

## Measured result

Training used image size 416, batch 4, five epochs, AdamW at 0.0001, seed 42 and the first ten model modules frozen. CPU training plus the four evaluations took 54.62 seconds here; your laptop timing will differ. Ultralytics 8.4.154 and PyTorch 2.14.0+cu130 were installed; the run explicitly used CPU, not CUDA.

| Object-detection check | Original pretrained | Experimental fine-tune |
|---|---:|---:|
| Validation mAP50–95 | 0.2834 | 0.2561 |
| Test mAP50–95 | 0.7379 | 0.5640 |

mAP measures bounding-box detection across confidence and overlap thresholds; it is not near-miss accuracy. These results are small-data diagnostics only. The experimental model performed worse, so the normal app launcher keeps the original YOLO11n as its YOLO option. We do not claim an improvement. Checkpoint selection during training used validation; test data was evaluated only after fitting.

Included checkpoints:
- models/yolo11n.pt: original official pretrained model.
- models/nearguard_starter.pt: actual experimental fine-tune from this run.

The original report and per-epoch loss/metric CSV are included under training_results/. Paths in report.json record the original training machine; use the commands below on your computer.

## Use the models in the app

1. Extract the release into a new folder; stop the older running server.
2. Run INSTALL_WINDOWS.bat, then INSTALL_AI_WINDOWS.bat. Internet is needed for Python packages.
3. Run START_WINDOWS.bat and select **YOLO — yolo11n.pt** in Video studio for the original model.
4. To try the experiment, stop the server and run START_EXPERIMENTAL_AI_WINDOWS.bat instead. Select **YOLO — nearguard_starter.pt**. The filename also appears on the job.
5. Upload a short, authorized, fixed-camera real video. Without measured calibration, use tracking-only mode. The drawing-style bundled demos intentionally use motion mode.

The model recognises road-user categories; it does not learn physical distances from these images. Camera calibration remains necessary for metric risk screening. Review all candidate events manually.

## Reproduce training

Double-click TRAIN_STARTER_WINDOWS.bat after installing AI dependencies. It downloads and prepares the actual dataset automatically, then trains a new run. Dataset images are not bundled in the project ZIP; the reproducible downloader, source information and exact split manifest are included.

Manual commands from the project folder with the virtual environment active:

```sh
python -m training.prepare_starter
python -m training.train_detector --name starter_local --epochs 5 --device cpu
```

The scripts refuse to overwrite existing prepared data or training runs. To run another experiment, use a new `--output` for preparation or a new `--name` for training. The new weights are training_runs/starter_local/nearguard_starter.pt; they do not automatically overwrite the models in use. To try a new checkpoint, set NEARGUARD_MODEL_PATH to its absolute path before starting the app.

## What is still required for traffic-specific training

Obtain authorized, annotated fixed-camera road sequences representative of the target city, camera angle, day/night lighting and occlusion. Label people and vehicles; label actual near-miss time intervals separately with reviewer agreement. A downloaded stock video without labels is input footage, not supervised training data.

Keep whole camera recordings together in one split; preferably reserve unseen cameras and dates for the final test. Do not randomly mix adjacent frames from the same video into training and test. Include ordinary traffic and difficult negative examples as well as conflicts.

For a labelled YOLO-format dataset, provide a data.yaml with train/val/test directories and class names. The training script accepts it using --data. The app reads class names from model metadata, so class-number changes do not silently turn a truck into a person. Adapt model initialization and training settings for the actual dataset and GPU budget; the default starter settings are not a tuned traffic training recipe.

Evaluate object-detection precision/recall by class, track identity stability, and reviewed event-level precision/recall separately. Measure night/rain/occlusion failures and calibration error. Do not present these starter scores as road-safety validation.

## Accurate statement for the jury

“We integrated a pretrained YOLO detector and completed a five-epoch fine-tuning experiment using COCO128. We saved reproducible splits and compared both models. The small fine-tune performed worse, so we retained the original model as the normal option. Near-miss candidates come from calibrated trajectories and human review; real traffic-specific validation is still pending.”

## Sources and notices

- COCO128: https://docs.ultralytics.com/datasets/detect/coco128/
- Original model release: https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
- Training API: https://docs.ultralytics.com/modes/train/
- Ultralytics licensing: https://www.ultralytics.com/license ; the package's supplied license is in models/ULTRALYTICS_LICENSE.txt. Consult those terms when distributing the model/app. The dataset's original notices are retained separately.
