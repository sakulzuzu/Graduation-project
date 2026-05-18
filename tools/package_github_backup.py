from __future__ import annotations

import shutil
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
DST_ROOT = Path(r"D:\AAAAAAA\Graduation project code")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: Path, dst: Path, ignore=None) -> None:
    if not src.exists():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def keep_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def package_backend() -> None:
    backend_src = SRC_ROOT / "backend"
    backend_dst = DST_ROOT / "backend"

    for name in ["app.py", "config.py", "models.py", "requirements.txt", "__init__.py"]:
        copy_file(backend_src / name, backend_dst / name)

    copy_tree(backend_src / "ml", backend_dst / "ml", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_tree(backend_src / "scripts", backend_dst / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    copy_tree(backend_src / "services", backend_dst / "services", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    write_text(
        backend_dst / ".env.example",
        "\n".join(
            [
                "SECRET_KEY=change-me",
                "DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/thyroid_ai?charset=utf8mb4",
                "ADMIN_INVITE_CODE=invite-admin",
                "JWT_EXPIRE_SECONDS=7200",
                "MODEL_WEIGHTS=backend/models/thyroid_resnet50.pth",
                "UPLOAD_DIR=backend/storage/original",
                "PROCESSED_DIR=backend/storage/processed",
                "HEATMAP_DIR=backend/storage/heatmap",
                "",
            ]
        ),
    )

    write_text(
        backend_dst / "models" / "README.md",
        """# 模型权重说明

本目录默认用于放置后端推理所需的模型权重文件，例如：

- `thyroid_resnet50.pth`
- `thyroid_resnet50_tn5000_formal_20260507_024833.pth`

为了便于上传 GitHub，本次备份版未直接包含 `.pth` 权重文件，原因如下：

1. 单个权重文件约 94 MB，接近 GitHub 单文件大小限制。
2. 多个权重文件会显著增大仓库体积，不利于后续代码备份与版本管理。

如需恢复完整运行环境，可手动将本地权重文件复制到本目录，或使用 Git LFS 单独管理模型文件。
""",
    )

    for sub in ["original", "processed", "heatmap"]:
        keep_file(backend_dst / "storage" / sub / ".gitkeep")


def package_frontend() -> None:
    frontend_src = SRC_ROOT / "frontend"
    frontend_dst = DST_ROOT / "frontend"

    for name in ["index.html", "package.json", "package-lock.json", "vite.config.js"]:
        copy_file(frontend_src / name, frontend_dst / name)

    write_text(frontend_dst / ".env.example", "VITE_API_BASE=http://localhost:5000\n")
    copy_tree(frontend_src / "public", frontend_dst / "public", ignore=shutil.ignore_patterns(".DS_Store"))
    copy_tree(
        frontend_src / "src",
        frontend_dst / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def package_database() -> None:
    copy_file(SRC_ROOT / "database" / "schema.sql", DST_ROOT / "database" / "schema.sql")


def package_docs() -> None:
    docs_dst = DST_ROOT / "docs"
    copy_tree(SRC_ROOT / "docs" / "diagrams", docs_dst / "diagrams", ignore=shutil.ignore_patterns(".DS_Store"))

    art_src = SRC_ROOT / "backend" / "models" / "thyroid_resnet50_tn5000_formal_20260507_024833_artifacts"
    art_dst = docs_dst / "experiment_results" / "formal_training_20260507"
    selected_artifacts = [
        "summary.txt",
        "summary.json",
        "metrics.csv",
        "best_val_report.json",
        "test_report.json",
        "training_curves.png",
        "confusion_matrix_best.png",
        "confusion_matrix_test.png",
    ]
    for name in selected_artifacts:
        copy_file(art_src / name, art_dst / name)

    download_candidates = {
        "training_curves_optimized.png": "training_curves_optimized.png",
        "validation_confusion_matrix_best_optimized.png": "validation_confusion_matrix_best_optimized.png",
        "test_confusion_matrix_optimized.png": "test_confusion_matrix_optimized.png",
        "public_dataset_training_result_supplement_enhanced.docx": "public_dataset_training_result_supplement_enhanced.docx",
    }
    downloads = Path(r"C:\Users\86136\Downloads")
    for src_name, dst_name in download_candidates.items():
        src = downloads / src_name
        if src.exists():
            copy_file(src, art_dst / dst_name)

    write_text(
        docs_dst / "EXPERIMENT_RESULTS.md",
        """# 公开数据集训练结果说明

本项目已在整理后的 TN5000 数据集上完成正式训练与测试，相关结果已整理到：

- `docs/experiment_results/formal_training_20260507/`

其中包含：

- `summary.txt` / `summary.json`：训练摘要
- `metrics.csv`：逐轮训练与验证指标
- `best_val_report.json`：最优验证轮次结果
- `test_report.json`：测试集结果
- `training_curves.png`：原始训练曲线图
- `confusion_matrix_best.png`：原始最优验证集混淆矩阵图
- `confusion_matrix_test.png`：原始测试集混淆矩阵图
- `training_curves_optimized.png`：优化后的训练曲线图
- `validation_confusion_matrix_best_optimized.png`：优化后的验证集混淆矩阵图
- `test_confusion_matrix_optimized.png`：优化后的测试集混淆矩阵图
- `public_dataset_training_result_supplement_enhanced.docx`：可直接用于论文插入的实验结果补充说明文档

本次正式训练的核心结果如下：

- 最优验证轮次：第 32 轮
- 最优验证集准确率：93.80%
- 测试集损失：0.3985
- 测试集准确率：89.20%
- 测试集 Macro-F1：85.93%

这些结果可作为系统模型有效性的实验支撑材料。
""",
    )

    write_text(
        docs_dst / "PROJECT_STRUCTURE.md",
        """# 项目目录说明

## 顶层目录

- `backend/`：Flask 后端、模型推理、训练脚本与服务逻辑
- `frontend/`：React 前端页面、交互组件与接口调用代码
- `database/`：数据库建表脚本
- `docs/`：系统结构图、实验结果说明、训练产物整理
- `datasets/`：数据集结构说明（不包含实际数据）
- `tools/`：数据集准备、实验结果整理与图像优化工具脚本

## backend

- `app.py`：后端主入口，定义认证、上传、推理、历史记录、报告管理等 API
- `config.py`：读取环境变量并构建应用配置
- `models.py`：数据库模型定义，包含用户、影像、预测、报告、审计日志等实体
- `ml/`：模型加载、推理、Grad-CAM 热力图生成与图像预处理逻辑
- `services/`：鉴权、文件存储等通用服务
- `scripts/`：数据库初始化、管理员创建、训练脚本等
- `storage/`：运行时原图、过程图和热力图目录，占位保留，默认不提交实际内容
- `models/`：模型权重放置目录，本次备份未包含 `.pth` 大文件

## frontend

- `src/App.jsx`：前端主界面状态协调
- `src/components/`：登录、上传、结果、历史、报告等业务组件
- `src/api/client.js`：前端请求封装
- `styles.css`：全局样式

## docs

- `diagrams/`：系统架构图、模块图、用例图、E-R 图等
- `experiment_results/`：正式训练结果、优化图和论文补充说明文档

## tools

保留了与项目运行、训练和结果整理直接相关的脚本，便于后续复现：

- 数据集下载与整理
- 合成数据集生成
- 训练曲线与混淆矩阵优化绘图
- 公开数据集训练结果补充说明生成
- GitHub 备份打包脚本
""",
    )

    write_text(
        docs_dst / "GITHUB_UPLOAD_NOTES.md",
        """# GitHub 上传说明

本备份目录已按适合上传 GitHub 的方式进行整理，默认不包含以下内容：

- 虚拟环境目录：`.venv/`、`.venv-1/`
- 前端依赖目录：`frontend/node_modules/`
- 构建产物目录：`frontend/dist/`
- 原始数据集与压缩包：`datasets/raw/`、`datasets/thyroid_tn5000/`、`datasets/thyroid_synthetic/`
- 本地运行生成的上传影像与热力图：`backend/storage/` 中的实际内容
- 本地敏感配置：`backend/.env`、`frontend/.env`
- 训练权重文件：`backend/models/*.pth`

如果后续需要把模型权重也纳入仓库，建议使用 Git LFS，而不是直接提交到普通 Git 仓库。
""",
    )


def package_datasets_readme() -> None:
    write_text(
        DST_ROOT / "datasets" / "README.md",
        """# 数据集说明

本备份目录不直接包含训练数据与原始压缩包，仅保留数据集组织说明。

正式训练时建议采用如下目录结构：

```text
datasets/thyroid_tn5000/
  train/
    benign/
    malignant/
  val/
    benign/
    malignant/
  test/
    benign/
    malignant/
```

其中：

- `train/`：训练集
- `val/`：验证集
- `test/`：测试集

本项目附带了数据准备脚本，可根据原始 TN5000 数据整理为上述分类目录结构。
""",
    )


def package_tools() -> None:
    tools_dst = DST_ROOT / "tools"
    selected = [
        "download_tn5000.py",
        "prepare_tn5000_classification_dataset.py",
        "generate_synthetic_thyroid_dataset.py",
        "generate_optimized_training_curves.py",
        "generate_optimized_confusion_matrix.py",
        "generate_public_dataset_training_result_supplement.py",
        "package_github_backup.py",
    ]
    for name in selected:
        copy_file(SRC_ROOT / "tools" / name, tools_dst / name)


def write_root_readme() -> None:
    write_text(
        DST_ROOT / "README.md",
        """# 基于迁移学习的甲状腺结节超声影像良恶性辅助分析系统

## 项目简介

本项目是一个本科毕业设计系统，目标是构建一个面向甲状腺结节超声影像的良恶性辅助分析工具。系统采用前后端分离架构，后端基于 Flask 提供用户认证、影像上传、模型推理、历史记录、诊断报告与审核接口，前端基于 React 实现医生与管理员双角色交互界面。模型部分采用预训练 ResNet50 进行迁移学习，并结合 Grad-CAM 生成热力图，提高预测结果的可解释性。

## 技术栈

- 前端：React、Vite
- 后端：Flask、Flask-SQLAlchemy、PyMySQL、JWT
- 深度学习：PyTorch、Torchvision、ResNet50、Grad-CAM
- 数据库：MySQL
- 训练与结果整理：Python 脚本、PIL

## 核心功能

- 用户注册、登录与角色区分（医生 / 管理员）
- 甲状腺超声影像上传（JPEG / PNG）
- 良恶性二分类推理与概率输出
- 热力图可解释化展示
- 历史记录查询（按时间 / 预测记录 ID）
- 诊断报告创建、查看与管理员审核
- 实验训练结果整理与论文插图辅助生成

## 目录结构

详细目录说明见：

- `docs/PROJECT_STRUCTURE.md`

## 快速启动

### 1. 后端

进入 `backend/`，根据 `.env.example` 创建 `.env`，安装依赖后运行：

```powershell
python app.py
```

### 2. 前端

进入 `frontend/`，根据 `.env.example` 创建 `.env`，安装依赖后运行：

```powershell
npm install
npm run dev
```

### 3. 数据库

使用 `database/schema.sql` 初始化数据库结构。

## 模型与数据说明

- 本备份版未包含 `.pth` 模型权重文件
- 本备份版未包含 TN5000 实际数据集图像与原始压缩包
- 如需复现实验，请手动准备数据集，并将模型权重放入 `backend/models/`

## 训练与实验结果

公开数据集训练结果已整理在：

- `docs/EXPERIMENT_RESULTS.md`
- `docs/experiment_results/formal_training_20260507/`

## GitHub 备份建议

上传前可先阅读：

- `docs/GITHUB_UPLOAD_NOTES.md`

本目录已经尽量整理为适合 GitHub 备份的版本，但实际上传时仍建议再次检查：

- 是否误带本地账号密码
- 是否误带大体积数据或模型文件
- 是否需要使用 Git LFS 管理权重文件
""",
    )


def write_gitignore() -> None:
    write_text(
        DST_ROOT / ".gitignore",
        """# Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Virtual environments
.venv/
.venv-1/

# Local env files
backend/.env
frontend/.env

# Frontend dependencies and build output
frontend/node_modules/
frontend/dist/

# Runtime storage
backend/storage/original/*
backend/storage/processed/*
backend/storage/heatmap/*
!backend/storage/original/.gitkeep
!backend/storage/processed/.gitkeep
!backend/storage/heatmap/.gitkeep

# Large model files
backend/models/*.pth

# Datasets
datasets/raw/
datasets/thyroid_tn5000/
datasets/thyroid_synthetic/

# Temporary and local preview directories
tmp/
generated/
defense_ppt_preview/
ppt_preview_focused/
ppt_preview_summary4/
template_summary4_preview/
template_tech1_preview/
extracted_thesis_media/
tmp_thesis_v12_media/

# Office temp files
~$*.docx
~$*.pptx
""",
    )


def main() -> None:
    DST_ROOT.mkdir(parents=True, exist_ok=True)
    package_backend()
    package_frontend()
    package_database()
    package_docs()
    package_datasets_readme()
    package_tools()
    write_root_readme()
    write_gitignore()
    print(DST_ROOT)


if __name__ == "__main__":
    main()
