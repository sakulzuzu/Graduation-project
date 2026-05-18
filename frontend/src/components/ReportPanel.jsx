import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";

function ReportPanel({ predictionId, userRole }) {
  const [content, setContent] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [reviewingId, setReviewingId] = useState(null);
  const isAdmin = userRole === "admin";

  const loadReports = async () => {
    if (!predictionId && !isAdmin) {
      setReports([]);
      setListError("");
      return;
    }

    setListLoading(true);
    setListError("");
    try {
      const query = predictionId ? `?prediction_id=${predictionId}` : "";
      const result = await apiRequest(`/api/reports${query}`);
      setReports(result.items || []);
    } catch (err) {
      setListError(err.message);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, [predictionId, userRole]);

  const renderStatusLabel = (status) => {
    if (status === "approved") return "已通过";
    if (status === "rejected") return "已驳回";
    if (status === "draft") return "待审核";
    return status || "未知";
  };

  const renderStatusClass = (status) => {
    if (status === "approved") return "benign";
    if (status === "rejected") return "malignant";
    return "pending";
  };

  const handleSubmit = async () => {
    if (!predictionId) {
      setError("请先选择一条预测记录");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await apiRequest("/api/reports", {
        method: "POST",
        body: JSON.stringify({ prediction_id: predictionId, content })
      });
      setMessage(`报告已创建：${result.report_id}`);
      setContent("");
      loadReports();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (reportId, status) => {
    setReviewingId(reportId);
    setError("");
    setMessage("");
    try {
      await apiRequest(`/api/reports/${reportId}/review`, {
        method: "POST",
        body: JSON.stringify({ status })
      });
      setMessage(status === "approved" ? "报告已审核通过" : "报告已驳回");
      await loadReports();
    } catch (err) {
      setError(err.message);
    } finally {
      setReviewingId(null);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>诊断报告</h2>
          <p>{isAdmin ? "管理员可审核报告，医生仅可填写和查看。" : "为当前选中的预测结果填写诊断说明。"}</p>
        </div>
        <div className="top-actions">
          <button className="ghost" onClick={loadReports} disabled={listLoading || (!predictionId && !isAdmin)}>
            {listLoading ? "加载中..." : "查看报告"}
          </button>
          <button className="primary" onClick={handleSubmit} disabled={loading}>
            {loading ? "保存中..." : "保存报告"}
          </button>
        </div>
      </div>
      <div className="status">
        当前预测ID：{predictionId || (isAdmin ? "全部（管理员审核视图）" : "未选择")}
      </div>
      <label className="textarea">
        备注
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="请输入临床说明、风险因素与随访建议..."
        />
      </label>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {listError && <div className="error">{listError}</div>}

      <div className="report-list">
        <h3>报告记录</h3>
        {!predictionId && !isAdmin && <div className="empty">请先在左侧选择一条预测记录。</div>}
        {(predictionId || isAdmin) && listLoading && <div className="empty">报告加载中...</div>}
        {(predictionId || isAdmin) && !listLoading && reports.length === 0 && <div className="empty">暂无报告记录。</div>}
        {reports.map((report) => (
          <div className="report-item" key={report.report_id}>
            <div className="report-meta">
              <span>报告ID：{report.report_id}</span>
              <span className={`pill ${renderStatusClass(report.status)}`}>
                {renderStatusLabel(report.status)}
              </span>
            </div>
            <p>{report.content}</p>
            <div className="report-time">
              <span>创建时间：{report.created_at ? new Date(report.created_at).toLocaleString() : "-"}</span>
              <span>审核时间：{report.reviewed_at ? new Date(report.reviewed_at).toLocaleString() : "未审核"}</span>
            </div>
            {isAdmin && (
              <div className="review-actions">
                <button
                  className="ghost"
                  type="button"
                  onClick={() => handleReview(report.report_id, "approved")}
                  disabled={reviewingId === report.report_id || report.status === "approved"}
                >
                  {reviewingId === report.report_id ? "处理中..." : "通过"}
                </button>
                <button
                  className="ghost danger"
                  type="button"
                  onClick={() => handleReview(report.report_id, "rejected")}
                  disabled={reviewingId === report.report_id || report.status === "rejected"}
                >
                  {reviewingId === report.report_id ? "处理中..." : "驳回"}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ReportPanel;
