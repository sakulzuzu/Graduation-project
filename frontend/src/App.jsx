import { useEffect, useState } from "react";
import { API_BASE, apiRequest, clearToken, getToken } from "./api/client";
import AuthPanel from "./components/AuthPanel";
import HistoryPanel from "./components/HistoryPanel";
import ReportPanel from "./components/ReportPanel";
import ResultPanel from "./components/ResultPanel";
import UploadPanel from "./components/UploadPanel";
import "./styles.css";

function App() {
  const [token, setTokenState] = useState(getToken());
  const [profile, setProfile] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [activePredictionId, setActivePredictionId] = useState(null);
  const [status, setStatus] = useState("");

  const loadProfile = async () => {
    try {
      const data = await apiRequest("/api/users/me");
      setProfile(data);
    } catch (err) {
      clearToken();
      setTokenState(null);
      setProfile(null);
    }
  };

  useEffect(() => {
    if (token) {
      loadProfile();
    }
  }, [token]);

  const handleAuth = (authData) => {
    setTokenState(authData.token);
    setProfile({ id: authData.user_id, role: authData.role });
  };

  const handleLogout = () => {
    clearToken();
    setTokenState(null);
    setProfile(null);
    setPrediction(null);
    setActivePredictionId(null);
  };

  const handlePrediction = (predictionData) => {
    setPrediction(predictionData);
    setActivePredictionId(predictionData.prediction_id);
    setStatus("已加载最新模型结果");
  };

  const handleHistorySelect = (item) => {
    const selected = {
      prediction_id: item.prediction_id,
      image_id: item.image_id,
      label: item.label,
      prob_benign: item.prob_benign,
      prob_malignant: item.prob_malignant,
      original_url: `${API_BASE}/api/images/${item.image_id}/original`,
      heatmap_url: `${API_BASE}/api/images/${item.image_id}/heatmap`
    };
    setPrediction(selected);
    setActivePredictionId(item.prediction_id);
    setStatus(`已加载预测记录 ${item.prediction_id}。`);
  };

  if (!token) {
    return (
      <div className="page">
        <header className="hero">
          <div>
            <p className="eyebrow">甲状腺超声影像 AI</p>
            <h1>基于迁移学习的甲状腺结节超声影像良恶性辅助分析系统</h1>
          </div>
        </header>
        <AuthPanel onAuth={handleAuth} />
      </div>
    );
  }

  return (
    <div className="page">
      <header className="top-bar">
        <div>
          <p className="eyebrow">甲状腺超声影像 AI</p>
          <h1>临床辅助分析工作台</h1>
        </div>
        <div className="top-actions">
          {profile && (
            <div className="user-chip">
              <span>{profile.email || "用户"}</span>
              <span className="role">{profile.role === "admin" ? "管理员" : "医生"}</span>
            </div>
          )}
          <button className="ghost" onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </header>

      {status && <div className="status">{status}</div>}

      <div className="grid">
        <div className="column">
          <UploadPanel onPrediction={handlePrediction} />
          <ResultPanel prediction={prediction} />
        </div>
        <div className="column">
          <HistoryPanel onSelect={handleHistorySelect} />
          <ReportPanel predictionId={activePredictionId} userRole={profile?.role} />
        </div>
      </div>
    </div>
  );
}

export default App;
