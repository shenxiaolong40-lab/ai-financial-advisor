// FIRE 仪表盘页

let projectionChart = null;
let expenseChart = null;

async function loadFireDashboard() {
  try {
    const status = await API.fireStatus();
    renderHero(status);
    renderStats(status);
    renderSensitivity(status.sensitivity || [], status.annual_return);
    await renderProjectionChart(status);
    renderAIHint();
  } catch (e) {
    document.getElementById('fire-years').textContent = '—';
    console.error(e);
  }
}

function renderHero(s) {
  const yearsEl    = document.getElementById('fire-years');
  const subtitleEl = document.getElementById('fire-subtitle');
  const progressEl = document.getElementById('fire-progress-bar');
  const labelEl    = document.getElementById('fire-progress-label');

  if (s.already_free) {
    yearsEl.textContent = '🎉';
    yearsEl.style.fontSize = '3rem';
    subtitleEl.textContent = '恭喜！你已实现财务自由';
  } else if (!s.has_data) {
    yearsEl.textContent = '?';
    subtitleEl.textContent = '请先在 ⚙️ 配置中填入资产、工资和支出';
  } else if (s.years_to_fire === null) {
    yearsEl.textContent = '∞';
    yearsEl.style.color = 'var(--danger)';
    subtitleEl.textContent = '按当前参数 100 年内无法达标 — 建议增加收入或降低支出';
  } else {
    yearsEl.textContent = s.years_to_fire;
    const fd = s.fire_detail || {};
    subtitleEl.textContent =
      `被动收入 ${fmt(s.current_passive_income)}/年，覆盖支出 ${s.passive_coverage_pct}%，` +
      `年化收益率 ${s.annual_return}%`;
  }

  // 进度条 = 被动收入覆盖率（最高100%）
  const pct = Math.min(s.passive_coverage_pct || 0, 100);
  progressEl.style.width = pct + '%';
  labelEl.textContent =
    `被动收入 ${fmt(s.current_passive_income)}/年 ÷ 年支出 ${fmt(s.annual_expense)}（${pct.toFixed(1)}%）`;
}

function renderStats(s) {
  const monthly = v => fmt(v / 12);

  // 月工资
  document.getElementById('stat-salary').textContent = monthly(s.annual_salary);
  const salarySubEl = document.getElementById('stat-salary-sub');
  if (salarySubEl) salarySubEl.textContent = `年结余 ${fmt(s.annual_surplus)}`;

  // 月支出
  document.getElementById('stat-expense').textContent = monthly(s.annual_expense);
  const expSubEl = document.getElementById('stat-expense-sub');
  if (expSubEl) expSubEl.textContent = `储蓄率 ${s.savings_rate != null ? s.savings_rate + '%' : '—'}`;

  // 月被动收入
  document.getElementById('stat-passive').textContent = monthly(s.current_passive_income);

  // 被动覆盖率
  const covEl = document.getElementById('stat-coverage');
  covEl.textContent = s.passive_coverage_pct != null ? `${s.passive_coverage_pct}%` : '—';
  const cov = s.passive_coverage_pct || 0;
  covEl.style.color = cov >= 100 ? 'var(--success)' : cov >= 50 ? 'var(--warning)' : 'var(--danger)';
}

function renderSensitivity(sensitivity) {
  const wrap = document.getElementById('sensitivity-wrap');
  if (!wrap) return;
  if (!sensitivity.length) {
    wrap.innerHTML = '<p class="chart-empty-tip">请先配置资产信息</p>';
    return;
  }

  const rows = sensitivity.map(s => {
    const yr = s.years_to_fire != null ? `<strong>${s.years_to_fire}</strong> 年` : '无法达标';
    return `<tr><td>${s.return_rate}%</td><td>${yr}</td></tr>`;
  }).join('');

  wrap.innerHTML = `
    <table class="sens-table">
      <thead><tr><th>年化收益率</th><th>达标年限</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="sens-note">内置通胀率 2.5%</p>`;
}

