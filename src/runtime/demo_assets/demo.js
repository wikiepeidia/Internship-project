const form = document.querySelector("#analysis-form");
const messageInput = document.querySelector("#message-input");
const channelSelect = document.querySelector("#channel-select");
const analyzeButton = document.querySelector("#analyze-button");
const sampleButton = document.querySelector("#sample-button");
const resultPanel = document.querySelector("#result-panel");

const resultTemplate = document.querySelector("#result-template");
const errorTemplate = document.querySelector("#error-template");

const sampleText = "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP hoặc Smart OTP và không bấm vào link đăng nhập https://vpbank-secure.example để xác minh ngay.";

const riskTierLabel = {
  benign: "Benign",
  suspicious: "Suspicious",
  "high-risk": "High risk",
};

function resetPanel() {
  resultPanel.classList.remove("result-panel--empty");
  resultPanel.replaceChildren();
}

function setBusyState(isBusy) {
  analyzeButton.disabled = isBusy;
  sampleButton.disabled = isBusy;
  analyzeButton.textContent = isBusy ? "Analyzing..." : "Analyze locally";
}

function createListItems(listNode, values) {
  listNode.replaceChildren();

  if (!values.length) {
    const item = document.createElement("li");
    item.textContent = "None";
    listNode.append(item);
    return;
  }

  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    listNode.append(item);
  });
}

function renderResult(result) {
  resetPanel();
  const fragment = resultTemplate.content.cloneNode(true);

  fragment.querySelector("#result-summary").textContent = result.summary;
  const riskPill = fragment.querySelector("#result-risk-tier");
  riskPill.textContent = riskTierLabel[result.risk_tier] ?? result.risk_tier;
  riskPill.dataset.riskTier = result.risk_tier;
  fragment.querySelector("#result-labels").textContent = result.threat_labels.length
    ? result.threat_labels.join(", ")
    : "None";
  fragment.querySelector("#result-backend").textContent = result.backend_name;

  createListItems(
    fragment.querySelector("#result-cues"),
    result.top_cues.map((cue) => `"${cue.span}" - ${cue.reason}`),
  );
  createListItems(fragment.querySelector("#result-recommendations"), result.recommendations);

  resultPanel.append(fragment);
}

function renderError(error) {
  resetPanel();
  const fragment = errorTemplate.content.cloneNode(true);

  fragment.querySelector("#error-message").textContent = error.message;
  createListItems(fragment.querySelector("#error-steps"), error.steps || []);

  resultPanel.append(fragment);
}

async function analyzeMessage(event) {
  event.preventDefault();
  setBusyState(true);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: messageInput.value,
        channel: channelSelect.value,
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      renderError(payload.error || { message: "Unknown error", steps: [] });
      return;
    }

    renderResult(payload);
  } catch (error) {
    renderError({
      message: "The local demo could not reach the runtime service.",
      steps: ["Retry after the local runtime finishes loading."],
    });
  } finally {
    setBusyState(false);
  }
}

form.addEventListener("submit", analyzeMessage);

sampleButton.addEventListener("click", () => {
  messageInput.value = sampleText;
  channelSelect.value = "sms";
  messageInput.focus();
});

messageInput.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    form.requestSubmit();
  }
});