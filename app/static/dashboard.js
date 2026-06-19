const moneyFormatter = new Intl.NumberFormat("ko-KR", {
  maximumFractionDigits: 0,
});

const decimalFormatter = new Intl.NumberFormat("ko-KR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const usdtFormatter = new Intl.NumberFormat("ko-KR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
});

const ids = [
  "updatedAt",
  "botStatus",
  "tradeMode",
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
];

const el = Object.fromEntries(ids.map((id) => [id, document.getElementById(id)]));

function krw(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${moneyFormatter.format(Number(value))}원`;
}

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${decimalFormatter.format(Number(value))}%`;
}

function number(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return decimalFormatter.format(Number(value));
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
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function updateStatusClass(status) {
  el.botStatus.className = "status-pill";
  if (status === "RUNNING") el.botStatus.classList.add("running");
  if (status === "ERROR") el.botStatus.classList.add("error");
  if (status === "PAUSED_BY_RISK") el.botStatus.classList.add("paused");
}

function premiumState(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return ["-", "hold"];
  }
  const premium = Number(value);
  if (premium <= -0.3) return ["BUY ZONE", "buy"];
  if (premium >= 0.3) return ["SELL ZONE", "sell"];
  return ["HOLD", "hold"];
}

function renderStatus(data) {
  el.botStatus.textContent = data.botStatus ?? "-";
  updateStatusClass(data.botStatus);
  el.tradeMode.textContent = data.tradeMode ?? "-";
  el.lastSignal.textContent = data.lastSignal ?? "-";
  el.lastSignalAt.textContent = shortDate(data.lastSignalAt);
  el.premiumRate.textContent = percent(data.premiumRate);

  const [stateText, stateClass] = premiumState(data.premiumRate);
  el.premiumState.textContent = stateText;
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
  el.updatedAt.textContent = `Updated ${new Date().toLocaleTimeString("ko-KR")}`;
}

function renderTrades(trades) {
  if (!Array.isArray(trades) || trades.length === 0) {
    el.tradeRows.innerHTML = '<tr><td colspan="5" class="empty">No trades</td></tr>';
    return;
  }

  el.tradeRows.innerHTML = trades
    .map((trade) => {
      const profit = Number(trade.profit ?? 0);
      const profitClass = profit >= 0 ? "positive" : "negative";
      return `
        <tr>
          <td>${shortDate(trade.created_at)}</td>
          <td>${trade.side}</td>
          <td>${krw(trade.price)}</td>
          <td>${usdt(trade.volume)}</td>
          <td class="${profitClass}">${krw(profit)}</td>
        </tr>
      `;
    })
    .join("");
}

async function refresh() {
  const [statusResponse, tradesResponse] = await Promise.all([
    fetch("/status"),
    fetch("/trades?limit=10"),
  ]);

  if (!statusResponse.ok) throw new Error("Failed to load status");
  if (!tradesResponse.ok) throw new Error("Failed to load trades");

  renderStatus(await statusResponse.json());
  renderTrades(await tradesResponse.json());
}

async function command(path) {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) throw new Error(`Command failed: ${path}`);
  renderStatus(await response.json());
  await refresh();
}

el.startButton.addEventListener("click", () => command("/bot/start").catch(console.error));
el.stopButton.addEventListener("click", () => command("/bot/stop").catch(console.error));

refresh().catch(console.error);
setInterval(() => refresh().catch(console.error), 5000);
