# 数据集说明

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
