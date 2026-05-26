let pieChart = null;

async function loadDashboard() {
  const month = currentMonth();
  document.getElementById('dashboard-month').textContent = month.replace('-', ' 年 ') + ' 月';
  try {
    const data = await API.dashboard(month);
    document.getElementById('db-balance').textContent = fmt(data.balance);
    document.getElementById('db-income').textContent = fmt(data.total_income);
    document.getElementById('db-expense').textContent = fmt(data.total_expense);
    renderPieChart(data.category_breakdown);
    renderBudgetProgress(data.budget_progress);
    renderRecentTxns(data.recent_transactions);
  } catch (e) {
    console.error('Dashboard error', e);
  }
}

function renderPieChart(breakdown) {
  const ctx = document.getElementById('pie-chart').getContext('2d');
  if (pieChart) { pieChart.destroy(); pieChart = null; }
  if (!breakdown || !breakdown.length) return;

  const COLORS = ['#6C63FF','#22C55E','#F59E0B','#EF4444','#3B82F6','#EC4899','#8B5CF6','#14B8A6','#F97316','#64748B'];
  pieChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: breakdown.map(b => b.icon + ' ' + b.name),
      datasets: [{
        data: breakdown.map(b => b.amount),
        backgroundColor: COLORS.slice(0, breakdown.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      cutout: '60%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 12 } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ¥${ctx.raw.toLocaleString('zh-CN', {minimumFractionDigits:2})}`,
          },
        },
      },
    },
  });
}

function renderBudgetProgress(budgets) {
  const el = document.getElementById('db-budgets');
  if (!budgets || !budgets.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📊</div>暂无预算</div>';
    return;
  }
  el.innerHTML = budgets.map(b => {
    const cls = b.percent >= 100 ? 'over' : b.percent >= 80 ? 'warn' : '';
    return `
      <div class="progress-wrap">
        <div class="progress-label">
          <span>${b.icon} ${b.name}</span>
          <span class="pct">${fmt(b.spent)} / ${fmt(b.limit)} (${b.percent}%)</span>
        </div>
        <div class="progress-track"><div class="progress-fill ${cls}" style="width:${Math.min(b.percent,100)}%"></div></div>
      </div>`;
  }).join('<div style="margin-top:14px"></div>');
}

function renderRecentTxns(txns) {
  const el = document.getElementById('db-recent');
  if (!txns || !txns.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div>暂无交易记录</div>';
    return;
  }
  el.innerHTML = txns.map(t => `
    <div class="txn-item" onclick="openEditTxn(${t.id})">
      <div class="txn-icon">${t.category_icon || '📦'}</div>
      <div class="txn-info">
        <div class="txn-name">${t.merchant || t.description || '未知'}</div>
        <div class="txn-sub">${t.category_name || '未分类'} · ${t.date}</div>
      </div>
      <div class="txn-amount ${t.type}">${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}</div>
    </div>`).join('');
}
