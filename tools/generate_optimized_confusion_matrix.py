import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = (
    ROOT
    / "backend"
    / "models"
    / "thyroid_resnet50_tn5000_formal_20260507_024833_artifacts"
    / "best_val_report.json"
)
DEFAULT_OUTPUT = Path(r"C:\Users\86136\Downloads\validation_confusion_matrix_best_optimized.png")
DEFAULT_TEST_REPORT = (
    ROOT
    / "backend"
    / "models"
    / "thyroid_resnet50_tn5000_formal_20260507_024833_artifacts"
    / "test_report.json"
)
DEFAULT_TEST_OUTPUT = Path(r"C:\Users\86136\Downloads\test_confusion_matrix_optimized.png")


def get_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates.extend(
            [
                r"C:\Windows\Fonts\msyhbd.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
            ]
        )
    candidates.extend(
        [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ]
    )
    for font_path in candidates:
        path = Path(font_path)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def build_matrix_image(report_path: Path, output_path: Path, title: str):
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    confusion = metrics["confusion_matrix"]
    total = sum(sum(row) for row in confusion)
    class_names = ["benign", "malignant"]

    width, height = 980, 760
    image = Image.new("RGB", (width, height), "#eef4fa")
    draw = ImageDraw.Draw(image)

    title_font = get_font(26, bold=True)
    label_font = get_font(21, bold=True)
    value_font = get_font(32, bold=True)
    pct_font = get_font(22, bold=False)

    title_box = draw.textbbox((0, 0), title, font=title_font)
    title_w = title_box[2] - title_box[0]
    draw.text(((width - title_w) / 2, 28), title, fill="#163457", font=title_font)

    matrix_left = 260
    matrix_top = 140
    cell = 210
    gap = 18
    max_value = max(max(row) for row in confusion)

    pred_y = matrix_top - 46
    for col, class_name in enumerate(class_names):
        x = matrix_left + col * (cell + gap) + cell / 2
        text = f"Pred {class_name}"
        box = draw.textbbox((0, 0), text, font=label_font)
        draw.text((x - (box[2] - box[0]) / 2, pred_y), text, fill="#29476b", font=label_font)

    for row, class_name in enumerate(class_names):
        y = matrix_top + row * (cell + gap) + cell / 2
        text = f"True {class_name}"
        box = draw.textbbox((0, 0), text, font=label_font)
        draw.text((92, y - (box[3] - box[1]) / 2), text, fill="#29476b", font=label_font)

    for row in range(2):
        for col in range(2):
            value = confusion[row][col]
            ratio = value / max(max_value, 1)
            if row == col:
                fill = (
                    int(210 - 34 * ratio),
                    int(243 - 34 * ratio),
                    int(248 - 16 * ratio),
                )
            else:
                fill = (
                    int(245 - 10 * ratio),
                    int(246 - 8 * ratio),
                    int(248 - 8 * ratio),
                )

            x1 = matrix_left + col * (cell + gap)
            y1 = matrix_top + row * (cell + gap)
            x2 = x1 + cell
            y2 = y1 + cell
            draw.rounded_rectangle(
                (x1, y1, x2, y2),
                radius=18,
                fill=fill,
                outline="#7d9dc3",
                width=2,
            )

            pct = value / total * 100 if total else 0.0
            value_text = str(value)
            pct_text = f"{pct:.1f}%"

            value_box = draw.textbbox((0, 0), value_text, font=value_font)
            pct_box = draw.textbbox((0, 0), pct_text, font=pct_font)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            draw.text(
                (cx - (value_box[2] - value_box[0]) / 2, cy - 34),
                value_text,
                fill="#1a2d42",
                font=value_font,
            )
            draw.text(
                (cx - (pct_box[2] - pct_box[0]) / 2, cy + 12),
                pct_text,
                fill="#2f445b",
                font=pct_font,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


if __name__ == "__main__":
    val_path = build_matrix_image(DEFAULT_REPORT, DEFAULT_OUTPUT, "Validation Confusion Matrix (Best)")
    print(val_path)
    test_path = build_matrix_image(DEFAULT_TEST_REPORT, DEFAULT_TEST_OUTPUT, "Test Confusion Matrix")
    print(test_path)
