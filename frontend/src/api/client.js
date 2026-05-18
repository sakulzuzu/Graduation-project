const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

const ERROR_I18N = {
  "email and password required": "邮箱和密码不能为空",
  "invalid role": "角色无效",
  "invalid admin code": "管理员邀请码错误",
  "email already exists": "邮箱已被注册",
  "invalid credentials": "邮箱或密码错误",
  "missing token": "缺少登录凭证，请先登录",
  "invalid token": "登录凭证无效，请重新登录",
  "user not found": "用户不存在",
  "forbidden": "无权限访问该资源",
  "file required": "请上传影像文件",
  "invalid file": "文件格式无效，仅支持 JPG/PNG",
  "heatmap not available": "热力图暂不可用",
  "original image not found": "原始影像文件不存在",
  "heatmap file not found": "热力图文件不存在",
  "image not found": "影像不存在",
  "prediction_id and content required": "请提供预测记录ID和报告内容",
  "invalid prediction_id": "预测ID无效，请输入正整数",
  "invalid review status": "审核状态无效",
  "Request failed": "请求失败",
  "请求失败": "请求失败"
};

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearToken() {
  localStorage.removeItem("token");
}

function normalizeErrorMessage(errorText) {
  const raw = (errorText || "").trim();
  if (!raw) return "请求失败";
  try {
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && typeof parsed.error === "string") {
      return ERROR_I18N[parsed.error] || parsed.error;
    }
  } catch (_e) {
    // Keep raw text when it is not JSON.
  }
  return ERROR_I18N[raw] || raw;
}

async function apiRequest(path, options = {}) {
  const isAbsolute = typeof path === "string" && (path.startsWith("http://") || path.startsWith("https://"));
  const url = isAbsolute ? path : `${API_BASE}${path}`;
  const headers = options.headers ? { ...options.headers } : {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const isForm = options.body instanceof FormData;
  if (!isForm && options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(url, { ...options, headers });
  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const errorText = contentType.includes("application/json")
      ? JSON.stringify(await response.json())
      : await response.text();
    throw new Error(normalizeErrorMessage(errorText));
  }
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.blob();
}

export { API_BASE, apiRequest, getToken, setToken, clearToken };
