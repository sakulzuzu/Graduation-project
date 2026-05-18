import { useState } from "react";
import { API_BASE, apiRequest } from "../api/client";

function UploadPanel({ onPrediction }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFileChange = (event) => {
    const chosen = event.target.files[0];
    setFile(chosen || null);
    setPreviewUrl(chosen ? URL.createObjectURL(chosen) : "");
  };

  const handleUpload = async () => {
    if (!file) {
      setError("请先选择影像文件");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const uploadResult = await apiRequest("/api/images/upload", {
        method: "POST",
        body: formData
      });
      const prediction = await apiRequest(`/api/predict/${uploadResult.image_id}`, {
        method: "POST"
      });
      onPrediction({
        ...prediction,
        image_id: uploadResult.image_id,
        original_url: `${API_BASE}/api/images/${uploadResult.image_id}/original`
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>超声影像上传</h2>
          <p>仅支持 JPEG 或 PNG 格式</p>
        </div>
        <button className="primary" onClick={handleUpload} disabled={loading}>
          {loading ? "分析中..." : "开始分类"}
        </button>
      </div>
      <div className="upload-grid">
        <label className="dropzone">
          <input type="file" accept="image/png,image/jpeg" onChange={handleFileChange} />
          <div>
            <strong>选择超声影像</strong>
            <span>拖拽到此处或点击选择文件</span>
          </div>
        </label>
        <div className="preview">
          {previewUrl ? (
            <img src={previewUrl} alt="影像预览" />
          ) : (
            <div className="placeholder">预览区</div>
          )}
        </div>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  );
}

export default UploadPanel;
