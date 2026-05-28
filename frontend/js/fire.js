// FIRE 仪表盘页

let projectionChart = null;
let expenseChart = null;
let assetChart = null;

async function loadFireDashboard() {
  try {
    const status = await API.fireStatus();
    renderHero(status);
    renderStats(status);
    await renderProjectionChart(status);
    renderCategoryPie(status.category_breakdown || []);
    renderAssetPie(status.asset_breakdown || {});
    renderAIHint();
  } catch (e) {
    document.getElementById('fire-years').textContent = '—';
    console.error(e);
  }
}

function renderHero(s) {
  const yearsEl = document.getElementById('fire-years');
  const subtitleEl = document.getElementById('fire-subtitle');
  const progressEl = document.getElementById('fire-progress-bar');
  const progressLabelEl = document.getElementById('fire-progress-label');

  if (s.years_to_fire === 0) {
    yearsEl.textContent = '🎉';
    subtitleEl.textContent = '恭喜！你已实现财务自由';
    yearsEl.style.fontSize = '3rem';
  } else if (s.years_to_fire === null) {
    yearsEl.textContent = '∞';
    subtitleEl.textContent = '当前支出超过收入，无法预测 — 请调整配置';
    yearsEl.style.color = 'var(--danger)';
  } else if (!s.has_data) {
    yearsEl.textContent = '?';
    subtitleEl.textContent = '请录入收入/资产信息，并添加至少1笔支出记录';
  } else {
    yearsEl.textContent = s.years_to_fire;
    subtitleEl.textContent = `距离财务自由还需 ${s.years_to_fire} 年（FIRE 目标 ${fmt(s.fire_number)}）`;
  }

  const pct = s.progress_pct || 0;
  progressEl.style.width = pct + '%';
  progressLabelEl.textContent = `${fmt(s.total_assets)} / ${fmt(s.fire_number)}（${pct}%）`;
}

function renderStats(s) {
  document.getElementById('stat-income').textContent   = fmt(s.monthly_income);
  document.getElementById('stat-expense').textContent  = fmt(s.avg_monthly_expense);
  document.getElementById('stat-savings').textContent  = fmt(s.monthly_savings);
  document.getElementById('stat-rate').textContent     = s.savings_rate != null ? `${s.savings_rate}%` : '—';

  // 储蓄率颜色
  const rateEl = document.getElementById('stat-rate');
  const r = s.savings_rate || 0;
  rateEl.style.color = r >= 50 ? 'var(--success)' : r >= 30 ? 'var(--warning)' : 'var(--danger)';
}

async function renderProjectionChart(s) {
  const canvas = document.getElementById('chart-projection');
  if (!canvas) return;

  let points = [];
  try {
    const res = await API.fireProjection(35);
    points = res.points || [];
  } catch (_) {}

  const labels = points.map(p => `${p.year}年`);
  const assets = points.map(p => p.assets);
  const target = points.map(p => p.fire_target);

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
        },
        {
          label: 'FIRE 目标',
          data: target,
          borderColor: '#F59E0B',
          borderWidth: 2,
          borderDash: [6, 4],
          fill: false,
          pointRadius: 0,
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
          ticks: {
            font: { size: 10 },
            callback: v => `${(v / 10000).toFixed(0)}万`,
          },
        },
      },
    },
  });
}

function renderCategoryPie(cats) {
  const canvas = document.getElementById('chart-expense-pie');
  if (!canvas || !cats.length) return;

  const labels = cats.slice(0, 6).map(c => c.icon + c.name);
  const data = cats.slice(0, 6).map(c => c.amount);
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

function renderAssetPie(assets) {
  const canvas = document.getElementById('chart-asset-pie');
  if (!canvas) return;

  const items = [
    { label: '💵 现金', value: assets.cash || 0 },
    { label: '📈 股票/基金', value: assets.stock || 0 },
    { label: '🏠 房产', value: assets.real_estate || 0 },
    { label: '💎 其他', value: assets.other || 0 },
  ].filter(i => i.value > 0);

  if (!items.length) {
    canvas.parentElement.innerHTML = '<p style="text-align:center;color:#9CA3AF;font-size:12px;padding:20px 0">暂无资产数据</p>';
    return;
  }

  if (assetChart) { assetChart.destroy(); assetChart = null; }

  assetChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: items.map(i => i.label),
      datasets: [{ data: items.map(i => i.value), backgroundColor: ['#06B6D4','#6366F1','#F97316','#84CC16'], borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 6 } },
        tooltip: { callbacks: { label: ctx => `${ctx.label}: ${fmt(ctx.raw)}` } },
      },
    },
  });
}

async function renderAIHint() {
  const el = document.getElementById('ai-hint-text');
  if (!el) return;
  // 只展示最近一条 AI assistant 回复的前80字
  try {
    const history = await API.aiHistory();
    const last = [...history].reverse().find(m => m.role === 'assistant');
    if (last) {
      el.textContent = last.content.replace(/\*\*/g, '').slice(0, 80) + '...';
    } else {
      el.textContent = '点击"AI 顾问"生成你的专属 FIRE 优化建议';
    }
  } catch (_) {
    el.textContent = '点击"AI 顾问"生成你的专属 FIRE 优化建议';
  }
}

// ── FIRE 配置编辑 ─────────────────────────────────────────────────────────────
async function openFireConfig() {
  try {
    const p = await API.fireProfile();
    document.getElementById('cfg-income').value          = p.monthly_income || '';
    document.getElementById('cfg-cash').value            = p.cash_assets || '';
    document.getElementById('cfg-stock').value           = p.stock_assets || '';
    document.getElementById('cfg-realestate').value      = p.real_estate_assets || '';
    document.getElementById('cfg-other').value           = p.other_assets || '';
    document.getElementById('cfg-return').value          = ((p.expected_return || 0.07) * 100).toFixed(1);
    document.getElementById('cfg-multiplier').value      = p.fire_multiplier || 25;
    openModal('modal-fire-config');
  } catch (e) { toast(e.message, 'error'); }
}

async function saveFireConfig() {
  const body = {
    monthly_income:      parseFloat(document.getElementById('cfg-income').value) || 0,
    cash_assets:         parseFloat(document.getElementById('cfg-cash').value) || 0,
    stock_assets:        parseFloat(document.getElementById('cfg-stock').value) || 0,
    real_estate_assets:  parseFloat(document.getElementById('cfg-realestate').value) || 0,
    other_assets:        parseFloat(document.getElementById('cfg-other').value) || 0,
    expected_return:     (parseFloat(document.getElementById('cfg-return').value) || 7) / 100,
    fire_multiplier:     parseFloat(document.getElementById('cfg-multiplier').value) || 25,
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
