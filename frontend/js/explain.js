// 财务自由说明页

const INFLATION = 0.025;

async function loadExplain() {
  try {
    const [s, profile] = await Promise.all([API.fireStatus(), API.fireProfile()]);
    if (!s.has_data) {
      document.getElementById('explain-loading').style.display = '';
      document.getElementById('explain-content').style.display = 'none';
      return;
    }
    document.getElementById('explain-loading').style.display = 'none';
    document.getElementById('explain-content').style.display = '';

    renderParams(s, profile);
    renderCurrent(s);
    renderLogic(s, profile);

    const proj = await API.fireProjection(100);
    renderMilestones(s, proj.points || []);
    renderExplainSensitivity(s);
  } catch (e) {
    console.error(e);
  }
}

// ── 参数卡 ────────────────────────────────────────────────────────────────────
function renderParams(s, profile) {
  const el = document.getElementById('explain-params');
  const gs = profile?.salary_growth_rate != null
    ? (profile.salary_growth_rate * 100).toFixed(1) + '%'
    : '5%';
  const rows = [
    ['💰 当前总资产',    fmt(s.total_assets)],
    ['📈 年化理财收益率', s.annual_return + '%'],
    ['💼 税后年工资',    fmt(s.annual_salary)],
    ['📊 年工资增长率',  gs],
    ['🏠 年刚性支出',    fmt(s.annual_fixed_expense)],
    ['🛍 年弹性支出',    fmt(s.annual_flex_expense)],
    ['📋 年总支出',      fmt(s.annual_expense)],
  ];
  el.innerHTML = rows.map(([label, value]) => `
    <div class="explain-param-row">
      <span class="explain-param-label">${label}</span>
      <span class="explain-param-value">${value}</span>
    </div>
  `).join('');

  // 数据来源徽章
  const ds = s.data_source || {};
  const srcLabel = (k) => {
    const v = ds[k];
    if (v === 'transactions') return '来自近3月交易记录';
    if (v === 'manual')       return '来自手动配置';
    return '未填写';
  };
  const txInfo = ds.expense === 'transactions' || ds.income === 'transactions'
    ? `<div class="explain-data-source">
         收入数据：${srcLabel('income')} · 支出数据：${srcLabel('expense')}
       </div>`
    : '';
  el.insertAdjacentHTML('beforeend', txInfo);
}

// ── 现在的位置 ────────────────────────────────────────────────────────────────
function renderCurrent(s) {
  const el = document.getElementById('explain-current');
  const gap = s.annual_expense - s.current_passive_income;
  const coverPct = s.passive_coverage_pct;

  if (s.already_free) {
    el.innerHTML = `<div class="explain-highlight success">
      🎉 恭喜！你的资产每年产生 <strong>${fmt(s.current_passive_income)}</strong> 被动收入，
      已经覆盖了年支出 ${fmt(s.annual_expense)}，你已实现财务自由！
    </div>`;
    return;
  }

  el.innerHTML = `
    <div class="explain-block">
      <p>你目前的资产 <strong>${fmt(s.total_assets)}</strong> 每年能产生
        <strong>${fmt(s.current_passive_income)}</strong> 被动收入（${s.annual_return}% 年化）。</p>
      <p>但你每年需要 <strong>${fmt(s.annual_expense)}</strong> 才能维持生活。</p>
    </div>
    <div class="explain-gap-bar">
      <div class="explain-gap-fill" style="width:${Math.min(coverPct, 100)}%">
        <span>${coverPct.toFixed(1)}%</span>
      </div>
    </div>
    <p class="explain-gap-label">
      被动收入已覆盖 <strong>${coverPct.toFixed(1)}%</strong> 的年支出，
      还差 <strong>${fmt(gap)}</strong>/年 才能财务自由。
    </p>
    ${s.annual_surplus > 0
      ? `<p class="explain-note">好消息：你每年的工资结余 <strong>${fmt(s.annual_surplus)}</strong>（工资 ${fmt(s.annual_salary)} - 支出 ${fmt(s.annual_expense)}）会持续投入资产池，加速缩小这个差距。</p>`
      : `<p class="explain-note warn">⚠️ 你的年支出超过年工资，资产会被消耗。调整收支结构是首要任务。</p>`
    }
  `;
}

