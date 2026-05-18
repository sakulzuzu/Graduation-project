# 基于迁移学习的甲状腺结节超声影像良恶性辅助分析系统

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
