# 公开数据集训练结果说明

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
