async function loadGoals() {
  await loadSharedData();
  const [income, goals, budgets, summary] = await Promise.all([
    API.income(), API.goals(), API.budgets(),
    API.dashboard(currentMonth()),
  ]).catch(() => [null, [], [], null]);

  if (income) {
    document.getElementById('income-monthly').value = income.monthly_income || '';
    document.getElementById('income-extra').value = income.monthly_extra || '';
  }

  renderGoalsList(goals || []);
  renderBudgetsList(budgets || [], summary);
}

async function saveIncome() {
  const monthly_income = parseFloat(document.getElementById('income-monthly').value) || 0;
  const monthly_extra = parseFloat(document.getElementById('income-extra').value) || 0;
  try {
    await API.updateIncome({ monthly_income, monthly_extra });
    showToast('收入设置已保存');
  } catch (e) { alert(e.message); }
}

function renderGoalsList(goals) {
  const el = document.getElementById('goals-list');
  if (!goals.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div>暂无储蓄目标，点击右上角新增</div>';
    return;
  }

  el.innerHTML = goals.map(g => {
    const pct = g.target_amount > 0 ? Math.min(g.current_amount / g.target_amount * 100, 100) : 0;
    const remaining = g.target_amount - g.current_amount;
    let deadlineInfo = '';
    if (g.deadline) {
      const daysLeft = Math.ceil((new Date(g.deadline) - new Date()) / 86400000);
      if (daysLeft > 0) {
        const monthsLeft = Math.ceil(daysLeft / 30);
        const monthlyNeeded = monthsLeft > 0 ? remaining / monthsLeft : remaining;
        deadlineInfo = `截止 ${g.deadline} · 每月需存 ${fmt(monthlyNeeded)}`;
      } else {
        deadlineInfo = `已过截止日期`;
      }
    }

    return `
      <div class="goal-card">
        <div class="goal-card-header">
          <div>
            <div class="goal-card-name">🎯 ${g.name}</div>
            ${deadlineInfo ? `<div class="goal-card-deadline">${deadlineInfo}</div>` : ''}
          </div>
          <button class="btn btn-outline btn-sm" onclick="openGoalModal(${g.id})">编辑</button>
        </div>
        <div class="progress-track" style="height:12px">
          <div class="progress-fill" style="width:${pct.toFixed(1)}%;background:${pct >= 100 ? 'var(--success)' : 'var(--primary)'}"></div>
        </div>
        <div class="goal-amount-row">
          <span>已存 <strong>${fmt(g.current_amount)}</strong></span>
          <span style="font-size:18px;font-weight:700;color:var(--primary)">${pct.toFixed(0)}%</span>
          <span>目标 <strong>${fmt(g.target_amount)}</strong></span>
        </div>
        ${remaining > 0 ? `<div style="margin-top:8px;font-size:12px;color:var(--text-3);text-align:center">还差 ${fmt(remaining)}</div>` : `<div style="margin-top:8px;font-size:12px;color:var(--success);text-align:center;font-weight:600">🎉 目标已达成！</div>`}
      </div>`;
  }).join('');
}

