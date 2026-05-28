// API 客户端 — 财务自由顾问
const BASE = '';

const Auth = {
  getToken: () => localStorage.getItem('fire_token'),
  setToken: (t) => localStorage.setItem('fire_token', t),
  clear: () => localStorage.removeItem('fire_token'),
  headers: () => {
    const t = Auth.getToken();
    return t ? { 'Authorization': `Bearer ${t}` } : {};
  },
};

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...Auth.headers() },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (res.status === 204) return null;
  if (res.status === 401) {
    Auth.clear();
    window._showLogin && window._showLogin();
    throw new Error('请先登录');
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || '请求失败');
  return data;
}

const API = {
  get:    (path)       => request('GET',    path),
  post:   (path, body) => request('POST',   path, body),
  put:    (path, body) => request('PUT',    path, body),
  delete: (path)       => request('DELETE', path),

  // FIRE
  fireStatus:     ()           => API.get('/api/fire/status'),
  fireProfile:    ()           => API.get('/api/fire/profile'),
  updateFireProfile: (body)    => API.put('/api/fire/profile', body),
  fireProjection: (years = 30) => API.get(`/api/fire/projection?years=${years}`),

  // 交易
  transactions: (params) => API.get('/api/transactions?' + new URLSearchParams(params).toString()),
  createTxn:    (body)   => API.post('/api/transactions', body),
  updateTxn:    (id, b)  => API.put(`/api/transactions/${id}`, b),
  deleteTxn:    (id)     => API.delete(`/api/transactions/${id}`),

  // 分类
  categories: () => API.get('/api/categories'),

  // 导入
  importBill: async (source, file) => {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${BASE}/api/import/${source}`, {
      method: 'POST',
      headers: Auth.headers(),
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '导入失败');
    return data;
  },
  sampleUrl: (source) => `${BASE}/api/import/sample/${source}`,

  // AI
  aiChat:         (msg)  => API.post('/api/ai/chat', { message: msg }),
  aiAnalysis:     ()     => API.post('/api/ai/analysis', {}),
  aiHistory:      ()     => API.get('/api/ai/history'),
  aiClearHistory: ()     => API.delete('/api/ai/history'),

  // 认证
  authMe:       ()     => API.get('/api/auth/me'),
  authLogin:    (body) => API.post('/api/auth/login', body),
  authRegister: (body) => API.post('/api/auth/register', body),
};
