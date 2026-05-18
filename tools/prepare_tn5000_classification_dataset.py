from pathlib import Path
import os
import shutil
import xml.etree.ElementTree as ET


RAW_ROOT = Path(r"D:\AAAAAAA\bishe\datasets\raw\TN5000\TN5000_forReview")
OUT_ROOT = Path(r"D:\AAAAAAA\bishe\datasets\thyroid_tn5000")
LABEL_MAP = {
    "0": "benign",
    "1": "malignant",
}


def parse_label(xml_path: Path) -> str:
    tree = ET.parse(xml_path)
    names = {obj.findtext("name", default="").strip() for obj in tree.findall(".//object")}
    names.discard("")
    if len(names) != 1:
        raise ValueError(f"unexpected labels in {xml_path.name}: {sorted(names)}")
    raw = names.pop()
    if raw not in LABEL_MAP:
        raise ValueError(f"unknown label {raw!r} in {xml_path.name}")
    return LABEL_MAP[raw]


def read_split_ids(split_name: str):
    split_file = RAW_ROOT / "ImageSets" / "Main" / f"{split_name}.txt"
    return [line.strip() for line in split_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def link_or_copy(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def ensure_dirs():
    for split in ("train", "val", "test"):
        for label in ("benign", "malignant"):
            (OUT_ROOT / split / label).mkdir(parents=True, exist_ok=True)


def write_readme(stats: dict[tuple[str, str], int]):
    lines = [
        "TN5000 classification-ready dataset",
        "",
        "Source:",
        "  TN5000: An Ultrasound Image Dataset for Thyroid Nodule Detection and Classification",
        "  DOI: 10.6084/m9.figshare.28455641",
        "",
        "Preparation notes:",
        "  - Data were reorganized from VOC-style JPEGImages/Annotations into ImageFolder format.",
        "  - Label mapping used here: 0 -> benign, 1 -> malignant.",
        "  - train/val/test follow the official split files under ImageSets/Main.",
        "",
        "Counts:",
    ]
    for split in ("train", "val", "test"):
        for label in ("benign", "malignant"):
            lines.append(f"  {split}/{label}: {stats.get((split, label), 0)}")
    (OUT_ROOT / "README.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ensure_dirs()
    stats: dict[tuple[str, str], int] = {}

    for split in ("train", "val", "test"):
        ids = read_split_ids(split)
        for image_id in ids:
            xml_path = RAW_ROOT / "Annotations" / f"{image_id}.xml"
            image_path = RAW_ROOT / "JPEGImages" / f"{image_id}.jpg"
            label = parse_label(xml_path)
            dst = OUT_ROOT / split / label / image_path.name
            link_or_copy(image_path, dst)
            stats[(split, label)] = stats.get((split, label), 0) + 1

    write_readme(stats)
    print(OUT_ROOT)
    for split in ("train", "val", "test"):
        for label in ("benign", "malignant"):
            print(split, label, stats.get((split, label), 0))


if __name__ == "__main__":
    main()
