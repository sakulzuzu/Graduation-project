import argparse
import csv
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BASE_DIR)
sys.path.append(BASE_DIR)

import torch
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

from ml.utils import build_transform


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if torch.backends.cudnn.is_available():
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def resolve_device(device_name: str, require_cuda: bool) -> torch.device:
    requested = (device_name or "").strip().lower()
    if not requested:
        requested = "cuda" if torch.cuda.is_available() else "cpu"

    if requested.startswith("cuda"):
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was requested for training, but torch.cuda.is_available() is False. "
                "Please check the NVIDIA driver, CUDA-enabled PyTorch build, and GPU environment."
            )
        return torch.device(requested)

    if require_cuda:
        raise RuntimeError("This training script is configured to require CUDA. Please set --device cuda.")

    return torch.device(requested)


def build_train_transform(image_size: int = 224):
    return transforms.Compose(
        [
            transforms.Resize((image_size + 32, image_size + 32)),
            transforms.RandomResizedCrop(image_size, scale=(0.85, 1.0), ratio=(0.92, 1.08)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=8),
            transforms.RandomAffine(degrees=0, translate=(0.03, 0.03), scale=(0.95, 1.05)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


class ThyroidBinaryDataset(Dataset):
    def __init__(self, root: Path, class_names: list[str], transform=None):
        self.root = root
        self.class_names = class_names
        self.transform = transform
        self.class_to_idx = {name: idx for idx, name in enumerate(class_names)}
        self.samples: list[tuple[Path, int]] = []

        if not root.exists():
            raise FileNotFoundError(f"dataset split directory not found: {root}")

        for class_name in class_names:
            class_dir = root / class_name
            if not class_dir.exists():
                raise FileNotFoundError(f"class directory not found: {class_dir}")

            for file_path in sorted(class_dir.rglob("*")):
                if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.samples.append((file_path, self.class_to_idx[class_name]))

        if not self.samples:
            raise RuntimeError(f"no image files found under: {root}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        image_path, label = self.samples[index]
        image = Image.open(image_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, label


@dataclass
class ArtifactPaths:
    dir: Path
    metrics_csv: Path
    summary_txt: Path
    summary_json: Path
    curves_png: Path
    cm_last_png: Path
    cm_best_png: Path
    cm_test_png: Path
    report_best_json: Path
    report_test_json: Path


def ensure_artifact_paths(output_path: Path) -> ArtifactPaths:
    artifact_dir = output_path.parent / f"{output_path.stem}_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return ArtifactPaths(
        dir=artifact_dir,
        metrics_csv=artifact_dir / "metrics.csv",
        summary_txt=artifact_dir / "summary.txt",
        summary_json=artifact_dir / "summary.json",
        curves_png=artifact_dir / "training_curves.png",
        cm_last_png=artifact_dir / "confusion_matrix_last.png",
        cm_best_png=artifact_dir / "confusion_matrix_best.png",
        cm_test_png=artifact_dir / "confusion_matrix_test.png",
        report_best_json=artifact_dir / "best_val_report.json",
        report_test_json=artifact_dir / "test_report.json",
    )


def compute_class_weights(dataset: ThyroidBinaryDataset, num_classes: int) -> torch.Tensor:
    counts = torch.zeros(num_classes, dtype=torch.float32)
    for _, label in dataset.samples:
        counts[label] += 1
    weights = counts.sum() / torch.clamp(counts, min=1.0)
    weights = weights / weights.mean()
    return weights


def confusion_to_metrics(confusion: torch.Tensor, class_names: list[str]) -> dict:
    total = confusion.sum().item()
    correct = confusion.diag().sum().item()
    accuracy = correct / total if total else 0.0

    class_metrics = {}
    macro_precision = 0.0
    macro_recall = 0.0
    macro_f1 = 0.0
    weighted_f1 = 0.0

    for idx, class_name in enumerate(class_names):
        tp = confusion[idx, idx].item()
        fp = confusion[:, idx].sum().item() - tp
        fn = confusion[idx, :].sum().item() - tp
        support = confusion[idx, :].sum().item()

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        class_metrics[class_name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(support),
        }
        macro_precision += precision
        macro_recall += recall
        macro_f1 += f1
        weighted_f1 += f1 * support

    num_classes = len(class_names)
    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision / num_classes if num_classes else 0.0,
        "macro_recall": macro_recall / num_classes if num_classes else 0.0,
        "macro_f1": macro_f1 / num_classes if num_classes else 0.0,
        "weighted_f1": weighted_f1 / total if total else 0.0,
        "class_metrics": class_metrics,
        "confusion_matrix": confusion.tolist(),
    }


def evaluate(model, loader, criterion, device, class_names: list[str]):
    model.eval()
    num_classes = len(class_names)
    total_loss = 0.0
    total = 0
    correct = 0
    confusion = torch.zeros((num_classes, num_classes), dtype=torch.int64)

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            preds = outputs.argmax(dim=1)

            total_loss += loss.item() * images.size(0)
            total += labels.size(0)
            correct += (preds == labels).sum().item()

            for true_label, pred_label in zip(labels.view(-1), preds.view(-1)):
                confusion[true_label.long(), pred_label.long()] += 1

    avg_loss = total_loss / max(total, 1)
    avg_acc = correct / max(total, 1)
    metrics = confusion_to_metrics(confusion, class_names)
    return avg_loss, avg_acc, confusion, metrics


def save_metrics_csv(history: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "epoch",
                "train_loss",
                "train_acc",
                "val_loss",
                "val_acc",
                "val_macro_precision",
                "val_macro_recall",
                "val_macro_f1",
                "val_weighted_f1",
                "epoch_seconds",
            ],
        )
        writer.writeheader()
        writer.writerows(history)


def draw_curve_panel(draw, box, title, train_values, val_values, train_color, val_color):
    left, top, right, bottom = box
    padding_left = 60
    padding_right = 20
    padding_top = 35
    padding_bottom = 45
    chart_left = left + padding_left
    chart_top = top + padding_top
    chart_right = right - padding_right
    chart_bottom = bottom - padding_bottom

    font = ImageFont.load_default()
    draw.rounded_rectangle(box, radius=16, outline="#8ea7c4", width=2, fill="#f8fbff")
    draw.text((left + 16, top + 10), title, fill="#1f3a5f", font=font)
    draw.line((chart_left, chart_top, chart_left, chart_bottom), fill="#7a8796", width=2)
    draw.line((chart_left, chart_bottom, chart_right, chart_bottom), fill="#7a8796", width=2)

    all_values = train_values + val_values
    vmin = min(all_values) if all_values else 0.0
    vmax = max(all_values) if all_values else 1.0
    if abs(vmax - vmin) < 1e-8:
        vmax = vmin + 1.0

    def to_xy(index, value, total_points):
        if total_points == 1:
            x = (chart_left + chart_right) / 2
        else:
            x = chart_left + (chart_right - chart_left) * index / (total_points - 1)
        y = chart_bottom - (value - vmin) / (vmax - vmin) * (chart_bottom - chart_top)
        return x, y

    for i in range(5):
        y = chart_top + (chart_bottom - chart_top) * i / 4
        value = vmax - (vmax - vmin) * i / 4
        draw.line((chart_left, y, chart_right, y), fill="#dde6f0", width=1)
        draw.text((left + 8, y - 6), f"{value:.3f}", fill="#5b6672", font=font)

    total_points = max(len(train_values), len(val_values), 1)
    for i in range(total_points):
        x = (chart_left + chart_right) / 2 if total_points == 1 else chart_left + (chart_right - chart_left) * i / (total_points - 1)
        draw.line((x, chart_bottom, x, chart_bottom + 5), fill="#7a8796", width=1)
        draw.text((x - 6, chart_bottom + 10), str(i + 1), fill="#5b6672", font=font)

    def draw_series(values, color):
        if not values:
            return
        points = [to_xy(i, v, len(values)) for i, v in enumerate(values)]
        if len(points) >= 2:
            draw.line(points, fill=color, width=3)
        for x, y in points:
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color, outline=color)

    draw_series(train_values, train_color)
    draw_series(val_values, val_color)

    legend_y = top + 10
    draw.line((right - 150, legend_y + 8, right - 125, legend_y + 8), fill=train_color, width=3)
    draw.text((right - 118, legend_y + 1), "train", fill="#334155", font=font)
    draw.line((right - 80, legend_y + 8, right - 55, legend_y + 8), fill=val_color, width=3)
    draw.text((right - 48, legend_y + 1), "val", fill="#334155", font=font)


def save_training_curves(history: list[dict], path: Path) -> None:
    width, height = 1200, 760
    image = Image.new("RGB", (width, height), "#eef3f8")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.text((24, 18), "Training Curves", fill="#1f3a5f", font=font)
    train_loss = [row["train_loss"] for row in history]
    val_loss = [row["val_loss"] for row in history]
    train_acc = [row["train_acc"] for row in history]
    val_acc = [row["val_acc"] for row in history]

    draw_curve_panel(draw, (24, 54, 1176, 360), "Loss", train_loss, val_loss, "#2f6fed", "#ef6c39")
    draw_curve_panel(draw, (24, 392, 1176, 698), "Accuracy", train_acc, val_acc, "#10a37f", "#8b5cf6")
    image.save(path)


def save_confusion_matrix(confusion: torch.Tensor, class_names: list[str], path: Path, title: str) -> None:
    size = 700
    image = Image.new("RGB", (size, size), "#f5f8fc")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.text((24, 18), title, fill="#1f3a5f", font=font)

    matrix_left = 170
    matrix_top = 120
    cell = 180
    max_value = max(int(confusion.max().item()) if confusion.numel() else 1, 1)

    for i, name in enumerate(class_names):
        draw.text((matrix_left + i * cell + 55, 80), f"Pred {name}", fill="#334155", font=font)
        draw.text((32, matrix_top + i * cell + 75), f"True {name}", fill="#334155", font=font)

    total = int(confusion.sum().item()) if confusion.numel() else 0
    for row in range(confusion.shape[0]):
        for col in range(confusion.shape[1]):
            value = int(confusion[row, col].item())
            intensity = int(235 - 140 * (value / max_value))
            fill = (225, intensity, intensity) if row != col else (intensity, 228, 240)
            x1 = matrix_left + col * cell
            y1 = matrix_top + row * cell
            x2 = x1 + cell - 8
            y2 = y1 + cell - 8
            draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=fill, outline="#8ea7c4", width=2)
            pct = (value / total * 100) if total else 0.0
            draw.text((x1 + 68, y1 + 72), str(value), fill="#1f2937", font=font)
            draw.text((x1 + 56, y1 + 100), f"{pct:.1f}%", fill="#475569", font=font)

    image.save(path)


