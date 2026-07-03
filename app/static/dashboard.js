const tokenKey = "usdt_auto_token";

const moneyFormatter = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });
const decimalFormatter = new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const usdtFormatter = new Intl.NumberFormat("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 6 });
const kstDateTimeFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});
const kstTimeFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const ids = [
  "authView",
  "appView",
  "authMessage",
  "toast",
  "loginId",
  "password",
  "loginButton",
  "registerButton",
  "logoutButton",
  "currentUser",
  "updatedAt",
  "botStatus",
  "tradeMode",
  "strategyType",
  "lastSignal",
  "lastSignalAt",
  "premiumRate",
  "premiumState",
  "premiumMarker",
  "upbitUsdtPrice",
  "usdKrwRate",
  "totalAssetKrw",
  "krwBalance",
  "usdtBalance",
  "avgBuyPrice",
  "todayProfit",
  "todayTradeCount",
  "lastError",
  "tradeRows",
  "startButton",
  "stopButton",
  "settingMarket",
  "settingsForm",
  "settingTradeMode",
  "settingStrategy",
  "settingApiKey",
  "settingBuyPremium",
  "settingSellPremium",
  "settingBasePrice",
  "settingPriceGap",
  "settingMaxOrder",
  "settingManualFx",
  "strategyHint",
  "saveSettingsButton",
  "manualSellForm",
  "manualSellPrice",
  "manualSellVolume",
  "manualSellButton",
  "apiKeyName",
  "apiAccessKey",
  "apiSecretKey",
  "saveApiKeyButton",
  "apiKeyList",
];

const el = Object.fromEntries(ids.map((id) => [id, document.getElementById(id)]));
let settingsDirty = false;
let toastTimer = null;

function isEditingSettings() {
  return settingsDirty || el.settingsForm.contains(document.activeElement);
}

function notify(message, type = "success") {
  if (toastTimer) window.clearTimeout(toastTimer);
  el.toast.textContent = message;
  el.toast.className = type === "error" ? "toast error" : "toast";
  toastTimer = window.setTimeout(() => {
    el.toast.classList.add("hidden");
  }, 3200);
}