async function renderProjectionChart(s) {
  const canvas = document.getElementById('chart-projection');
  if (!canvas) return;

  if (!s.has_data || s.annual_return <= 0) {
    if (projectionChart) { projectionChart.destroy(); projectionChart = null; }
    canvas.parentElement.innerHTML =
      '<p class="chart-empty-tip">请先完善资产、工资和支出配置</p>';
    return;
  }

  let points = [];
  try {
    const res = await API.fireProjection(100);
    points = res.points || [];
  } catch (_) {}

  if (!points.length) {
    if (projectionChart) { projectionChart.destroy(); projectionChart = null; }
    canvas.parentElement.innerHTML =
      '<p class="chart-empty-tip">暂无有效预测数据，请完善配置</p>';
    return;
  }

  const labels        = points.map(p => `${p.year}年`);
  const assets        = points.map(p => p.assets);
  const fireTarget    = points.map(p => p.fire_target);
  const passiveIncome = points.map(p => p.passive_income);

  if (projectionChart) { projectionChart.destroy(); projectionChart = null; }

  projectionChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '预测资产',
          data: assets,
          borderColor: '#10B981',
          backgroundColor: 'rgba(16,185,129,0.08)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          yAxisID: 'y',
        },
        {
          label: '所需资产（FIRE门槛）',
          data: fireTarget,
          borderColor: '#F59E0B',
          borderWidth: 2,
          borderDash: [6, 4],
          fill: false,
          pointRadius: 0,
          yAxisID: 'y',
        },
        {
          label: '年被动收入',
          data: passiveIncome,
          borderColor: '#3B82F6',
          borderWidth: 1.5,
          borderDash: [3, 3],
          fill: false,
          pointRadius: 0,
          yAxisID: 'y',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ¥${(ctx.raw / 10000).toFixed(0)}万`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
        y: {
          grid: { color: 'rgba(0,0,0,0.04)' },
          ticks: { font: { size: 10 }, callback: v => `${(v / 10000).toFixed(0)}万` },
        },
      },
    },
  });
}

function renderCategoryPie(cats) {
  const canvas = document.getElementById('chart-expense-pie');
  if (!canvas || !cats.length) return;

  const labels = cats.slice(0, 6).map(c => c.icon + c.name);
  const data   = cats.slice(0, 6).map(c => c.amount);
  const colors = ['#10B981','#3B82F6','#F59E0B','#EF4444','#8B5CF6','#EC4899'];

  if (expenseChart) { expenseChart.destroy(); expenseChart = null; }

  expenseChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 6 } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ¥${ctx.raw.toFixed(0)}（${cats[ctx.dataIndex]?.pct}%）`,
          },
        },
      },
    },
  });
}

async function renderAIHint() {
  const el = document.getElementById('ai-hint-text');
  if (!el) return;
  try {
    const history = await API.aiHistory();
    const last = [...history].reverse().find(m => m.role === 'assistant');
    el.textContent = last
      ? last.content.replace(/\*\*/g, '').slice(0, 80) + '...'
      : '点击"AI 顾问"生成你的专属 FIRE 优化建议';
  } catch (_) {
    el.textContent = '点击"AI 顾问"生成你的专属 FIRE 优化建议';
  }
}

// ── FIRE 配置编辑 ─────────────────────────────────────────────────────────────
async function openFireConfig() {
  try {
    const p = await API.fireProfile();
    document.getElementById('cfg-total-assets').value  = p.total_assets           || '';
    document.getElementById('cfg-annual-return').value = ((p.annual_return || 0.05) * 100).toFixed(1);
    document.getElementById('cfg-annual-salary').value = p.annual_salary           || '';
    document.getElementById('cfg-salary-growth').value = ((p.salary_growth_rate || 0.05) * 100).toFixed(1);
    document.getElementById('cfg-fixed-expense').value = p.annual_fixed_expense   || '';
    document.getElementById('cfg-flex-expense').value  = p.annual_flex_expense    || '';
    openModal('modal-fire-config');
  } catch (e) { toast(e.message, 'error'); }
}

async function saveFireConfig() {
  const g  = id => parseFloat(document.getElementById(id).value) || 0;
  const body = {
    total_assets:         g('cfg-total-assets'),
    annual_return:        g('cfg-annual-return') / 100,
    annual_salary:        g('cfg-annual-salary'),
    salary_growth_rate:   g('cfg-salary-growth') / 100,
    annual_fixed_expense: g('cfg-fixed-expense'),
    annual_flex_expense:  g('cfg-flex-expense'),
  };
  try {
    await API.updateFireProfile(body);
    closeModal('modal-fire-config');
    toast('配置已保存');
    loadFireDashboard();
  } catch (e) { toast(e.message, 'error'); }
}

// 绑定事件
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-fire-config')?.addEventListener('click', openFireConfig);
  document.getElementById('btn-save-config')?.addEventListener('click', saveFireConfig);
});
