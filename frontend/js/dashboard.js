let pieChart = null;
let trendChart = null;
let dashboardMonth = currentMonth();
let dashboardData = null;
let activePieTab = 'expense';

const CHART_COLORS = ['#6C63FF','#22C55E','#F59E0B','#EF4444','#3B82F6','#EC4899','#8B5CF6','#14B8A6','#F97316','#64748B'];

function dashboardPrevMonth() {
  const [y, m] = dashboardMonth.split('-').map(Number);
  const d = new Date(y, m - 2, 1);
  dashboardMonth = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  loadDashboard();
}

function dashboardNextMonth() {
  const [y, m] = dashboardMonth.split('-').map(Number);
  const d = new Date(y, m, 1);
  const next = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  if (next > currentMonth()) return;
  dashboardMonth = next;
  loadDashboard();
}

function switchPieTab(tab) {
  activePieTab = tab;
  document.getElementById('pie-tab-expense').classList.toggle('active', tab === 'expense');
  document.getElementById('pie-tab-income').classList.toggle('active', tab === 'income');
  if (dashboardData) renderPieAndList(dashboardData);
}

async function loadDashboard() {
  document.getElementById('dashboard-month-label').textContent = dashboardMonth;

  try {
    const [data, trend] = await Promise.all([
      API.dashboard(dashboardMonth),
      API.trend(6),
    ]);
    dashboardData = data;

    // Summary
    document.getElementById('db-balance').textContent = fmt(data.balance);
    document.getElementById('db-income').textContent = fmt(data.total_income);
    document.getElementById('db-expense').textContent = fmt(data.total_expense);
    document.getElementById('db-income-sub').textContent =
      `收入 ${fmt(data.total_income)} · 支出 ${fmt(data.total_expense)}`;

    renderTrendChart(trend);
    renderPieAndList(data);
    renderBudgetProgress(data.budget_progress);
    renderGoalsSnapshot(data.goals_snapshot);
    renderRecentTxns(data.recent_transactions);
  } catch (e) {
    console.error('Dashboard error', e);
  }
}

function renderTrendChart(trend) {
  const ctx = document.getElementById('trend-chart').getContext('2d');
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  if (!trend || !trend.length) return;

  const labels = trend.map(t => t.month.slice(5) + '月');
  trendChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: '收入',
          data: trend.map(t => t.income),
          backgroundColor: 'rgba(34,197,94,0.7)',
          borderRadius: 5,
        },
        {
          label: '支出',
          data: trend.map(t => t.expense),
          backgroundColor: 'rgba(108,99,255,0.7)',
          borderRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ¥${ctx.raw.toLocaleString('zh-CN', { minimumFractionDigits: 0 })}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          grid: { color: 'rgba(0,0,0,0.04)' },
          ticks: {
            font: { size: 10 },
            callback: v => '¥' + (v >= 10000 ? (v / 10000).toFixed(0) + 'w' : v),
          },
        },
      },
    },
  });
}

function renderPieAndList(data) {
  const isExpense = activePieTab === 'expense';
  const breakdown = isExpense ? data.category_breakdown : buildIncomeBreakdown(data);
  const total = isExpense ? data.total_expense : data.total_income;

  renderPieChart(breakdown);
  renderCategoryList(breakdown, total);
}

function buildIncomeBreakdown(data) {
  // income doesn't have category breakdown from backend, show placeholder
  if (data.total_income === 0) return [];
  return [{ name: '收入', icon: '💼', amount: data.total_income }];
}

