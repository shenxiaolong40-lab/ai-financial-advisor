async function loadGoals() {
  await loadSharedData();
  const [income, goals, budgets] = await Promise.all([
    API.income(), API.goals(), API.budgets(),
  ]).catch(() => [null, [], []]);

  if (income) {
    document.getElementById('income-monthly').value = income.monthly_income || '';
    document.getElementById('income-extra').value = income.monthly_extra || '';
  }

  renderGoalsList(goals || []);
  renderBudgetsList(budgets || []);
}

async function saveIncome() {
  const monthly_income = parseFloat(document.getElementById('income-monthly').value) || 0;
  const monthly_extra = parseFloat(document.getElementById('income-extra').value) || 0;
  try {
    await API.updateIncome({ monthly_income, monthly_extra });
    alert('保存成功');
  } catch (e) { alert(e.message); }
}

function renderGoalsList(goals) {
  const el = document.getElementById('goals-list');
  if (!goals.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div>暂无储蓄目标</div>';
    return;
  }
  el.innerHTML = goals.map(g => {
    const pct = g.target_amount > 0 ? Math.min(g.current_amount / g.target_amount * 100, 100) : 0;
    const deadlineStr = g.deadline ? ` · 截止 ${g.deadline}` : '';
    return `
      <div class="card" style="margin-bottom:12px">
        <div class="flex-between">
          <span style="font-weight:700">${g.name}</span>
          <button class="btn btn-outline btn-sm" onclick="openGoalModal(${g.id})">编辑</button>
        </div>
        <div class="progress-wrap mt-8">
          <div class="progress-label">
            <span>${fmt(g.current_amount)} / ${fmt(g.target_amount)}${deadlineStr}</span>
            <span class="pct">${pct.toFixed(1)}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width:${pct}%"></div>
          </div>
        </div>
      </div>`;
  }).join('');
}

function renderBudgetsList(budgets) {
  const el = document.getElementById('budgets-list');
  if (!budgets.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">💰</div>暂无预算</div>';
    return;
  }
  el.innerHTML = budgets.map(b => {
    const catName = b.category_id
      ? (categories.find(c => c.id === b.category_id)?.name || '未知')
      : '总预算';
    const periodLabel = b.period === 'monthly' ? '每月' : '每周';
    return `
      <div class="card flex-between" style="margin-bottom:10px">
        <div>
          <div style="font-weight:700">${catName}</div>
          <div class="text-sm text-muted">${periodLabel} · 上限 ${fmt(b.limit_amount)}</div>
        </div>
        <button class="btn btn-outline btn-sm text-danger" onclick="removeBudget(${b.id})">删除</button>
      </div>`;
  }).join('');
}

function openGoalModal(id) {
  document.getElementById('goal-edit-id').value = id || '';
  if (!id) {
    document.getElementById('goal-name').value = '';
    document.getElementById('goal-target').value = '';
    document.getElementById('goal-current').value = '';
    document.getElementById('goal-deadline').value = '';
  } else {
    API.goals().then(goals => {
      const g = goals.find(x => x.id === id);
      if (!g) return;
      document.getElementById('goal-name').value = g.name;
      document.getElementById('goal-target').value = g.target_amount;
      document.getElementById('goal-current').value = g.current_amount;
      document.getElementById('goal-deadline').value = g.deadline || '';
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
  } catch (e) { alert(e.message); }
}

async function removeBudget(id) {
  if (!confirm('确认删除此预算？')) return;
  try {
    await API.deleteBudget(id);
    loadGoals();
  } catch (e) { alert(e.message); }
}
