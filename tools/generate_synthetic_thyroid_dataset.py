from pathlib import Path
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


ROOT = Path(r"D:\AAAAAAA\bishe\datasets\thyroid_synthetic")
SPLITS = {"train": 80, "val": 20}
IMAGE_SIZE = 512
SEED = 20260322


def build_background(rng: random.Random) -> Image.Image:
    canvas = Image.new("L", (IMAGE_SIZE, IMAGE_SIZE), color=rng.randint(95, 135))

    # Low-frequency illumination variation
    draw = ImageDraw.Draw(canvas)
    for y in range(0, IMAGE_SIZE, 16):
        tone = max(0, min(255, 118 + rng.randint(-18, 18) + y // 48))
        draw.rectangle([(0, y), (IMAGE_SIZE, min(IMAGE_SIZE, y + 16))], fill=tone)

    # Ultrasound-like speckle
    noise = Image.effect_noise((IMAGE_SIZE, IMAGE_SIZE), rng.uniform(12.0, 22.0))
    noise = noise.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.4, 0.8)))
    canvas = Image.blend(canvas, noise, alpha=rng.uniform(0.18, 0.28))

    # Slight vignette
    vignette = Image.new("L", (IMAGE_SIZE, IMAGE_SIZE), color=255)
    vdraw = ImageDraw.Draw(vignette)
    margin = rng.randint(36, 60)
    vdraw.ellipse((margin, margin, IMAGE_SIZE - margin, IMAGE_SIZE - margin), fill=210)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=46))
    canvas = ImageChops.multiply(canvas, vignette)
    return canvas


def ellipse_points(cx, cy, rx, ry, count=80):
    points = []
    for i in range(count):
        theta = 2 * math.pi * i / count
        x = cx + rx * math.cos(theta)
        y = cy + ry * math.sin(theta)
        points.append((x, y))
    return points


def jitter_points(points, rng: random.Random, jitter: float):
    jittered = []
    for x, y in points:
        jittered.append((x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter)))
    return jittered


def add_speckles(img: Image.Image, rng: random.Random, count: int, bright=True):
    draw = ImageDraw.Draw(img)
    for _ in range(count):
        x = rng.randint(0, IMAGE_SIZE - 1)
        y = rng.randint(0, IMAGE_SIZE - 1)
        radius = rng.randint(1, 3)
        tone = rng.randint(190, 245) if bright else rng.randint(15, 70)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=tone)


def generate_benign(rng: random.Random) -> Image.Image:
    img = build_background(rng)
    cx = rng.randint(190, 320)
    cy = rng.randint(190, 320)
    rx = rng.randint(68, 112)
    ry = rng.randint(50, 92)

    base = Image.new("L", img.size, color=0)
    draw = ImageDraw.Draw(base)
    draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=rng.randint(72, 102))

    # Simulate clearer margin / halo
    halo = Image.new("L", img.size, color=0)
    hdraw = ImageDraw.Draw(halo)
    hdraw.ellipse((cx - rx - 10, cy - ry - 10, cx + rx + 10, cy + ry + 10), fill=165)
    hdraw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=0)
    halo = halo.filter(ImageFilter.GaussianBlur(radius=4))

    lesion = base.filter(ImageFilter.GaussianBlur(radius=2.8))
    img = Image.composite(lesion, img, lesion)
    img = Image.blend(img, halo, alpha=0.14)

    # Mild homogeneous internal texture
    texture = Image.effect_noise(img.size, rng.uniform(6.0, 10.0)).filter(ImageFilter.GaussianBlur(radius=1.2))
    img = Image.blend(img, texture, alpha=0.08)

    add_speckles(img, rng, count=rng.randint(30, 55), bright=False)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))
    return ImageOps.autocontrast(img).convert("RGB")


def generate_malignant(rng: random.Random) -> Image.Image:
    img = build_background(rng)
    cx = rng.randint(190, 320)
    cy = rng.randint(185, 325)
    rx = rng.randint(60, 110)
    ry = rng.randint(55, 95)

    points = ellipse_points(cx, cy, rx, ry, count=64)
    points = jitter_points(points, rng, jitter=rng.uniform(8.0, 20.0))

    mask = Image.new("L", img.size, color=0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.polygon(points, fill=rng.randint(58, 95))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.3))

    img = Image.composite(mask, img, mask)

    # Heterogeneous texture inside lesion
    hetero = Image.effect_noise(img.size, rng.uniform(14.0, 24.0)).filter(ImageFilter.GaussianBlur(radius=0.6))
    img = Image.blend(img, hetero, alpha=0.16)

    # Bright microcalcification-like spots
    lesion_draw = ImageDraw.Draw(img)
    for _ in range(rng.randint(8, 18)):
        x = int(cx + rng.uniform(-rx * 0.7, rx * 0.7))
        y = int(cy + rng.uniform(-ry * 0.7, ry * 0.7))
        r = rng.randint(1, 3)
        lesion_draw.ellipse((x - r, y - r, x + r, y + r), fill=rng.randint(220, 255))

    # Slight posterior shadowing and irregular edge enhancement
    shadow = Image.new("L", img.size, color=0)
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rectangle((cx - rx // 2, cy + ry, cx + rx // 2, min(IMAGE_SIZE, cy + ry + 90)), fill=55)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=16))
    img = Image.blend(img, shadow, alpha=0.12)

    add_speckles(img, rng, count=rng.randint(40, 75), bright=True)
    add_speckles(img, rng, count=rng.randint(35, 60), bright=False)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    return ImageOps.autocontrast(img).convert("RGB")


def ensure_structure():
    for split in SPLITS:
        for label in ("benign", "malignant"):
            (ROOT / split / label).mkdir(parents=True, exist_ok=True)


def clear_old_files():
    if not ROOT.exists():
        return
    for path in ROOT.rglob("*.jpg"):
        path.unlink()


def write_readme():
    text = (
        "这是自动生成的合成甲状腺超声风格二分类数据集，用于验证训练脚本、目录结构和推理流程。\n"
        "其中 benign 与 malignant 标签由生成规则定义，并非真实医学标注，因此不能用于论文实验结论或临床相关性能评估。\n"
        "目录结构符合 backend/scripts/train.py 的 ImageFolder 读取要求。\n"
    )
    (ROOT / "README.txt").write_text(text, encoding="utf-8")


def main():
    rng = random.Random(SEED)
    clear_old_files()
    ensure_structure()
    write_readme()

    generators = {
        "benign": generate_benign,
        "malignant": generate_malignant,
    }

    for split, count in SPLITS.items():
        for label, generator in generators.items():
            for idx in range(count):
                img = generator(random.Random(rng.randint(0, 10**9)))
                path = ROOT / split / label / f"{label}_{idx + 1:03d}.jpg"
                img.save(path, quality=95)

    print(ROOT)


if __name__ == "__main__":
    main()
