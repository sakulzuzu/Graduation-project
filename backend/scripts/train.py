import os
import time

from train_formal import BASE_DIR, REPO_ROOT, create_parser, train


def smoke_output_path() -> str:
    return os.path.join(
        BASE_DIR,
        "models",
        f"thyroid_resnet50_tn5000_smoke_{time.strftime('%Y%m%d_%H%M%S')}.pth",
    )


if __name__ == "__main__":
    parser = create_parser(
        default_overrides={
            "data_dir": os.path.join(REPO_ROOT, "datasets", "thyroid_tn5000"),
            "epochs": 3,
            "batch_size": 8,
            "lr": 1e-4,
            "weight_decay": 1e-4,
            "image_size": 224,
            "seed": 42,
            "num_workers": 0 if os.name == "nt" else 4,
            "log_interval": 10,
            "device": "",
            "classes": ["benign", "malignant"],
            "require_cuda": False,
            "output": smoke_output_path(),
        },
        description="Smoke-test GPU training script for thyroid ultrasound binary classification.",
    )
    args = parser.parse_args()
    train(args)
