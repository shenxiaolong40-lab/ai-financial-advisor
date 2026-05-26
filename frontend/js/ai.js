let aiLoaded = false;
let aiSending = false;

async function loadAI() {
  if (aiLoaded) return;
  aiLoaded = true;
  await loadAIHistory();
  if (!document.getElementById('ai-messages').children.length) {
    appendMsg('assistant', '你好！我是你的 **AI 财务顾问** 👋\n\n我已接入你的真实账单数据，可以帮你分析消费习惯、评估储蓄目标、给出具体的省钱建议。\n\n试试下方的快捷问题，或直接输入你的问题。');
  }
}

async function loadAIHistory() {
  try {
    const history = await API.aiHistory();
    const el = document.getElementById('ai-messages');
    el.innerHTML = '';
    history.forEach(h => {
      if (h.role === 'user' || h.role === 'assistant') {
        appendMsg(h.role, h.content, false);
      }
    });
    el.scrollTop = el.scrollHeight;
  } catch (e) {
    console.error('Load history error', e);
  }
}

function appendMsg(role, text, scroll = true) {
  const el = document.getElementById('ai-messages');
  const div = document.createElement('div');
  div.className = 'msg-bubble ' + role;
  div.innerHTML = mdToHtml(text);
  el.appendChild(div);
  if (scroll) el.scrollTop = el.scrollHeight;
  return div;
}

function mdToHtml(text) {
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
}

async function sendAI() {
  if (aiSending) return;
  const input = document.getElementById('ai-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  aiSending = true;
  appendMsg('user', text);

  const typingDiv = appendMsg('assistant', '');
  typingDiv.innerHTML = '<span class="ai-typing"><span></span><span></span><span></span></span>';

  try {
    const data = await API.aiChat({ message: text });
    typingDiv.innerHTML = mdToHtml(data.reply || '暂无回复');
    if (data.model) {
      const modelTag = document.createElement('div');
      modelTag.className = 'ai-model-tag';
      modelTag.textContent = data.model.includes('haiku') ? '⚡ Haiku' : '🧠 Sonnet';
      typingDiv.appendChild(modelTag);
    }
  } catch (e) {
    typingDiv.innerHTML = `<span style="color:var(--danger)">请求失败：${e.message}</span>`;
  }

  document.getElementById('ai-messages').scrollTop = 99999;
  aiSending = false;
}

async function runAnalysis() {
  if (aiSending) return;
  aiSending = true;

  const btn = document.getElementById('btn-analysis');
  if (btn) { btn.disabled = true; btn.textContent = '分析中…'; }

  const typingDiv = appendMsg('assistant', '');
  typingDiv.innerHTML = '📊 正在生成本月财务分析报告…<br><span class="ai-typing"><span></span><span></span><span></span></span>';
  document.getElementById('ai-messages').scrollTop = 99999;

  try {
    const data = await API.aiAnalysis();
    typingDiv.innerHTML = mdToHtml(data.report || '分析完成');
    const modelTag = document.createElement('div');
    modelTag.className = 'ai-model-tag';
    modelTag.textContent = '🧠 Sonnet 深度分析';
    typingDiv.appendChild(modelTag);
  } catch (e) {
    typingDiv.innerHTML = `<span style="color:var(--danger)">分析失败：${e.message}</span>`;
  }

  document.getElementById('ai-messages').scrollTop = 99999;
  if (btn) { btn.disabled = false; btn.textContent = '📊 生成分析报告'; }
  aiSending = false;
}

async function clearAIHistory() {
  if (!confirm('确认清空对话记录？')) return;
  try {
    await API.aiClearHistory();
    document.getElementById('ai-messages').innerHTML = '';
    aiLoaded = false;
    loadAI();
    showToast('对话已清空');
  } catch (e) { alert(e.message); }
}

function sendQuick(text) {
  document.getElementById('ai-input').value = text;
  sendAI();
}
