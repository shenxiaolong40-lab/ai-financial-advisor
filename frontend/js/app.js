let currentPage = 'dashboard';
let categories = [];
let accounts = [];

function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  currentPage = page;
  location.hash = page;
  onPageActivate(page);
}

function onPageActivate(page) {
  if (page === 'dashboard') loadDashboard();
  if (page === 'transactions') loadTransactions();
  if (page === 'goals') loadGoals();
  if (page === 'ai') loadAI();
  if (page === 'accounts') loadAccounts();
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', () => navigate(item.dataset.page));
});

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function fmt(amount) {
  return '¥' + Number(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function currentMonth() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

async function loadSharedData() {
  try {
    [categories, accounts] = await Promise.all([API.categories(), API.accounts()]);
  } catch (e) {
    console.error('Failed to load shared data', e);
  }
}

function populateCategorySelect(selectId, includeAll = false) {
  const sel = document.getElementById(selectId);
  sel.innerHTML = includeAll ? '<option value="">全部分类</option>' : '';
  categories.forEach(c => {
    if (!c.parent_id) {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.icon + ' ' + c.name;
      sel.appendChild(opt);
    }
  });
}

function populateAccountSelect(selectId) {
  const sel = document.getElementById(selectId);
  sel.innerHTML = '<option value="">不绑定账户</option>';
  accounts.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.id;
    opt.textContent = a.name;
    sel.appendChild(opt);
  });
}

function showToast(msg, type = 'success') {
  const el = document.createElement('div');
  el.style.cssText = `
    position:fixed;bottom:calc(var(--nav-height)+16px);left:50%;transform:translateX(-50%);
    background:${type === 'success' ? '#1A1D2E' : '#EF4444'};color:#fff;
    padding:10px 20px;border-radius:99px;font-size:13px;font-weight:600;
    z-index:9999;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,0.2);
    animation:fadeIn 0.2s ease;
  `;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

// Init
(async () => {
  await loadSharedData();
  const hash = location.hash.replace('#', '') || 'dashboard';
  navigate(['dashboard','transactions','goals','ai','accounts'].includes(hash) ? hash : 'dashboard');
})();