async function withButtonFeedback(button, action, successMessage) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "처리 중...";
  try {
    const result = await action();
    notify(successMessage);
    return result;
  } catch (error) {
    notify(error.message || "처리 중 오류가 발생했습니다.", "error");
    throw error;
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

function token() {
  return localStorage.getItem(tokenKey);
}

function setToken(value) {
  localStorage.setItem(tokenKey, value);
}

function clearToken() {
  localStorage.removeItem(tokenKey);
}

function showAuth(message = "") {
  el.authView.classList.remove("hidden");
  el.appView.classList.add("hidden");
  el.authMessage.textContent = message;
}

function showApp() {
  el.authView.classList.add("hidden");
  el.appView.classList.remove("hidden");
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    clearToken();
    showAuth("로그인이 필요합니다.");
    throw new Error("Not authenticated");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed: ${path}`);
  }
  return response.json();
}

function krw(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${moneyFormatter.format(Number(value))}원`;
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${decimalFormatter.format(Number(value))}%`;
}

function integer(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return moneyFormatter.format(Number(value));
}

function usdt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return usdtFormatter.format(Number(value));
}

function shortDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${kstDateTimeFormatter.format(date)} KST`;
}

function botStatusLabel(value) {
  const labels = {
    STOPPED: "중지",
    RUNNING: "실행 중",
    PAUSED_BY_RISK: "리스크 중지",
    ERROR: "오류",
  };
  return labels[value] ?? value ?? "-";
}

function tradeModeLabel(value) {
  const labels = {
    paper: "가상매매",
    live: "실거래",
  };
  return labels[value] ?? value ?? "-";
}

function strategyLabel(value) {
  const labels = {
    premium_rebalance: "환율 괴리",
    base_price_gap: "기준가격",
  };
  return labels[value] ?? value ?? "-";
}

function signalLabel(value) {
  const labels = {
    BUY: "매수",
    SELL: "매도",
    HOLD: "대기",
  };
  return labels[value] ?? value ?? "-";
}

function updateStatusClass(status) {
  el.botStatus.className = "status-pill";
  if (status === "RUNNING") el.botStatus.classList.add("running");
  if (status === "ERROR") el.botStatus.classList.add("error");
  if (status === "PAUSED_BY_RISK") el.botStatus.classList.add("paused");
}

function premiumState(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return ["-", "hold"];
  const premium = Number(value);
  if (premium <= -0.3) return ["매수 구간", "buy"];
  if (premium >= 0.3) return ["매도 구간", "sell"];
  return ["대기", "hold"];
}

function renderStatus(data) {
  el.botStatus.textContent = botStatusLabel(data.botStatus);
  updateStatusClass(data.botStatus);
  el.tradeMode.textContent = tradeModeLabel(data.tradeMode);
  el.strategyType.textContent = strategyLabel(data.strategyType);
  el.lastSignal.textContent = signalLabel(data.lastSignal);
  el.lastSignalAt.textContent = shortDate(data.lastSignalAt);
  el.premiumRate.textContent = percent(data.premiumRate);

  const [stateText, stateClass] = premiumState(data.premiumRate);
  el.premiumState.textContent = data.strategyType === "base_price_gap" ? "기준가격" : stateText;
  el.premiumState.className = `state ${stateClass}`;

  const clamped = Math.max(-1, Math.min(1, Number(data.premiumRate ?? 0)));
  el.premiumMarker.style.left = `${((clamped + 1) / 2) * 100}%`;

  el.upbitUsdtPrice.textContent = krw(data.upbitUsdtPrice);
  el.usdKrwRate.textContent = krw(data.usdKrwRate);
  el.totalAssetKrw.textContent = krw(data.totalAssetKrw);
  el.krwBalance.textContent = krw(data.krwBalance);
  el.usdtBalance.textContent = usdt(data.usdtBalance);
  el.avgBuyPrice.textContent = krw(data.avgBuyPrice);
  el.todayProfit.textContent = krw(data.todayProfit);
  el.todayProfit.className = Number(data.todayProfit ?? 0) >= 0 ? "positive" : "negative";
  el.todayTradeCount.textContent = integer(data.todayTradeCount);
  el.lastError.textContent = data.lastError || "-";
  el.updatedAt.textContent = `갱신 ${kstTimeFormatter.format(new Date())} KST`;
}

function renderTrades(trades) {
  if (!Array.isArray(trades) || trades.length === 0) {
    el.tradeRows.innerHTML = '<tr><td colspan="5" class="empty">거래내역이 없습니다</td></tr>';
    return;
  }
  el.tradeRows.innerHTML = trades
    .map((trade) => {
      const profit = Number(trade.profit ?? 0);
      const profitClass = profit >= 0 ? "positive" : "negative";
      return `
        <tr>
          <td>${shortDate(trade.created_at)}</td>
          <td>${signalLabel(trade.side)}</td>
          <td>${krw(trade.price)}</td>
          <td>${usdt(trade.volume)}</td>
          <td class="${profitClass}">${krw(profit)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderSettings(settings) {
  if (isEditingSettings()) return;
  el.settingMarket.value = settings.market ?? "KRW-USDT";
  el.settingTradeMode.value = settings.trade_mode ?? "paper";
  el.settingStrategy.value = settings.strategy_type ?? "premium_rebalance";
  el.settingApiKey.value = settings.api_key_id ?? "";
  el.settingBuyPremium.value = settings.buy_premium_threshold ?? -0.3;
  el.settingSellPremium.value = settings.sell_premium_threshold ?? 0.3;
  el.settingBasePrice.value = settings.base_price ?? "";
  el.settingPriceGap.value = settings.price_gap ?? 3;
  el.settingMaxOrder.value = settings.max_order_amount ?? 10000000;
  el.settingManualFx.value = settings.manual_usd_krw_rate ?? 1370;
  updateStrategyFields();
  renderStrategyHint();
}

function updateStrategyFields() {
  const strategy = el.settingStrategy.value;
  const premiumEnabled = strategy === "premium_rebalance";
  const baseEnabled = strategy === "base_price_gap";
  for (const wrapper of el.settingsForm.querySelectorAll("[data-strategy-field]")) {
    const type = wrapper.dataset.strategyField;
    const enabled = type === "premium" ? premiumEnabled : baseEnabled;
    wrapper.classList.toggle("field-disabled", !enabled);
    for (const input of wrapper.querySelectorAll("input, select")) {
      input.disabled = !enabled;
    }
  }
}

function renderStrategyHint() {
  const strategy = el.settingStrategy.value;
  const basePrice = Number(el.settingBasePrice.value);
  const priceGap = Number(el.settingPriceGap.value || 0);
  if (strategy === "base_price_gap" && Number.isFinite(basePrice) && basePrice > 0 && Number.isFinite(priceGap)) {
    el.strategyHint.textContent = `기준가격 전략: 보유 USDT가 없으면 현재가가 ${krw(basePrice - priceGap)} 이하일 때 매수합니다. 매도는 기준가격이 아니라 실제 평균 매수가 + 기준차이가격, 즉 매수 후 평균 매수가보다 ${krw(priceGap)} 올라왔을 때 나갑니다.`;
    return;
  }
  if (strategy === "base_price_gap") {
    el.strategyHint.textContent = "기준가격 전략: 기준가격과 기준차이가격을 입력하면 매수 기준을 계산합니다. 매도는 실제 평균 매수가 + 기준차이가격 기준입니다.";
    return;
  }
  el.strategyHint.textContent = "환율 괴리 전략: 매수/매도 괴리율 기준에 도달하면 신호가 발생합니다.";
}

function renderApiKeys(keys) {
  el.settingApiKey.innerHTML = '<option value="">선택 안 함</option>';
  el.apiKeyList.innerHTML = "";
  for (const key of keys) {
    const option = document.createElement("option");
    option.value = key.id;
    option.textContent = key.name;
    el.settingApiKey.appendChild(option);

    const item = document.createElement("div");
    item.className = "key-item";
    item.innerHTML = `<strong>${key.name}</strong><span>${key.is_active ? "사용 중" : "중지"}</span>`;
    el.apiKeyList.appendChild(item);
  }
  if (keys.length === 0) el.apiKeyList.innerHTML = '<p class="message">저장된 API 키가 없습니다.</p>';
}

async function refresh() {
  const [me, status, trades, settings, apiKeys] = await Promise.all([
    api("/me"),
    api("/status"),
    api("/trades?limit=10"),
    api("/bot/settings"),
    api("/api-keys"),
  ]);
  el.currentUser.textContent = me.login_id;
  renderApiKeys(apiKeys);
  renderSettings(settings);
  renderStatus(status);
  renderTrades(trades);
  if (!isEditingSettings() && settings.api_key_id) el.settingApiKey.value = settings.api_key_id;
}

async function login(path) {
  el.authMessage.textContent = "";
  const payload = { login_id: el.loginId.value.trim(), password: el.password.value };
  const response = await api(path, { method: "POST", body: JSON.stringify(payload) });
  setToken(response.access_token);
  showApp();
  await refresh();
}

async function command(path) {
  const status = await api(path, { method: "POST" });
  renderStatus(status);
  await refresh();
}

async function saveSettings() {
  const payload = {
    market: el.settingMarket.value,
    trade_mode: el.settingTradeMode.value,
    strategy_type: el.settingStrategy.value,
    api_key_id: el.settingApiKey.value ? Number(el.settingApiKey.value) : null,
    buy_premium_threshold: Number(el.settingBuyPremium.value),
    sell_premium_threshold: Number(el.settingSellPremium.value),
    base_price: el.settingBasePrice.value ? Number(el.settingBasePrice.value) : null,
    price_gap: Number(el.settingPriceGap.value),
    max_order_amount: Number(el.settingMaxOrder.value),
    manual_usd_krw_rate: Number(el.settingManualFx.value),
  };
  await api("/bot/settings", { method: "PUT", body: JSON.stringify(payload) });
  settingsDirty = false;
  document.activeElement?.blur();
  await refresh();
}

async function saveApiKey() {
  const payload = {
    name: el.apiKeyName.value.trim(),
    access_key: el.apiAccessKey.value.trim(),
    secret_key: el.apiSecretKey.value.trim(),
  };
  await api("/api-keys", { method: "POST", body: JSON.stringify(payload) });
  el.apiKeyName.value = "";
  el.apiAccessKey.value = "";
  el.apiSecretKey.value = "";
  await refresh();
}

async function manualSell() {
  const price = Number(el.manualSellPrice.value);
  if (!Number.isFinite(price) || price <= 0) {
    throw new Error("매도가를 입력하세요.");
  }
  const payload = {
    price,
    volume: el.manualSellVolume.value ? Number(el.manualSellVolume.value) : null,
  };
  await api("/bot/manual-sell", { method: "POST", body: JSON.stringify(payload) });
  el.manualSellPrice.value = "";
  el.manualSellVolume.value = "";
  await refresh();
}

el.loginButton.addEventListener("click", () =>
  withButtonFeedback(el.loginButton, () => login("/auth/login"), "로그인되었습니다.").catch(
    (error) => (el.authMessage.textContent = error.message),
  ),
);
el.registerButton.addEventListener("click", () =>
  withButtonFeedback(el.registerButton, () => login("/auth/register"), "가입되었습니다.").catch(
    (error) => (el.authMessage.textContent = error.message),
  ),
);
el.logoutButton.addEventListener("click", () => {
  clearToken();
  showAuth();
});
el.startButton.addEventListener("click", () =>
  withButtonFeedback(el.startButton, () => command("/bot/start"), "봇이 시작되었습니다.").catch(console.error),
);
el.stopButton.addEventListener("click", () =>
  withButtonFeedback(el.stopButton, () => command("/bot/stop"), "봇이 중지되었습니다.").catch(console.error),
);
el.saveSettingsButton.addEventListener("click", () =>
  withButtonFeedback(el.saveSettingsButton, saveSettings, "설정이 저장되었습니다.").catch(console.error),
);
el.saveApiKeyButton.addEventListener("click", () =>
  withButtonFeedback(el.saveApiKeyButton, saveApiKey, "API 키가 저장되었습니다.").catch(console.error),
);
el.manualSellButton.addEventListener("click", () =>
  withButtonFeedback(el.manualSellButton, manualSell, "강제 매도가 처리되었습니다.").catch(console.error),
);
el.settingsForm.addEventListener("input", () => {
  settingsDirty = true;
  updateStrategyFields();
  renderStrategyHint();
});
el.settingsForm.addEventListener("change", () => {
  settingsDirty = true;
  updateStrategyFields();
  renderStrategyHint();
});

if (token()) {
  showApp();
  refresh().catch((error) => showAuth(error.message));
} else {
  showAuth();
}

setInterval(() => {
  if (token()) refresh().catch(console.error);
}, 5000);
