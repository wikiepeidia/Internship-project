// DOM refs
const form = document.getElementById('analysis-form');
const messageInput = document.getElementById('message-input');
const channelSelect = document.getElementById('channel-select');
const analyzeButton = document.getElementById('analyze-button');
const sampleButton = document.getElementById('sample-button');
const resultPanel = document.getElementById('result-panel');
const userMsgTpl = document.getElementById('user-message-template');
const resultTpl = document.getElementById('result-template');
const typingTpl = document.getElementById('typing-template');
const errorTpl = document.getElementById('error-template');

// Module state
const history = [];
let currentController = null;
const sampleText = 'VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP hoặc Smart OTP và không bấm vào link đăng nhập https://vpbank-secure.example để xác minh ngay.';

// Apply i18n text to cloned template nodes
function applyI18nToClone(el) {
  if (!window.I18N) return;
  el.querySelectorAll('[data-i18n]').forEach((node) => {
    const key = node.dataset.i18n;
    if (window.I18N[key]) node.textContent = window.I18N[key];
  });
  el.querySelectorAll('[data-i18n-aria]').forEach((node) => {
    const key = node.dataset.i18nAria;
    if (window.I18N[key]) node.setAttribute('aria-label', window.I18N[key]);
  });
}

// Populate a <ul> with <li> items; empty list falls back to LIST_EMPTY
function createListItems(listNode, values) {
  listNode.replaceChildren();
  if (!values || !values.length) {
    const item = document.createElement('li');
    item.textContent = window.I18N?.LIST_EMPTY ?? 'Không có';
    listNode.append(item);
    return;
  }
  values.forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    listNode.append(item);
  });
}

// Scroll thread to newest bubble after paint
function scrollToBottom() {
  requestAnimationFrame(() => { resultPanel.scrollTop = resultPanel.scrollHeight; });
}

// Disable/enable send button and update its label
function setBusyState(isBusy) {
  analyzeButton.disabled = isBusy;
  analyzeButton.textContent = window.I18N
    ? (isBusy ? window.I18N.ANALYZE_BTN_BUSY : window.I18N.ANALYZE_BTN)
    : (isBusy ? 'Đang phân tích...' : 'Phân tích tại máy');
}

// Append right-aligned user bubble
function appendUserBubble(text) {
  const article = userMsgTpl.content.cloneNode(true).firstElementChild;
  article.querySelector('[data-slot="text"]').textContent = text;
  applyI18nToClone(article);
  resultPanel.classList.remove('result-panel--empty');
  resultPanel.append(article);
  scrollToBottom();
}

// Append animated typing bubble; returns the DOM node for later removal
function appendTypingBubble() {
  const article = typingTpl.content.cloneNode(true).firstElementChild;
  applyI18nToClone(article);
  resultPanel.append(article);
  scrollToBottom();
  return article;
}

// Risk tier → bilingual label
function riskLabel(tier) {
  const map = {
    benign: window.I18N?.RISK_BENIGN ?? 'Thấp / Không phát hiện',
    suspicious: window.I18N?.RISK_SUSPICIOUS ?? 'Nguy hiểm trung bình',
    'high-risk': window.I18N?.RISK_HIGH ?? 'Nguy hiểm cao',
  };
  return map[tier] ?? tier;
}

// Append bot result bubble
function appendResultBubble(result) {
  const article = resultTpl.content.cloneNode(true).firstElementChild;
  applyI18nToClone(article);

  article.querySelector('[data-slot="verdict"]').textContent = result.summary;

  const riskPill = article.querySelector('[data-slot="risk-tier"]');
  riskPill.textContent = riskLabel(result.risk_tier);
  riskPill.dataset.riskTier = result.risk_tier;

  article.querySelector('[data-slot="labels"]').textContent = result.threat_labels.length
    ? result.threat_labels.join(', ')
    : (window.I18N?.LIST_EMPTY ?? 'Không có');

  article.querySelector('[data-slot="backend"]').textContent = result.backend_name;

  createListItems(
    article.querySelector('[data-slot="grounded-cues"]'),
    result.top_cues.map((c) => `"${c.span}" — ${c.reason}`),
  );
  createListItems(article.querySelector('[data-slot="recommendations"]'), result.recommendations);

  resultPanel.append(article);
  scrollToBottom();
}

// Append error bubble
function appendErrorBubble(error) {
  const article = errorTpl.content.cloneNode(true).firstElementChild;
  applyI18nToClone(article);
  article.querySelector('[data-slot="message"]').textContent = error.message;
  createListItems(article.querySelector('[data-slot="steps"]'), error.steps || []);
  resultPanel.append(article);
  scrollToBottom();
}

// Submit handler
async function analyzeMessage(event) {
  event.preventDefault();

  const text = messageInput.value.trim();
  if (!text) return;
  const channel = channelSelect.value;

  if (currentController) currentController.abort();
  currentController = new AbortController();

  history.push({ text, channel });
  appendUserBubble(text);
  messageInput.value = '';
  setBusyState(true);
  const typingEl = appendTypingBubble();

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, channel }),
      signal: currentController.signal,
    });

    const payload = await response.json();
    typingEl.remove();

    if (!response.ok) {
      appendErrorBubble(payload.error || {
        message: window.I18N?.ERR_NETWORK ?? 'Lỗi không xác định.',
        steps: [],
      });
      return;
    }

    appendResultBubble(payload);
  } catch (err) {
    typingEl.remove();
    if (err.name !== 'AbortError') {
      appendErrorBubble({
        message: window.I18N?.ERR_NETWORK ?? 'Không thể kết nối với runtime cục bộ.',
        steps: [window.I18N?.ERR_NETWORK_STEP ?? 'Thử lại sau khi runtime cục bộ đã tải xong.'],
      });
    }
  } finally {
    setBusyState(false);
    currentController = null;
  }
}

// Event listeners
form.addEventListener('submit', analyzeMessage);

messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

sampleButton.addEventListener('click', () => {
  messageInput.value = sampleText;
  channelSelect.value = 'sms';
  messageInput.focus();
});