// ── 财务自由逻辑 ──────────────────────────────────────────────────────────────
function renderLogic(s, profile) {
  const el = document.getElementById('explain-logic');

  if (!s.has_data) { el.innerHTML = ''; return; }

  const yearsText = s.years_to_fire === null
    ? '按当前参数无法在 100 年内达标'
    : `大约需要 <strong>${s.years_to_fire} 年</strong>`;

  el.innerHTML = `
    <div class="explain-block">
      <p><strong>财务自由 = 被动收入 ≥ 年支出</strong></p>
      <p>即：资产 × ${s.annual_return}% ≥ 每年支出（含通胀增长）</p>
      <p>你现在的资产需要达到约
        <strong>${fmt(s.annual_expense / (s.annual_return / 100))}</strong>
        才能仅靠被动收入覆盖当前支出。
      </p>
    </div>
    <div class="explain-block">
      <p><strong>怎么走到那一步？</strong></p>
      <ol class="explain-steps">
        <li>你每年把工资结余 <strong>${fmt(s.annual_surplus)}</strong> 存入资产池</li>
        <li>已有资产以 <strong>${s.annual_return}%</strong> 年化增长（复利）</li>
        <li>同时，支出随通胀 <strong>2.5%/年</strong> 增长，所需资产目标也在升高</li>
        <li>两条线交叉的那一刻，就是财务自由</li>
      </ol>
      <p class="explain-note">${yearsText}</p>
    </div>
  `;
}

// ── 里程碑 ────────────────────────────────────────────────────────────────────
function renderMilestones(s, points) {
  const el = document.getElementById('explain-milestones');
  if (!points.length) {
    el.innerHTML = '<p class="chart-empty-tip">暂无预测数据，请完善配置。</p>';
    return;
  }

  // 找到被动收入覆盖 25% / 50% / 75% / 100% 支出的年份
  const targets = [0.25, 0.5, 0.75, 1.0];
  const milestones = targets.map(ratio => {
    const pt = points.find(p => p.passive_income >= p.expense * ratio);
    return { label: `${ratio * 100}%`, year: pt ? pt.year : null, pt };
  });

  const rows = milestones.map(m => {
    if (!m.year) return `<tr><td>覆盖 ${m.label}</td><td colspan="3" class="muted">100年内未达到</td></tr>`;
    return `<tr>
      <td>被动收入覆盖 <strong>${m.label}</strong> 支出</td>
      <td>第 <strong>${m.year}</strong> 年</td>
      <td>${fmt(m.pt.assets)}</td>
      <td>${fmt(m.pt.passive_income)} / 年</td>
    </tr>`;
  }).join('');

  el.innerHTML = `
    <table class="milestone-table">
      <thead><tr><th>里程碑</th><th>时间</th><th>届时资产</th><th>届时被动收入</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="explain-note">注：支出每年随通胀 2.5% 增长，目标资产同步上升。</p>
  `;
}

// ── 敏感性 ────────────────────────────────────────────────────────────────────
function renderExplainSensitivity(s) {
  const el = document.getElementById('explain-sensitivity');
  const sens = s.sensitivity || [];
  if (!sens.length) { el.innerHTML = ''; return; }

  const rows = sens.map(item => {
    const isBase = Math.abs(item.return_rate - s.annual_return) < 0.05;
    const yr = item.years_to_fire != null ? `${item.years_to_fire} 年` : '100年内未达标';
    return `<tr class="${isBase ? 'sens-base' : ''}">
      <td>${item.return_rate}%${isBase ? ' ← 当前' : ''}</td>
      <td><strong>${yr}</strong></td>
      <td>${item.years_to_fire != null && s.sensitivity[1]?.years_to_fire != null
        ? (item.years_to_fire - s.sensitivity[1].years_to_fire > 0 ? '+' : '') +
          (item.years_to_fire - s.sensitivity[1].years_to_fire) + ' 年'
        : '—'}</td>
    </tr>`;
  }).join('');

  el.innerHTML = `
    <p class="explain-note">收益率每提升 1%，达标年限大约缩短：</p>
    <table class="sens-table">
      <thead><tr><th>年化收益率</th><th>达标年限</th><th>与当前差异</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <p class="explain-note">提升投资收益率（如从货基转指数基金）是缩短时间最有效的杠杆之一。</p>
  `;
}
