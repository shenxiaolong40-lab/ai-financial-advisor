let aiGreeted = false;

function loadAI() {
  if (!aiGreeted) {
    appendMsg('assistant', '你好！我是你的 AI 财务顾问 👋\n\n我可以帮你分析消费习惯、评估储蓄目标进度、给出具体的省钱建议。\n\n你可以直接问我，或者点击上方的快捷问题。');
    aiGreeted = true;
  }
}

function appendMsg(role, text) {
  const el = document.getElementById('ai-messages');
  const div = document.createElement('div');
  div.className = 'msg-bubble ' + role;
  div.innerHTML = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

async function sendAI() {
  const input = document.getElementById('ai-input');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  appendMsg('user', text);

  const typingDiv = document.createElement('div');
  typingDiv.className = 'msg-bubble assistant';
  typingDiv.innerHTML = '<span class="text-muted">思考中…</span>';
  document.getElementById('ai-messages').appendChild(typingDiv);
  document.getElementById('ai-messages').scrollTop = 99999;

  try {
    const data = await API.aiChat({ message: text });
    typingDiv.innerHTML = (data.reply || '暂无回复')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  } catch (e) {
    typingDiv.innerHTML = `<span class="text-danger">请求失败：${e.message}</span>`;
  }
  document.getElementById('ai-messages').scrollTop = 99999;
}

function sendQuick(text) {
  document.getElementById('ai-input').value = text;
  sendAI();
}