function renderBudgetsList(budgets, summary) {
  const el = document.getElementById('budgets-list');
  if (!budgets.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">💰</div>暂无预算，点击右上角新增</div>';
    return;
  }

  // build spent map from summary
  const spentMap = {};
  if (summary) {
    summary.budget_progress?.forEach(b => { spentMap[b.id] = b.spent; });
  }

  el.innerHTML = budgets.map(b => {
    const catName = b.category_id
      ? (categories.find(c => c.id === b.category_id)?.name || '未知')
      : '总预算';
    const catIcon = b.category_id
      ? (categories.find(c => c.id === b.category_id)?.icon || '📦')
      : '💰';
    const periodLabel = b.period === 'monthly' ? '每月' : '每周';
    const spent = spentMap[b.id] || 0;
    const pct = b.limit_amount > 0 ? spent / b.limit_amount * 100 : 0;
    const cls = pct >= 100 ? 'over' : pct >= 80 ? 'warn' : '';
    const statusColor = pct >= 100 ? 'var(--danger)' : pct >= 80 ? 'var(--warning)' : 'var(--success)';

    return `
      <div class="budget-card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:8px">
            <span style="font-size:22px">${catIcon}</span>
            <div>
              <div style="font-weight:700">${catName}</div>
              <div style="font-size:12px;color:var(--text-3)">${periodLabel}预算</div>
            </div>
          </div>
          <div style="text-align:right">
            <div style="font-size:16px;font-weight:700;color:${statusColor}">${fmt(spent)}</div>
            <div style="font-size:12px;color:var(--text-3)">/ ${fmt(b.limit_amount)}</div>
          </div>
        </div>
        <div class="progress-track" style="height:8px">
          <div class="progress-fill ${cls}" style="width:${Math.min(pct,100)}%"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:12px;color:var(--text-3)">
          <span>${pct.toFixed(0)}% 已用</span>
          <button class="btn btn-sm" style="padding:2px 8px;font-size:11px;color:var(--danger);background:none;border:none;cursor:pointer" onclick="removeBudget(${b.id})">删除</button>
        </div>
      </div>`;
  }).join('');
}

function openGoalModal(id) {
  document.getElementById('goal-edit-id').value = id || '';
  const deleteRow = document.getElementById('goal-delete-row');
  if (!id) {
    document.getElementById('goal-name').value = '';
    document.getElementById('goal-target').value = '';
    document.getElementById('goal-current').value = '';
    document.getElementById('goal-deadline').value = '';
    deleteRow.classList.add('hidden');
  } else {
    API.goals().then(goals => {
      const g = goals.find(x => x.id === id);
      if (!g) return;
      document.getElementById('goal-name').value = g.name;
      document.getElementById('goal-target').value = g.target_amount;
      document.getElementById('goal-current').value = g.current_amount;
      document.getElementById('goal-deadline').value = g.deadline || '';
      deleteRow.classList.remove('hidden');
    });
  }
  openModal('modal-goal');
}

async function saveGoal() {
  const id = document.getElementById('goal-edit-id').value;
  const body = {
    name: document.getElementById('goal-name').value,
    target_amount: parseFloat(document.getElementById('goal-target').value) || 0,
    current_amount: parseFloat(document.getElementById('goal-current').value) || 0,
    deadline: document.getElementById('goal-deadline').value || null,
  };
  if (!body.name) return alert('请填写目标名称');
  try {
    if (id) {
      await API.updateGoal(id, body);
    } else {
      await API.createGoal(body);
    }
    closeModal('modal-goal');
    loadGoals();
    showToast(id ? '目标已更新' : '目标已创建');
  } catch (e) { alert(e.message); }
}

async function deleteGoal() {
  const id = document.getElementById('goal-edit-id').value;
  if (!id || !confirm('确认删除此目标？')) return;
  try {
    await API.deleteGoal(id);
    closeModal('modal-goal');
    loadGoals();
    showToast('目标已删除');
  } catch (e) { alert(e.message); }
}

function openBudgetModal() {
  populateCategorySelect('budget-category', false);
  document.getElementById('budget-category').insertAdjacentHTML('afterbegin', '<option value="">总预算</option>');
  document.getElementById('budget-limit').value = '';
  openModal('modal-budget');
}

async function saveBudget() {
  const body = {
    category_id: parseInt(document.getElementById('budget-category').value) || null,
    limit_amount: parseFloat(document.getElementById('budget-limit').value) || 0,
    period: document.getElementById('budget-period').value,
  };
  if (!body.limit_amount) return alert('请填写预算上限');
  try {
    await API.upsertBudget(body);
    closeModal('modal-budget');
    loadGoals();
    showToast('预算已保存');
  } catch (e) { alert(e.message); }
}

async function removeBudget(id) {
  if (!confirm('确认删除此预算？')) return;
  try {
    await API.deleteBudget(id);
    loadGoals();
    showToast('预算已删除');
  } catch (e) { alert(e.message); }
}
