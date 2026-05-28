// 收支记录页

let txnMonth = '';
let txnFilter = '';
let txnCats = [];

async function loadTransactions() {
  if (!txnMonth) txnMonth = currentMonth();
  txnCats = await getCategories();
  renderMonthNav();
  await refreshTransactions();
}

function renderMonthNav() {
  document.getElementById('txn-month-label').textContent = txnMonth;
}

async function refreshTransactions() {
  const params = { month: txnMonth, page_size: 100 };
  if (txnFilter) params.type = txnFilter;
  const search = document.getElementById('txn-search')?.value.trim();
  if (search) params.search = search;

  try {
    const data = await API.transactions(params);
    renderTxnStats(data.items);
    renderTxnList(data.items);
  } catch (e) { toast(e.message, 'error'); }
}

function renderTxnStats(items) {
  const income  = items.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0);
  const expense = items.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
  document.getElementById('txn-income-total').textContent  = fmt(income);
  document.getElementById('txn-expense-total').textContent = fmt(expense);
  document.getElementById('txn-balance').textContent       = fmt(income - expense);
}

function renderTxnList(items) {
  const container = document.getElementById('txn-list');
  if (!items.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div><p>本月暂无记录</p></div>';
    return;
  }

  const groups = {};
  items.forEach(t => {
    if (!groups[t.date]) groups[t.date] = [];
    groups[t.date].push(t);
  });

  container.innerHTML = Object.keys(groups).sort((a, b) => b.localeCompare(a)).map(date => `
    <div class="txn-date-group">
      <div class="txn-date-label">${formatDate(date)}</div>
      ${groups[date].map(t => `
        <div class="txn-item" data-id="${t.id}">
          <div class="txn-icon">${t.category_icon || (t.type === 'income' ? '💰' : '💸')}</div>
          <div class="txn-info">
            <div class="txn-title">${t.merchant || t.description || t.category_name || '未分类'}</div>
            ${t.category_name ? `<div class="txn-sub">${t.category_name}</div>` : ''}
          </div>
          <div class="txn-amount ${t.type}">
            ${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}
          </div>
          <button class="btn-icon txn-delete" data-id="${t.id}">×</button>
        </div>
      `).join('')}
    </div>
  `).join('');

  container.querySelectorAll('.txn-delete').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('确认删除？')) return;
      try {
        await API.deleteTxn(btn.dataset.id);
        toast('已删除');
        refreshTransactions();
        loadFireDashboard();
      } catch (err) { toast(err.message, 'error'); }
    });
  });

  container.querySelectorAll('.txn-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('txn-delete')) return;
      openEditTxn(item.dataset.id, items);
    });
  });
}

function formatDate(d) {
  const today = new Date().toISOString().slice(0, 10);
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  if (d === today) return '今天';
  if (d === yesterday) return '昨天';
  const dt = new Date(d);
  return `${dt.getMonth() + 1}月${dt.getDate()}日`;
}

function openAddTxn() {
  document.getElementById('txn-form').reset();
  document.getElementById('txn-id').value   = '';
  document.getElementById('txn-date').value = new Date().toISOString().slice(0, 10);
  document.getElementById('modal-txn-title').textContent = '添加记录';
  populateCategorySelect(null);
  openModal('modal-txn');
}

function openEditTxn(id, items) {
  const t = items.find(x => x.id == id);
  if (!t) return;
  document.getElementById('txn-id').value          = t.id;
  document.getElementById('txn-type').value        = t.type;
  document.getElementById('txn-amount').value      = t.amount;
  document.getElementById('txn-date').value        = t.date;
  document.getElementById('txn-merchant').value    = t.merchant || '';
  document.getElementById('txn-description').value = t.description || '';
  document.getElementById('modal-txn-title').textContent = '编辑记录';
  populateCategorySelect(t.category_id);
  openModal('modal-txn');
}

function populateCategorySelect(selected) {
  const sel = document.getElementById('txn-category');
  sel.innerHTML = '<option value="">— 选择分类 —</option>' +
    txnCats.map(c => `<option value="${c.id}" ${c.id == selected ? 'selected' : ''}>${c.icon} ${c.name}</option>`).join('');
}

async function saveTxn() {
  const id = document.getElementById('txn-id').value;
  const body = {
    type:        document.getElementById('txn-type').value,
    amount:      parseFloat(document.getElementById('txn-amount').value),
    date:        document.getElementById('txn-date').value,
    merchant:    document.getElementById('txn-merchant').value.trim(),
    description: document.getElementById('txn-description').value.trim(),
    category_id: parseInt(document.getElementById('txn-category').value) || null,
  };
  if (!body.amount || !body.date) { toast('请填写金额和日期', 'error'); return; }
  try {
    if (id) { await API.updateTxn(id, body); toast('已更新'); }
    else     { await API.createTxn(body);     toast('已添加'); }
    closeModal('modal-txn');
    refreshTransactions();
    loadFireDashboard();
  } catch (e) { toast(e.message, 'error'); }
}

async function doImport(source) {
  const file = document.getElementById('import-file').files[0];
  if (!file) { toast('请先选择文件', 'error'); return; }
  const resultEl = document.getElementById('import-result');
  resultEl.textContent = '导入中...';
  resultEl.className = 'import-result';
  try {
    const r = await API.importBill(source, file);
    resultEl.textContent = r.message;
    resultEl.className = 'import-result success';
    refreshTransactions();
    loadFireDashboard();
  } catch (e) {
    resultEl.textContent = e.message;
    resultEl.className = 'import-result error';
  }
}

function prevMonth() {
  const [y, m] = txnMonth.split('-').map(Number);
  txnMonth = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`;
  renderMonthNav(); refreshTransactions();
}

function nextMonth() {
  const [y, m] = txnMonth.split('-').map(Number);
  txnMonth = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`;
  renderMonthNav(); refreshTransactions();
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-prev-month')?.addEventListener('click', prevMonth);
  document.getElementById('btn-next-month')?.addEventListener('click', nextMonth);
  document.getElementById('btn-add-txn')?.addEventListener('click', openAddTxn);
  document.getElementById('btn-save-txn')?.addEventListener('click', saveTxn);

  document.getElementById('btn-import-alipay')?.addEventListener('click', () => doImport('alipay'));
  document.getElementById('btn-import-wechat')?.addEventListener('click', () => doImport('wechat'));

  document.querySelectorAll('.txn-type-filter').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.txn-type-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      txnFilter = btn.dataset.filter;
      refreshTransactions();
    });
  });

  document.getElementById('txn-search')?.addEventListener('input', () => refreshTransactions());
});