def save_json_report(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(
    args,
    class_names: list[str],
    train_dataset: ThyroidBinaryDataset,
    val_dataset: ThyroidBinaryDataset,
    test_dataset: ThyroidBinaryDataset | None,
    best_epoch: int,
    best_val_metrics: dict,
    test_metrics: dict | None,
    artifacts: ArtifactPaths,
) -> None:
    lines = [
        f"data_dir={args.data_dir}",
        f"output={args.output}",
        f"device={args.device}",
        f"epochs={args.epochs}",
        f"batch_size={args.batch_size}",
        f"lr={args.lr}",
        f"weight_decay={args.weight_decay}",
        f"num_workers={args.num_workers}",
        f"class_names={class_names}",
        f"train_samples={len(train_dataset)}",
        f"val_samples={len(val_dataset)}",
        f"test_samples={len(test_dataset) if test_dataset else 0}",
        f"best_epoch={best_epoch}",
        f"best_val_acc={best_val_metrics['accuracy']:.4f}",
        f"best_val_macro_precision={best_val_metrics['macro_precision']:.4f}",
        f"best_val_macro_recall={best_val_metrics['macro_recall']:.4f}",
        f"best_val_macro_f1={best_val_metrics['macro_f1']:.4f}",
        f"best_val_weighted_f1={best_val_metrics['weighted_f1']:.4f}",
        f"metrics_csv={artifacts.metrics_csv}",
        f"curves_png={artifacts.curves_png}",
        f"confusion_matrix_last={artifacts.cm_last_png}",
        f"confusion_matrix_best={artifacts.cm_best_png}",
    ]
    if test_metrics is not None:
        lines.extend(
            [
                f"test_acc={test_metrics['accuracy']:.4f}",
                f"test_macro_precision={test_metrics['macro_precision']:.4f}",
                f"test_macro_recall={test_metrics['macro_recall']:.4f}",
                f"test_macro_f1={test_metrics['macro_f1']:.4f}",
                f"test_weighted_f1={test_metrics['weighted_f1']:.4f}",
                f"confusion_matrix_test={artifacts.cm_test_png}",
            ]
        )
    artifacts.summary_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary_json = {
        "data_dir": args.data_dir,
        "output": args.output,
        "device": args.device,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "weight_decay": args.weight_decay,
        "num_workers": args.num_workers,
        "class_names": class_names,
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "test_samples": len(test_dataset) if test_dataset else 0,
        "best_epoch": best_epoch,
        "best_val_metrics": best_val_metrics,
        "test_metrics": test_metrics,
        "artifacts": {
            "metrics_csv": str(artifacts.metrics_csv),
            "curves_png": str(artifacts.curves_png),
            "confusion_matrix_last": str(artifacts.cm_last_png),
            "confusion_matrix_best": str(artifacts.cm_best_png),
            "confusion_matrix_test": str(artifacts.cm_test_png),
            "report_best_json": str(artifacts.report_best_json),
            "report_test_json": str(artifacts.report_test_json),
        },
    }
    artifacts.summary_json.write_text(json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_test_dir(data_dir: Path) -> Path | None:
    direct_test = data_dir / "test"
    if direct_test.exists():
        return direct_test
    return None


def build_model(num_classes: int) -> nn.Module:
    model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def train(args):
    set_seed(args.seed)

    device = resolve_device(args.device, args.require_cuda)
    data_dir = Path(args.data_dir)
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"
    test_dir = Path(args.test_dir) if args.test_dir else infer_test_dir(data_dir)
    class_names = args.classes

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifacts = ensure_artifact_paths(output_path)

    train_dataset = ThyroidBinaryDataset(train_dir, class_names, transform=build_train_transform(args.image_size))
    val_dataset = ThyroidBinaryDataset(val_dir, class_names, transform=build_transform(args.image_size))
    test_dataset = None
    if test_dir is not None and test_dir.exists():
        test_dataset = ThyroidBinaryDataset(test_dir, class_names, transform=build_transform(args.image_size))

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    test_loader = None
    if test_dataset is not None:
        test_loader = DataLoader(
            test_dataset,
            batch_size=args.batch_size,
            shuffle=False,
            num_workers=args.num_workers,
            pin_memory=device.type == "cuda",
        )

    model = build_model(len(class_names)).to(device)
    class_weights = compute_class_weights(train_dataset, len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights if not args.disable_class_weights else None)
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    history = []
    best_epoch = 0
    best_val_acc = -1.0
    best_val_metrics = None
    best_val_confusion = None
    train_start = time.time()

    print(f"device={device}")
    print(f"classes={class_names}")
    print(f"train_dir={train_dir}")
    print(f"val_dir={val_dir}")
    print(f"test_dir={test_dir if test_dir else 'None'}")
    print(f"train_samples={len(train_dataset)} val_samples={len(val_dataset)} test_samples={len(test_dataset) if test_dataset else 0}")
    print(f"class_weights={class_weights.tolist()}")
    print(f"artifacts_dir={artifacts.dir}")

    for epoch in range(args.epochs):
        epoch_start = time.time()
        model.train()
        running_loss = 0.0
        running_correct = 0
        seen = 0
        total_batches = max(len(train_loader), 1)

        for step, (images, labels) in enumerate(train_loader, start=1):
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            preds = outputs.argmax(dim=1)
            running_loss += loss.item() * images.size(0)
            running_correct += (preds == labels).sum().item()
            seen += labels.size(0)

            if step == 1 or step % args.log_interval == 0 or step == total_batches:
                batch_elapsed = time.time() - epoch_start
                batch_eta = batch_elapsed / step * (total_batches - step)
                overall_elapsed = time.time() - train_start
                epoch_progress = epoch + step / total_batches
                avg_epoch_time = overall_elapsed / max(epoch_progress, 1e-8)
                total_eta = avg_epoch_time * (args.epochs - epoch_progress)
                print(
                    "epoch={}/{} batch={}/{} train_loss={:.4f} train_acc={:.4f} "
                    "epoch_eta={} total_eta={}".format(
                        epoch + 1,
                        args.epochs,
                        step,
                        total_batches,
                        running_loss / max(seen, 1),
                        running_correct / max(seen, 1),
                        format_seconds(batch_eta),
                        format_seconds(total_eta),
                    )
                )

        train_loss = running_loss / max(len(train_dataset), 1)
        train_acc = running_correct / max(len(train_dataset), 1)
        val_loss, val_acc, val_confusion, val_metrics = evaluate(model, val_loader, criterion, device, class_names)
        epoch_seconds = time.time() - epoch_start

        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": float(train_loss),
                "train_acc": float(train_acc),
                "val_loss": float(val_loss),
                "val_acc": float(val_acc),
                "val_macro_precision": float(val_metrics["macro_precision"]),
                "val_macro_recall": float(val_metrics["macro_recall"]),
                "val_macro_f1": float(val_metrics["macro_f1"]),
                "val_weighted_f1": float(val_metrics["weighted_f1"]),
                "epoch_seconds": float(epoch_seconds),
            }
        )

        print(
            "epoch={}/{} done in {} | train_loss={:.4f} train_acc={:.4f} "
            "val_loss={:.4f} val_acc={:.4f} val_macro_f1={:.4f}".format(
                epoch + 1,
                args.epochs,
                format_seconds(epoch_seconds),
                train_loss,
                train_acc,
                val_loss,
                val_acc,
                val_metrics["macro_f1"],
            )
        )

        save_metrics_csv(history, artifacts.metrics_csv)
        save_training_curves(history, artifacts.curves_png)
        save_confusion_matrix(val_confusion, class_names, artifacts.cm_last_png, title="Validation Confusion Matrix (Last)")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1
            best_val_metrics = val_metrics
            best_val_confusion = val_confusion.clone()
            torch.save(model.state_dict(), output_path)
            save_confusion_matrix(best_val_confusion, class_names, artifacts.cm_best_png, title="Validation Confusion Matrix (Best)")
            save_json_report(
                artifacts.report_best_json,
                {
                    "epoch": best_epoch,
                    "metrics": best_val_metrics,
                },
            )
            print(f"saved best weights: {output_path}")

    test_metrics = None
    if test_loader is not None and best_val_metrics is not None:
        best_model = build_model(len(class_names)).to(device)
        best_model.load_state_dict(torch.load(output_path, map_location=device))
        test_loss, test_acc, test_confusion, test_metrics = evaluate(best_model, test_loader, criterion, device, class_names)
        save_confusion_matrix(test_confusion, class_names, artifacts.cm_test_png, title="Test Confusion Matrix")
        save_json_report(
            artifacts.report_test_json,
            {
                "loss": test_loss,
                "accuracy": test_acc,
                "metrics": test_metrics,
            },
        )
        print(
            "test_loss={:.4f} test_acc={:.4f} test_macro_f1={:.4f}".format(
                test_loss,
                test_acc,
                test_metrics["macro_f1"],
            )
        )

    write_summary(
        args=args,
        class_names=class_names,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        test_dataset=test_dataset,
        best_epoch=best_epoch,
        best_val_metrics=best_val_metrics or {},
        test_metrics=test_metrics,
        artifacts=artifacts,
    )

    total_seconds = time.time() - train_start
    print(f"training finished in {format_seconds(total_seconds)}")
    print(f"best_epoch={best_epoch}")
    print(f"best_val_acc={best_val_acc:.4f}")
    print(f"weights={output_path}")
    print(f"artifacts={artifacts.dir}")


