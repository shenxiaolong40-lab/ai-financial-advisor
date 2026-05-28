// AI 财务自由顾问页

let aiLoaded = false;
let aiSending = false;

const QUICK_PROMPTS = [
  '如何提前 5 年实现财务自由？',
  '我的支出里哪项最值得压缩？',
  '现在的资产配置合理吗？',
  '帮我分析一下储蓄率',
];

async function loadAI() {
  if (!aiLoaded) {
    aiLoaded = true;
    await loadAIHistory();
    renderQuickPrompts();
  }
}

async function loadAIHistory() {
  try {
    const history = await API.aiHistory();
    const container = document.getElementById('ai-messages');
    container.innerHTML = '';
    history.forEach(m => appendMessage(m.role, m.content));
    scrollToBottom();
  } catch (_) {}
}

function renderQuickPrompts() {
  const container = document.getElementById('ai-quick-prompts');
  if (!container) return;
  container.innerHTML = QUICK_PROMPTS.map(q =>
    `<button class="quick-prompt-btn" data-q="${q}">${q}</button>`
  ).join('');
  container.querySelectorAll('.quick-prompt-btn').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.dataset.q));
  });
}

function appendMessage(role, content) {
  const container = document.getElementById('ai-messages');
  const el = document.createElement('div');
  el.className = `chat-msg chat-${role}`;
  // 简单 markdown 加粗支持
  el.innerHTML = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
  container.appendChild(el);
}

function scrollToBottom() {
  const container = document.getElementById('ai-messages');
  container.scrollTop = container.scrollHeight;
}

async function generateAnalysis() {
  const btn = document.getElementById('btn-ai-analysis');
  if (btn) { btn.disabled = true; btn.textContent = '分析中...'; }
  try {
    const r = await API.aiAnalysis();
    appendMessage('assistant', r.report || '暂无数据');
    scrollToBottom();
  } catch (e) {
    appendMessage('assistant', '分析失败：' + e.message);
    scrollToBottom();
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🔍 生成 FIRE 优化报告'; }
  }
}

async function sendMessage(text) {
  const input = document.getElementById('ai-input');
  const msg = text || (input?.value.trim());
  if (!msg || aiSending) return;
  if (input) input.value = '';
  aiSending = true;

  appendMessage('user', msg);
  const loadingEl = document.createElement('div');
  loadingEl.className = 'chat-msg chat-assistant chat-loading';
  loadingEl.textContent = '顾问思考中…';
  document.getElementById('ai-messages').appendChild(loadingEl);
  scrollToBottom();

  try {
    const r = await API.aiChat(msg);
    loadingEl.remove();
    appendMessage('assistant', r.reply || '暂无回复');
    scrollToBottom();
  } catch (e) {
    loadingEl.remove();
    appendMessage('assistant', '请求失败：' + e.message);
    scrollToBottom();
  } finally {
    aiSending = false;
  }
}

async function clearAIHistory() {
  if (!confirm('清空所有对话历史？')) return;
  try {
    await API.aiClearHistory();
    document.getElementById('ai-messages').innerHTML = '';
    aiLoaded = false;
    toast('已清空');
  } catch (e) { toast(e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-ai-analysis')?.addEventListener('click', generateAnalysis);
  document.getElementById('btn-ai-clear')?.addEventListener('click', clearAIHistory);

  document.getElementById('btn-ai-send')?.addEventListener('click', () => sendMessage());

  document.getElementById('ai-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
});
