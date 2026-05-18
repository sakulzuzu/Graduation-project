import { useState } from "react";
import { apiRequest, setToken } from "../api/client";

function AuthPanel({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("doctor");
  const [adminCode, setAdminCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "login") {
        const result = await apiRequest("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });
        setToken(result.token);
        onAuth(result);
      } else {
        await apiRequest("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({
            email,
            password,
            role,
            admin_code: adminCode
          })
        });
        setMode("login");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel auth-panel">
      <div className="panel-header">
        <div>
          <h2>{mode === "login" ? "登录" : "注册账号"}</h2>
          <p>面向医生与管理员的安全访问入口</p>
        </div>
        <button
          type="button"
          className="ghost"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "去注册" : "返回登录"}
        </button>
      </div>
      <form onSubmit={handleSubmit} className="form-grid">
        <label>
          邮箱
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required />
        </label>
        <label>
          密码
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required />
        </label>
        {mode === "register" && (
          <>
            <label>
              角色
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="doctor">医生</option>
                <option value="admin">管理员</option>
              </select>
            </label>
            {role === "admin" && (
              <label>
                管理员邀请码
                <input value={adminCode} onChange={(e) => setAdminCode(e.target.value)} />
              </label>
            )}
          </>
        )}
        {error && <div className="error">{error}</div>}
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
        </button>
      </form>
    </div>
  );
}

export default AuthPanel;