def create_parser(default_overrides: dict | None = None, description: str | None = None) -> argparse.ArgumentParser:
    default_overrides = default_overrides or {}
    default_data_dir = default_overrides.get("data_dir", os.path.join(REPO_ROOT, "datasets", "thyroid_tn5000"))
    default_output = default_overrides.get(
        "output",
        os.path.join(BASE_DIR, "models", f"thyroid_resnet50_formal_{time.strftime('%Y%m%d_%H%M%S')}.pth"),
    )

    parser = argparse.ArgumentParser(
        description=description or "Formal training script for thyroid ultrasound binary classification."
    )
    parser.add_argument(
        "--data-dir",
        default=default_data_dir,
        help="Dataset root containing train/, val/ and optional test/.",
    )
    parser.add_argument(
        "--test-dir",
        default=default_overrides.get("test_dir", ""),
        help="Optional explicit test split directory. If omitted, data_dir/test/ will be used when present.",
    )
    parser.add_argument("--epochs", type=int, default=default_overrides.get("epochs", 150))
    parser.add_argument("--batch-size", type=int, default=default_overrides.get("batch_size", 16))
    parser.add_argument("--lr", type=float, default=default_overrides.get("lr", 1e-4))
    parser.add_argument("--weight-decay", type=float, default=default_overrides.get("weight_decay", 1e-4))
    parser.add_argument("--image-size", type=int, default=default_overrides.get("image_size", 224))
    parser.add_argument("--seed", type=int, default=default_overrides.get("seed", 42))
    parser.add_argument(
        "--num-workers",
        type=int,
        default=default_overrides.get("num_workers", 0 if os.name == "nt" else 4),
    )
    parser.add_argument("--log-interval", type=int, default=default_overrides.get("log_interval", 20))
    parser.add_argument(
        "--device",
        default=default_overrides.get("device", ""),
        help="Training device. Leave empty to auto-select cuda if available, otherwise cpu.",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        default=default_overrides.get("classes", ["benign", "malignant"]),
        help="Class names used for training, in label order.",
    )
    parser.add_argument(
        "--require-cuda",
        action="store_true",
        default=default_overrides.get("require_cuda", False),
        help="Fail immediately when CUDA is unavailable.",
    )
    parser.add_argument(
        "--disable-class-weights",
        action="store_true",
        default=default_overrides.get("disable_class_weights", False),
        help="Disable class-weighted cross entropy.",
    )
    parser.add_argument(
        "--output",
        default=default_output,
        help="Output path for best model weights.",
    )
    return parser


if __name__ == "__main__":
    parser = create_parser(
        default_overrides={
            "data_dir": os.path.join(REPO_ROOT, "datasets", "thyroid_tn5000"),
            "epochs": 150,
            "batch_size": 16,
            "lr": 1e-4,
            "weight_decay": 1e-4,
            "image_size": 224,
            "seed": 42,
            "num_workers": 0 if os.name == "nt" else 4,
            "log_interval": 20,
            "device": "",
            "classes": ["benign", "malignant"],
            "require_cuda": False,
            "output": os.path.join(
                BASE_DIR,
                "models",
                f"thyroid_resnet50_tn5000_formal_{time.strftime('%Y%m%d_%H%M%S')}.pth",
            ),
        }
    )
    args = parser.parse_args()
    train(args)
