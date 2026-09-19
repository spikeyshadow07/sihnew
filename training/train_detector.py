"""Fine-tune a trusted local detector and save honest validation/test metrics."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

def summarize(metrics):
    return {"precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
            "mAP50": float(metrics.box.map50), "mAP50_95": float(metrics.box.map)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=Path("datasets/coco128_road_starter/data.yaml"))
    p.add_argument("--weights", type=Path, default=Path("models/yolo11n.pt"))
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--imgsz", type=int, default=416)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--device", default="cpu")
    p.add_argument("--project", type=Path, default=Path("training_runs"))
    p.add_argument("--name", default="starter")
    args = p.parse_args()
    if not args.data.is_file() or not args.weights.is_file():
        p.error("Prepare the dataset and download trusted model weights first. See TRAINING_GUIDE.md.")
    if args.epochs < 1:
        p.error("epochs must be positive")
    import torch
    from ultralytics import YOLO
    import ultralytics
    from ai_engine.detector import road_class_map
    torch.set_num_threads(4)
    root = args.project.resolve()/args.name
    if root.exists():
        p.error("Run name already exists; choose --name with a new value to preserve results")
    root.mkdir(parents=True)
    report = {"status": "running", "purpose": "Experimental object detection; NOT near-miss training",
              "parameters": {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
              "ultralytics_version": ultralytics.__version__, "torch_version": torch.__version__,
              "pretrained_sha256": hashlib.sha256(args.weights.read_bytes()).hexdigest(),
              "limitations": ["COCO128 overlaps the base model's COCO pretraining data.",
                "No independent traffic-domain or near-miss accuracy is established.",
                "Training does not replace camera calibration or event review."]}
    report_path = root/"report.json"
    report_path.write_text(json.dumps(report, indent=2))
    start = time.monotonic()
    try:
        model = YOLO(str(args.weights))
        classes = list(road_class_map(model.names))
        val_args = dict(data=str(args.data.resolve()), device=args.device, imgsz=args.imgsz,
                        batch=args.batch, workers=0, plots=False, classes=classes, verbose=False,
                        project=str(root))
        report["baseline_validation"] = summarize(model.val(split="val", name="baseline_val", **val_args))
        model.train(data=str(args.data.resolve()), epochs=args.epochs, imgsz=args.imgsz,
                    batch=args.batch, device=args.device, workers=0, seed=42, deterministic=True,
                    project=str(root), name="fit", freeze=10, optimizer="AdamW", lr0=.0001,
                    patience=5, cache=False, plots=False, amp=False, mosaic=0,
                    degrees=0, fliplr=.5, close_mosaic=0)
        best = Path(model.trainer.best)
        candidate = YOLO(str(best))
        report["candidate_validation"] = summarize(candidate.val(split="val", name="candidate_val", **val_args))
        # Test results are reported after fitting, never used for checkpoint selection.
        report["candidate_test"] = summarize(candidate.val(split="test", name="candidate_test", **val_args))
        report["baseline_test"] = summarize(YOLO(str(args.weights)).val(split="test", name="baseline_test", **val_args))
        report["validation_mAP50_95_change"] = report["candidate_validation"]["mAP50_95"]-report["baseline_validation"]["mAP50_95"]
        report["status"] = "completed"
        report["elapsed_seconds"] = round(time.monotonic()-start, 2)
        report["candidate_sha256"] = hashlib.sha256(best.read_bytes()).hexdigest()
        destination = root/"nearguard_starter.pt"
        shutil.copy2(best, destination)
        report["candidate_weights"] = str(destination)
        report["deployment"] = "Experimental checkpoint only. Existing default is unchanged. Use START_EXPERIMENTAL_AI_WINDOWS.bat to try it."
    except Exception as exc:
        report.update(status="failed", error=str(exc))
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