function renderPieChart(breakdown) {
  const ctx = document.getElementById('pie-chart').getContext('2d');
  if (pieChart) { pieChart.destroy(); pieChart = null; }
  if (!breakdown || !breakdown.length) return;

  pieChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: breakdown.map(b => b.icon + ' ' + b.name),
      datasets: [{
        data: breakdown.map(b => b.amount),
        backgroundColor: CHART_COLORS.slice(0, breakdown.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      cutout: '65%',
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ¥${ctx.raw.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`,
          },
        },
      },
    },
  });
}

function renderCategoryList(breakdown, total) {
  const el = document.getElementById('category-list');
  if (!breakdown || !breakdown.length) { el.innerHTML = ''; return; }

  el.innerHTML = breakdown.map((b, i) => {
    const pct = total > 0 ? (b.amount / total * 100).toFixed(1) : 0;
    const color = CHART_COLORS[i % CHART_COLORS.length];
    return `
      <div class="cat-row">
        <span style="font-size:20px;width:28px;text-align:center">${b.icon}</span>
        <div class="cat-bar-wrap">
          <div class="cat-bar-label">
            <span style="font-weight:600">${b.name}</span>
            <span style="color:var(--text-2)">${fmt(b.amount)} <span style="color:var(--text-3);font-size:11px">${pct}%</span></span>
          </div>
          <div class="cat-bar-track">
            <div class="cat-bar-fill" style="width:${pct}%;background:${color}"></div>
          </div>
        </div>
      </div>`;
  }).join('');
}

function renderBudgetProgress(budgets) {
  const el = document.getElementById('db-budgets');
  if (!budgets || !budgets.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div>暂无预算 <span class="section-link" onclick="navigate(\'goals\')" style="display:block;margin-top:8px">去设置 →</span></div>';
    return;
  }
  el.innerHTML = budgets.map(b => {
    const cls = b.percent >= 100 ? 'over' : b.percent >= 80 ? 'warn' : '';
    const statusText = b.percent >= 100
      ? `<span style="color:var(--danger);font-size:11px;font-weight:600">已超支 ${fmt(b.spent - b.limit)}</span>`
      : `<span style="color:var(--text-3);font-size:11px">剩余 ${fmt(b.limit - b.spent)}</span>`;
    return `
      <div class="progress-wrap" style="margin-bottom:14px">
        <div class="progress-label">
          <span style="font-weight:600">${b.icon} ${b.name}</span>
          ${statusText}
        </div>
        <div class="progress-track" style="height:10px">
          <div class="progress-fill ${cls}" style="width:${Math.min(b.percent,100)}%"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;font-size:11px;color:var(--text-3)">
          <span>${fmt(b.spent)} 已用</span>
          <span>上限 ${fmt(b.limit)}</span>
        </div>
      </div>`;
  }).join('');
}

function renderGoalsSnapshot(goals) {
  const el = document.getElementById('db-goals');
  if (!goals || !goals.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div>暂无目标</div>';
    return;
  }
  el.innerHTML = goals.map(g => {
    const daysLeft = g.deadline
      ? Math.ceil((new Date(g.deadline) - new Date()) / 86400000)
      : null;
    const deadlineLabel = daysLeft !== null
      ? (daysLeft > 0 ? `还有 ${daysLeft} 天` : `已过期`)
      : '';
    const pct = g.percent;
    const cls = pct >= 100 ? '' : pct >= 60 ? '' : 'warn';
    return `
      <div style="margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;margin-bottom:5px">
          <span style="font-weight:600">${g.name}</span>
          <span style="font-size:12px;color:var(--text-3)">${deadlineLabel}</span>
        </div>
        <div class="progress-track" style="height:10px">
          <div class="progress-fill ${cls}" style="width:${Math.min(pct,100)}%"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:3px;font-size:11px;color:var(--text-3)">
          <span>已存 ${fmt(g.current)}</span>
          <span>目标 ${fmt(g.target)} · ${pct}%</span>
        </div>
      </div>`;
  }).join('');
}

function renderRecentTxns(txns) {
  const el = document.getElementById('db-recent');
  if (!txns || !txns.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div>暂无交易记录</div>';
    return;
  }
  el.innerHTML = txns.map(t => `
    <div class="txn-item" onclick="navigate('transactions')">
      <div class="txn-icon">${t.category_icon || '📦'}</div>
      <div class="txn-info">
        <div class="txn-name">${t.merchant || t.description || '未知'}</div>
        <div class="txn-sub">${t.category_name || '未分类'} · ${t.date}</div>
      </div>
      <div class="txn-amount ${t.type}">${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}</div>
    </div>`).join('');
}
