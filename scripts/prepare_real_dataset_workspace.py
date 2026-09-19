from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "bdd100k": ["raw", "yolo_export"],
    "mot17": ["raw", "converted_tracks"],
    "cityflow": ["raw", "converted_tracks"],
    "dota": ["raw", "near_miss_labels"],
    "a3d": ["raw", "anomaly_labels"],
    "cadp": ["raw", "cctv_labels"],
}


def main():
    base = ROOT / "datasets" / "real"
    base.mkdir(parents=True, exist_ok=True)
    for name, children in DATASETS.items():
        dataset_dir = base / name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        for child in children:
            (dataset_dir / child).mkdir(parents=True, exist_ok=True)
        notes = dataset_dir / "notes.md"
        if not notes.exists():
            notes.write_text(
                f"# {name}\n\n"
                "Place authorized downloaded files in raw/.\n\n"
                "Record source URL, licence/access notes, split names, and conversion status here.\n",
                encoding="utf-8",
            )
    print(f"Real dataset workspace ready: {base}")
    print("Raw dataset files are not bundled. Download them from their official sources.")


if __name__ == "__main__":
    main()

