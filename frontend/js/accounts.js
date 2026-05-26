const ACCOUNT_ICONS = { bank: '🏦', alipay: '💙', wechat: '💚', cash: '💵' };

async function loadAccounts() {
  try {
    const data = await API.accounts();
    accounts = data;
    const total = data.reduce((s, a) => s + a.balance, 0);
    const el = document.getElementById('accounts-total');
    if (el) el.textContent = fmt(total);
    renderAccountsList(data);
  } catch (e) { console.error(e); }
}

function renderAccountsList(accs) {
  const el = document.getElementById('accounts-list');
  if (!accs || !accs.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">💳</div>暂无账户</div>';
    return;
  }
  el.innerHTML = accs.map(a => `
    <div class="card flex-between" style="margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:12px">
        <div style="font-size:28px">${ACCOUNT_ICONS[a.type] || '💳'}</div>
        <div>
          <div style="font-weight:700">${a.name}</div>
          <div class="text-sm text-muted">${a.type}</div>
        </div>
      </div>
      <div style="font-size:18px;font-weight:700">${fmt(a.balance)}</div>
    </div>`).join('');
}

function openAccountModal() {
  document.getElementById('account-name').value = '';
  document.getElementById('account-balance').value = '';
  openModal('modal-account');
}

async function saveAccount() {
  const body = {
    name: document.getElementById('account-name').value,
    type: document.getElementById('account-type').value,
    balance: parseFloat(document.getElementById('account-balance').value) || 0,
  };
  if (!body.name) return alert('请填写账户名称');
  try {
    await API.createAccount(body);
    closeModal('modal-account');
    loadAccounts();
  } catch (e) { alert(e.message); }
}
