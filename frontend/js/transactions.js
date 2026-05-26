let txnTypeFilter = '';
let txnEditData = null;
let txnSearchTimeout = null;

function loadTransactions() {
  const monthInput = document.getElementById('txn-month-filter');
  if (!monthInput.value) monthInput.value = currentMonth();
  fetchTxns();

  monthInput.addEventListener('change', fetchTxns);

  document.querySelectorAll('.toggle-tab[data-type]').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.toggle-tab[data-type]').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      txnTypeFilter = tab.dataset.type;
      fetchTxns();
    });
  });

  document.getElementById('txn-search').addEventListener('input', () => {
    clearTimeout(txnSearchTimeout);
    txnSearchTimeout = setTimeout(fetchTxns, 350);
  });
}

async function fetchTxns() {
  const params = {};
  const month = document.getElementById('txn-month-filter')?.value;
  if (month) params.month = month;
  if (txnTypeFilter) params.type = txnTypeFilter;
  const search = document.getElementById('txn-search')?.value;
  if (search) params.search = search;
  params.page_size = 100;

  try {
    const data = await API.transactions(params);
    renderTxnList(data.items);
  } catch (e) {
    console.error('Txn error', e);
  }
}

function renderTxnList(items) {
  const el = document.getElementById('txn-list');
  if (!items || !items.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div>暂无记录</div>';
    return;
  }

  const grouped = {};
  items.forEach(t => {
    if (!grouped[t.date]) grouped[t.date] = [];
    grouped[t.date].push(t);
  });

  el.innerHTML = Object.entries(grouped)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, txns]) => `
      <div class="txn-group-date">${date}</div>
      <div class="card" style="padding:0 16px;">
        ${txns.map(t => `
          <div class="txn-item" onclick="openEditTxn(${t.id})">
            <div class="txn-icon">${t.category_icon || '📦'}</div>
            <div class="txn-info">
              <div class="txn-name">${t.merchant || t.description || '未知'}</div>
              <div class="txn-sub">${t.category_name || '未分类'}${t.description ? ' · ' + t.description : ''}</div>
            </div>
            <div class="txn-amount ${t.type}">${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}</div>
          </div>`).join('')}
      </div>`).join('');
}

function openAddTxn() {
  txnEditData = null;
  document.getElementById('txn-edit-id').value = '';
  document.getElementById('modal-txn-title').textContent = '新增交易';
  document.getElementById('txn-amount').value = '';
  document.getElementById('txn-merchant').value = '';
  document.getElementById('txn-desc').value = '';
  document.getElementById('txn-date').value = today();
  document.getElementById('txn-delete-row').classList.add('hidden');
  setTxnType('expense');
  populateCategorySelect('txn-category');
  populateAccountSelect('txn-account');
  openModal('modal-txn');
}

async function openEditTxn(id) {
  try {
    const data = await API.transactions({ page_size: 200 });
    const t = data.items.find(i => i.id === id);
    if (!t) return;
    txnEditData = t;
    document.getElementById('txn-edit-id').value = t.id;
    document.getElementById('modal-txn-title').textContent = '编辑交易';
    document.getElementById('txn-amount').value = t.amount;
    document.getElementById('txn-merchant').value = t.merchant || '';
    document.getElementById('txn-desc').value = t.description || '';
    document.getElementById('txn-date').value = t.date;
    document.getElementById('txn-delete-row').classList.remove('hidden');
    setTxnType(t.type);
    populateCategorySelect('txn-category');
    populateAccountSelect('txn-account');
    if (t.category_id) document.getElementById('txn-category').value = t.category_id;
    if (t.account_id) document.getElementById('txn-account').value = t.account_id;
    openModal('modal-txn');
  } catch (e) { console.error(e); }
}

function setTxnType(type) {
  document.querySelectorAll('[data-txntype]').forEach(t => {
    t.classList.toggle('active', t.dataset.txntype === type);
  });
}

function getSelectedTxnType() {
  return document.querySelector('[data-txntype].active')?.dataset.txntype || 'expense';
}

async function saveTxn() {
  const id = document.getElementById('txn-edit-id').value;
  const body = {
    amount: parseFloat(document.getElementById('txn-amount').value) || 0,
    type: getSelectedTxnType(),
    date: document.getElementById('txn-date').value,
    merchant: document.getElementById('txn-merchant').value,
    description: document.getElementById('txn-desc').value,
    category_id: parseInt(document.getElementById('txn-category').value) || null,
    account_id: parseInt(document.getElementById('txn-account').value) || null,
  };
  if (!body.amount || !body.date) return alert('请填写金额和日期');
  try {
    if (id) {
      await API.updateTxn(id, body);
    } else {
      await API.createTxn(body);
    }
    closeModal('modal-txn');
    fetchTxns();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (e) { alert(e.message); }
}

async function deleteTxn() {
  const id = document.getElementById('txn-edit-id').value;
  if (!id || !confirm('确认删除这条交易记录？')) return;
  try {
    await API.deleteTxn(id);
    closeModal('modal-txn');
    fetchTxns();
    if (currentPage === 'dashboard') loadDashboard();
  } catch (e) { alert(e.message); }
}
