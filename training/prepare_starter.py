"""Download COCO128 and create disjoint fine-tuning splits (NOT a traffic benchmark)."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
import urllib.request
import zipfile

URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/coco128.zip"
NAMES = ("person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,"
         "fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,"
         "elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,"
         "skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,"
         "tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,"
         "orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,"
         "dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,"
         "toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush").split(",")
ROAD_IDS = [0, 1, 2, 3, 5, 7]

def split_records(records, seed):
    """Rare-class-first multilabel coverage, then random fill to 90/19/19."""
    remaining = list(records)
    random.Random(seed).shuffle(remaining)
    splits = {"train": [], "val": [], "test": []}
    availability = Counter(c for row in remaining for c in set(row[2]) if c in ROAD_IDS)
    for c in sorted(ROAD_IDS, key=lambda item: availability[item]):
        for rows in splits.values():
            if any(c in row[2] for row in rows):
                continue
            candidates = [i for i,row in enumerate(remaining) if c in row[2]]
            if candidates:
                covered = {item for row in rows for item in row[2]}
                index = max(candidates, key=lambda i: sum(1/availability[item] for item in set(remaining[i][2])
                    if item in ROAD_IDS and item not in covered))
                rows.append(remaining.pop(index))
    for split, size in (("train",90),("val",19),("test",19)):
        needed = size-len(splits[split])
        splits[split].extend(remaining[:needed])
        remaining = remaining[needed:]
    return splits

def validate_label(text):
    ids = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 5:
            raise ValueError("Expected class, center x/y and width/height in every label row")
        c = int(fields[0])
        coords = list(map(float, fields[1:]))
        if c not in range(80) or not all(0 <= x <= 1 for x in coords) or min(coords[2:]) <= 0:
            raise ValueError("Invalid normalized YOLO bounding box")
        ids.append(c)
    return ids

def prepare(archive, output, seed=42):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Use a new output directory; refusing to mix splits: {output}")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                if not (root/member.filename).resolve().is_relative_to(root.resolve()):
                    raise ValueError("Unsafe ZIP member")
            z.extractall(root)
        source = root/"coco128"
        images = sorted((source/"images"/"train2017").glob("*.jpg"))
        if len(images) != 128:
            raise ValueError(f"Expected official 128-image archive, found {len(images)}")
        records, hashes = [], set()
        for image in images:
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            if digest in hashes:
                raise ValueError("Duplicate image bytes detected")
            hashes.add(digest)
            label = source/"labels"/"train2017"/(image.stem+".txt")
            # COCO128 omits a label file for a verified empty image.
            text = label.read_text() if label.exists() else ""
            ids = validate_label(text)
            records.append((image, text, ids, digest))
        partitions = split_records(records, seed)
        manifest = {"source": URL, "archive_sha256": hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
                    "seed": seed, "purpose": "Training-pipeline experiment only",
                    "warning": "COCO-pretrained weights may already have seen ALL these images. Splits are disjoint for fine-tuning only. No independent accuracy or near-miss claim.",
                    "splits": {}}
        for split, rows in partitions.items():
            imdir, labdir = output/"images"/split, output/"labels"/split
            imdir.mkdir(parents=True)
            labdir.mkdir(parents=True)
            counts = Counter()
            entries = []
            for image, text, ids, digest in rows:
                shutil.copy2(image, imdir/image.name)
                (labdir/(image.stem+".txt")).write_text(text)
                counts.update(ids)
                entries.append({"image": image.name, "sha256": digest})
            manifest["splits"][split] = {"image_count": len(rows), "images": entries,
                "road_user_box_counts": {NAMES[c]: counts[c] for c in ROAD_IDS}}
        # JSON values are also valid YAML values, including quoted Windows paths.
        (output/"data.yaml").write_text("path: "+json.dumps(output.as_posix())+
            "\ntrain: images/train\nval: images/val\ntest: images/test\nnames: "+json.dumps(NAMES)+"\n")
        (output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("datasets/coco128_road_starter"))
    args = parser.parse_args()
    archive = args.archive or Path("datasets/coco128.zip")
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(URL, headers={"User-Agent": "NearGuard-training/1.0"})
        partial = archive.with_suffix(".download")
        try:
            with urllib.request.urlopen(request, timeout=90) as response, partial.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    report = prepare(archive, args.output)
    print(json.dumps({s: v["road_user_box_counts"] for s,v in report["splits"].items()}, indent=2))
    print("Prepared:", args.output/"data.yaml")

if __name__ == "__main__":
    main()
