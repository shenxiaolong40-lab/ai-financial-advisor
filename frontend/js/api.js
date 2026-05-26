const BASE = 'http://localhost:8000';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(BASE + path, opts);
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || '请求失败');
  return data;
}

const API = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  put: (path, body) => request('PUT', path, body),
  delete: (path) => request('DELETE', path),

  dashboard: (month) => API.get('/api/dashboard/summary' + (month ? `?month=${month}` : '')),
  trend: (months) => API.get(`/api/dashboard/trend?months=${months || 6}`),
  transactions: (params) => API.get('/api/transactions?' + new URLSearchParams(params).toString()),
  createTxn: (body) => API.post('/api/transactions', body),
  updateTxn: (id, body) => API.put(`/api/transactions/${id}`, body),
  deleteTxn: (id) => API.delete(`/api/transactions/${id}`),
  categories: () => API.get('/api/categories'),
  accounts: () => API.get('/api/accounts'),
  createAccount: (body) => API.post('/api/accounts', body),
  goals: () => API.get('/api/goals'),
  createGoal: (body) => API.post('/api/goals', body),
  updateGoal: (id, body) => API.put(`/api/goals/${id}`, body),
  deleteGoal: (id) => API.delete(`/api/goals/${id}`),
  budgets: () => API.get('/api/budgets'),
  upsertBudget: (body) => API.post('/api/budgets', body),
  deleteBudget: (id) => API.delete(`/api/budgets/${id}`),
  income: () => API.get('/api/income'),
  updateIncome: (body) => API.put('/api/income', body),
  aiChat: (body) => API.post('/api/ai/chat', body),
  aiAnalysis: () => API.post('/api/ai/analysis', {}),
  aiHistory: () => API.get('/api/ai/history'),
  aiClearHistory: () => API.delete('/api/ai/history'),
};
