// 主应用逻辑 — 3页导航

let currentPage = '';
let _categories = null;

// ── 导航 ──────────────────────────────────────────────────────────────────────
function navigate(page) {
  const pages = ['fire', 'transactions', 'ai'];
  if (!pages.includes(page)) page = 'fire';

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  currentPage = page;
  location.hash = page;

  if (page === 'fire')         loadFireDashboard();
  if (page === 'transactions') loadTransactions();
  if (page === 'ai')           loadAI();
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '—';
  return '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 2800);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (!m) return;
  m.style.display = 'flex';
  requestAnimationFrame(() => m.classList.add('open'));
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (!m) return;
  m.classList.remove('open');
  setTimeout(() => { m.style.display = 'none'; }, 280);
}

async function getCategories() {
  if (_categories) return _categories;
  _categories = await API.categories();
  return _categories;
}

// ── 认证 ──────────────────────────────────────────────────────────────────────
window._showLogin = () => openModal('modal-login');

function initAuth() {
  document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
      document.getElementById(`form-${tab.dataset.tab}`)?.classList.add('active');
    });
  });

  document.getElementById('btn-login')?.addEventListener('click', async () => {
    const email = document.getElementById('login-email').value.trim();
    const pw = document.getElementById('login-pw').value;
    try {
      const r = await API.authLogin({ email, password: pw });
      Auth.setToken(r.access_token);
      closeModal('modal-login');
      navigate('fire');
      toast('登录成功');
    } catch (e) { toast(e.message, 'error'); }
  });

  document.getElementById('btn-register')?.addEventListener('click', async () => {
    const email = document.getElementById('reg-email').value.trim();
    const pw = document.getElementById('reg-pw').value;
    try {
      const r = await API.authRegister({ email, password: pw });
      Auth.setToken(r.access_token);
      closeModal('modal-login');
      navigate('fire');
      toast('注册成功');
    } catch (e) { toast(e.message, 'error'); }
  });

  document.getElementById('btn-logout')?.addEventListener('click', () => {
    Auth.clear();
    toast('已退出');
    navigate('fire');
  });
}

// ── 模态框 ────────────────────────────────────────────────────────────────────
function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const overlay = btn.closest('.modal-overlay');
      if (overlay) closeModal(overlay.id);
    });
  });
}

// ── 启动 ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initAuth();
  initModals();

  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => navigate(item.dataset.page));
  });

  const hash = location.hash.replace('#', '');
  navigate(['fire', 'transactions', 'ai'].includes(hash) ? hash : 'fire');
});
