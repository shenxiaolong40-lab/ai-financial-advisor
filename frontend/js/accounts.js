const ACCOUNT_ICONS = { bank: '🏦', alipay: '💙', wechat: '💚', cash: '💵' };
let importFile = null;

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
    showToast('账户已添加');
  } catch (e) { alert(e.message); }
}

// ── 账单导入 ──────────────────────────────────────────────────────────────

function openImportModal(source) {
  importFile = null;
  document.getElementById('import-source').value = source;
  document.getElementById('import-modal-title').textContent =
    source === 'alipay' ? '💙 导入支付宝账单' : '💚 导入微信账单';
  document.getElementById('import-drop-icon').textContent = '📂';
  document.getElementById('import-drop-label').textContent = '点击或拖拽上传 CSV 文件';
  document.getElementById('import-drop-zone').className = 'import-drop-zone';
  document.getElementById('import-preview').classList.add('hidden');
  document.getElementById('import-result').classList.add('hidden');
  document.getElementById('btn-do-import').disabled = true;
  document.getElementById('import-file-input').value = '';

  // populate account selector
  const sel = document.getElementById('import-account');
  sel.innerHTML = '<option value="">不关联账户</option>';
  accounts.forEach(a => {
    if ((source === 'alipay' && a.type === 'alipay') ||
        (source === 'wechat' && a.type === 'wechat')) {
      sel.insertAdjacentHTML('beforeend', `<option value="${a.id}" selected>${a.name}</option>`);
    } else {
      sel.insertAdjacentHTML('beforeend', `<option value="${a.id}">${a.name}</option>`);
    }
  });

  // drag and drop
  const dz = document.getElementById('import-drop-zone');
  dz.ondragover = e => { e.preventDefault(); dz.classList.add('drag-over'); };
  dz.ondragleave = () => dz.classList.remove('drag-over');
  dz.ondrop = e => {
    e.preventDefault();
    dz.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) setImportFile(f);
  };

  openModal('modal-import');
}

function onImportFileSelect(e) {
  const f = e.target.files[0];
  if (f) setImportFile(f);
}

function setImportFile(file) {
  importFile = file;
  const dz = document.getElementById('import-drop-zone');
  dz.className = 'import-drop-zone has-file';
  document.getElementById('import-drop-icon').textContent = '✅';
  document.getElementById('import-drop-label').textContent = file.name;

  // preview file size and name
  const kb = (file.size / 1024).toFixed(1);
  const preview = document.getElementById('import-preview');
  const box = document.getElementById('import-preview-box');
  preview.classList.remove('hidden');
  box.innerHTML = `
    <div>📄 文件名：<strong>${file.name}</strong></div>
    <div>📦 文件大小：${kb} KB</div>
    <div style="margin-top:6px;color:var(--text-3)">确认后点击「开始导入」，系统会自动去重</div>
  `;

  document.getElementById('import-result').classList.add('hidden');
  document.getElementById('btn-do-import').disabled = false;
}

async function doImport() {
  if (!importFile) return;
  const source = document.getElementById('import-source').value;
  const accountId = document.getElementById('import-account').value;

  const btn = document.getElementById('btn-do-import');
  btn.disabled = true;
  btn.textContent = '导入中…';

  const formData = new FormData();
  formData.append('file', importFile);
  if (accountId) formData.append('account_id', accountId);

  try {
    const resp = await fetch(`http://localhost:8000/api/import/${source}`, {
      method: 'POST',
      body: formData,
    });
    const data = await resp.json();

    const resultEl = document.getElementById('import-result');
    const resultBox = document.getElementById('import-result-box');
    resultEl.classList.remove('hidden');

    if (!resp.ok) {
      resultBox.className = 'import-result-box error';
      resultBox.textContent = data.detail || '导入失败';
    } else {
      resultBox.className = 'import-result-box success';
      resultBox.innerHTML = `
        ✅ 导入完成！<br>
        新增 <strong>${data.inserted}</strong> 条 · 跳过重复 <strong>${data.skipped}</strong> 条 · 共解析 <strong>${data.total}</strong> 条
      `;
      showToast(`成功导入 ${data.inserted} 条账单`);
      // reload transactions if visible
      if (currentPage === 'transactions') fetchTxns();
      if (currentPage === 'dashboard') loadDashboard();
    }
  } catch (e) {
    const resultEl = document.getElementById('import-result');
    const resultBox = document.getElementById('import-result-box');
    resultEl.classList.remove('hidden');
    resultBox.className = 'import-result-box error';
    resultBox.textContent = `请求失败：${e.message}`;
  }

  btn.disabled = false;
  btn.textContent = '开始导入';
}
