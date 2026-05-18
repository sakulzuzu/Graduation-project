import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";

function HistoryPanel({ onSelect }) {
  const [items, setItems] = useState([]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [predictionId, setPredictionId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadHistory = async () => {
    setLoading(true);
    setError("");
    try {
      const trimmedPredictionId = predictionId.trim();
      if (trimmedPredictionId && (!/^\d+$/.test(trimmedPredictionId) || Number(trimmedPredictionId) <= 0)) {
        setError("预测ID必须是正整数");
        setLoading(false);
        return;
      }

      const params = new URLSearchParams();
      if (start) params.append("start", start);
      if (end) params.append("end", end);
      if (trimmedPredictionId) params.append("prediction_id", trimmedPredictionId);
      const query = params.toString();
      const result = await apiRequest(`/api/history${query ? `?${query}` : ""}`);
      setItems(result.items || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const renderLabel = (label) => {
    if (label === "malignant") return "恶性";
    if (label === "benign") return "良性";
    return label;
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>历史记录</h2>
          <p>按时间或预测ID筛选并复用历史预测结果。</p>
        </div>
        <button className="ghost" onClick={loadHistory} disabled={loading}>
          {loading ? "刷新中..." : "刷新"}
        </button>
      </div>
      <div className="filters history-filters">
        <label className="id-filter">
          预测ID
          <input
            type="number"
            min="1"
            value={predictionId}
            onChange={(e) => setPredictionId(e.target.value)}
            placeholder="例如 12"
          />
        </label>
        <label>
          开始日期
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          结束日期
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <button className="primary" onClick={loadHistory} disabled={loading}>
          应用筛选
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      <div className="history-table">
        <div className="history-row header">
          <span>ID</span>
          <span>影像ID</span>
          <span>标签</span>
          <span>良性</span>
          <span>恶性</span>
          <span>时间</span>
          <span></span>
        </div>
        {items.length === 0 && <div className="empty">暂无记录。</div>}
        {items.map((item) => (
          <div className="history-row" key={item.prediction_id}>
            <span>{item.prediction_id}</span>
            <span>{item.image_id}</span>
            <span className={item.label}>{renderLabel(item.label)}</span>
            <span>{(item.prob_benign * 100).toFixed(1)}%</span>
            <span>{(item.prob_malignant * 100).toFixed(1)}%</span>
            <span>{new Date(item.created_at).toLocaleString()}</span>
            <button className="ghost" onClick={() => onSelect(item)}>
              使用
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default HistoryPanel;
