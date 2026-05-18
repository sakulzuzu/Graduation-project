import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";

function toApiPath(url) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.search}`;
  }
  return url;
}

function ResultPanel({ prediction }) {
  const [originalSrc, setOriginalSrc] = useState("");
  const [heatmapSrc, setHeatmapSrc] = useState("");
  const [imageError, setImageError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let originalObjectUrl = "";
    let heatmapObjectUrl = "";

    const loadProtectedImages = async () => {
      if (!prediction?.original_url || !prediction?.heatmap_url) {
        setOriginalSrc("");
        setHeatmapSrc("");
        setImageError("");
        return;
      }

      setImageError("");
      setOriginalSrc("");
      setHeatmapSrc("");

      try {
        const [originalBlob, heatmapBlob] = await Promise.all([
          apiRequest(toApiPath(prediction.original_url)),
          apiRequest(toApiPath(prediction.heatmap_url))
        ]);
        if (cancelled) return;

        originalObjectUrl = URL.createObjectURL(originalBlob);
        heatmapObjectUrl = URL.createObjectURL(heatmapBlob);
        setOriginalSrc(originalObjectUrl);
        setHeatmapSrc(heatmapObjectUrl);
      } catch (err) {
        if (!cancelled) {
          setImageError(err.message || "影像加载失败");
        }
      }
    };

    loadProtectedImages();

    return () => {
      cancelled = true;
      if (originalObjectUrl) URL.revokeObjectURL(originalObjectUrl);
      if (heatmapObjectUrl) URL.revokeObjectURL(heatmapObjectUrl);
    };
  }, [prediction?.original_url, prediction?.heatmap_url]);

  if (!prediction) {
    return (
      <div className="panel empty-state">
        <h2>暂无分类结果</h2>
        <p>请先上传影像，系统将生成良恶性概率和热力图</p>
      </div>
    );
  }

  const benign = (prediction.prob_benign * 100).toFixed(1);
  const malignant = (prediction.prob_malignant * 100).toFixed(1);
  const labelText = prediction.label === "malignant" ? "恶性" : prediction.label === "benign" ? "良性" : prediction.label;

  return (
    <div className="panel result-panel">
      <div className="panel-header">
        <div>
          <h2>预测结果</h2>
          <p>{prediction.label === "malignant" ? "高风险倾向" : "倾向良性"}评估</p>
        </div>
        <span className={`pill ${prediction.label}`}>
          {labelText}
        </span>
      </div>
      <div className="result-grid">
        <div className="result-metrics">
          <div className="metric">
            <span>良性概率</span>
            <strong>{benign}%</strong>
          </div>
          <div className="metric">
            <span>恶性概率</span>
            <strong>{malignant}%</strong>
          </div>
          <div className="metric">
            <span>影像ID</span>
            <strong>{prediction.image_id}</strong>
          </div>
        </div>
        <div className="result-images">
          <div>
            <span>原始影像</span>
            {originalSrc ? (
              <img src={originalSrc} alt="原始影像" />
            ) : (
              <div className="placeholder">原始影像加载中...</div>
            )}
          </div>
          <div>
            <span>热力图</span>
            {heatmapSrc ? (
              <img src={heatmapSrc} alt="热力图" />
            ) : (
              <div className="placeholder">热力图加载中...</div>
            )}
          </div>
        </div>
      </div>
      {imageError && <div className="error">{imageError}</div>}
    </div>
  );
}

export default ResultPanel;
