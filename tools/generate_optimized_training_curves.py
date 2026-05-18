import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METRICS = ROOT / "backend" / "models" / "thyroid_resnet50_tn5000_formal_20260507_024833_artifacts" / "metrics.csv"
DEFAULT_OUTPUT = Path(r"C:\Users\86136\Downloads\training_curves_optimized.png")


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


def load_history(metrics_path: Path):
    with metrics_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [
        {
            "epoch": int(row["epoch"]),
            "train_loss": float(row["train_loss"]),
            "val_loss": float(row["val_loss"]),
            "train_acc": float(row["train_acc"]),
            "val_acc": float(row["val_acc"]),
        }
        for row in rows
    ]


def draw_series_panel(draw, box, title, epochs, train_values, val_values, colors, fonts):
    left, top, right, bottom = box
    axis_left = left + 84
    axis_right = right - 24
    axis_top = top + 42
    axis_bottom = bottom - 54

    title_font, label_font, tick_font = fonts
    train_color, val_color = colors

    draw.rounded_rectangle(box, radius=18, fill="#f7fbff", outline="#8ca6c6", width=2)
    draw.text((left + 16, top + 10), title, fill="#1f3a5f", font=title_font)

    legend_y = top + 14
    draw.line((right - 170, legend_y + 10, right - 138, legend_y + 10), fill=train_color, width=4)
    draw.text((right - 128, legend_y), "train", fill="#334155", font=label_font)
    draw.line((right - 84, legend_y + 10, right - 52, legend_y + 10), fill=val_color, width=4)
    draw.text((right - 42, legend_y), "val", fill="#334155", font=label_font)

    draw.line((axis_left, axis_top, axis_left, axis_bottom), fill="#6b7c93", width=2)
    draw.line((axis_left, axis_bottom, axis_right, axis_bottom), fill="#6b7c93", width=2)

    all_values = train_values + val_values
    value_min = min(all_values)
    value_max = max(all_values)
    if abs(value_max - value_min) < 1e-8:
        value_max = value_min + 1.0

    y_tick_count = 5
    for i in range(y_tick_count):
        ratio = i / (y_tick_count - 1)
        y = axis_top + (axis_bottom - axis_top) * ratio
        value = value_max - (value_max - value_min) * ratio
        draw.line((axis_left, y, axis_right, y), fill="#d6e2ef", width=1)
        label = f"{value:.3f}" if value_max < 2 else f"{value:.2f}"
        bbox = draw.textbbox((0, 0), label, font=tick_font)
        draw.text((axis_left - 18 - (bbox[2] - bbox[0]), y - 8), label, fill="#4b5563", font=tick_font)

    epoch_min = min(epochs)
    epoch_max = max(epochs)

    def to_xy(epoch, value):
        if epoch_max == epoch_min:
            x = (axis_left + axis_right) / 2
        else:
            x = axis_left + (epoch - epoch_min) / (epoch_max - epoch_min) * (axis_right - axis_left)
        y = axis_bottom - (value - value_min) / (value_max - value_min) * (axis_bottom - axis_top)
        return x, y

    x_ticks = [1]
    step = 10 if epoch_max > 80 else 5
    current = step
    while current < epoch_max:
        x_ticks.append(current)
        current += step
    if x_ticks[-1] != epoch_max:
        x_ticks.append(epoch_max)

    for tick in x_ticks:
        x, _ = to_xy(tick, value_min)
        draw.line((x, axis_bottom, x, axis_bottom + 6), fill="#6b7c93", width=1)
        label = str(tick)
        bbox = draw.textbbox((0, 0), label, font=tick_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, axis_bottom + 10), label, fill="#4b5563", font=tick_font)

    epoch_label = "Epoch"
    bbox = draw.textbbox((0, 0), epoch_label, font=label_font)
    draw.text(((axis_left + axis_right - (bbox[2] - bbox[0])) / 2, bottom - 28), epoch_label, fill="#334155", font=label_font)

    def draw_series(values, color):
        points = [to_xy(epoch, value) for epoch, value in zip(epochs, values)]
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 2.4, y - 2.4, x + 2.4, y + 2.4), fill=color, outline=color)

    draw_series(train_values, train_color)
    draw_series(val_values, val_color)


def generate(metrics_path: Path, output_path: Path):
    history = load_history(metrics_path)
    epochs = [row["epoch"] for row in history]
    train_loss = [row["train_loss"] for row in history]
    val_loss = [row["val_loss"] for row in history]
    train_acc = [row["train_acc"] for row in history]
    val_acc = [row["val_acc"] for row in history]

    width, height = 1800, 1180
    image = Image.new("RGB", (width, height), "#eef4fa")
    draw = ImageDraw.Draw(image)

    title_font = get_font(24, bold=True)
    panel_title_font = get_font(20, bold=True)
    label_font = get_font(18, bold=False)
    tick_font = get_font(16, bold=False)

    draw.text((32, 20), "Training Curves", fill="#213b63", font=title_font)

    draw_series_panel(
        draw,
        (24, 70, width - 24, 560),
        "Loss",
        epochs,
        train_loss,
        val_loss,
        ("#3b82f6", "#f97316"),
        (panel_title_font, label_font, tick_font),
    )
    draw_series_panel(
        draw,
        (24, 600, width - 24, height - 24),
        "Accuracy",
        epochs,
        train_acc,
        val_acc,
        ("#10b981", "#8b5cf6"),
        (panel_title_font, label_font, tick_font),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


if __name__ == "__main__":
    output = generate(DEFAULT_METRICS, DEFAULT_OUTPUT)
    print(output)
