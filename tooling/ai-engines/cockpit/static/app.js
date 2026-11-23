/* Naqex Quant Pod Local Control Room — Zero-Dependency Interactive Client */
(() => {
  "use strict";

  const PALETTE = {
    POD_COMPOSITE: "#e6ebf5",
    S1_PROP_FX_IDX: "#3b82f6",
    S2_CRYPTO_SPOT: "#f59e0b",
    S3A_FUND_CARRY: "#16c784",
    S3B_MACRO_ETF: "#06b6d4",
    S4_EXTRA: "#a855f7",
    S5_EXTRA: "#ec4899",
  };

  const state = {
    summary: null,
    alloc: null,
    telemetry: null,
    activeSeries: new Set(["POD_COMPOSITE", "S1_PROP_FX_IDX", "S2_CRYPTO_SPOT", "S3A_FUND_CARRY", "S3B_MACRO_ETF"]),
  };

  const $ = (id) => document.getElementById(id);
  const fmtUSD = (v) => `${Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })} USD`;
  const fmtVND = (v) => `${Math.round(Number(v || 0)).toLocaleString("vi-VN")} VND`;
  const fmtPct = (v, sign = true) => {
    const n = Number(v || 0);
    return `${sign && n > 0 ? "+" : ""}${n.toFixed(2)}%`;
  };

  async function fetchJson(url) {
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
    return resp.json();
  }

  function seriesColor(key, idx) {
    if (PALETTE[key]) return PALETTE[key];
    const extras = ["#a855f7", "#ec4899", "#84cc16", "#f97316"];
    return extras[idx % extras.length];
  }

  function renderTopAndKPIs() {
    const s = state.summary;
    const a = state.alloc;
    const t = state.telemetry;

    if (s) {
      const seal = s.safety_seal || {};
      $("seal-badge").textContent = `HOLDOUT 2025+ SEALED (${seal.holdout_lock_sha16 || "—"}) · OrderSend=${seal.order_send_count ?? 0}`;
      const snapMeta = (s.pod_snapshot && s.pod_snapshot.meta) || {};
      $("top-policy").textContent = snapMeta.active_policy || "ERC_Capped35";
      $("top-mt5").textContent = (t && t.mt5_heartbeat && t.mt5_heartbeat.status) || snapMeta.mt5_heartbeat || "STANDBY";
      const nextNews = (t && t.upcoming_red_news && t.upcoming_red_news[0]) || null;
      $("top-news").textContent = nextNews
        ? `${nextNews.utc_iso} (${nextNews.ccy} ${nextNews.event})`
        : (snapMeta.next_red_news || "—");

      const ho = (s.registry && s.registry.one_time_holdout_2025_2026) || {};
      $("kpi-holdout").textContent = ho.engines_positive ? `${ho.engines_positive} GO` : "GO";
      $("kpi-engines").textContent = ho.PORT_7E_verdict || `${(s.registry && s.registry.engines_count) || 9} engines frozen`;

      const be = (s.red_team_stress && s.red_team_stress.portfolio_breakeven) || {};
      const be7 = be.PORT_7E ? `${be.PORT_7E.breakeven_mult}×` : "—";
      const be9 = be.PORT_9E ? `${be.PORT_9E.breakeven_mult}×` : "—";
      $("kpi-be").textContent = `${be7} / ${be9}`;
    }

    if (a && a.available) {
      const pm = a.pod_composite_metrics || {};
      $("kpi-cagr").textContent = fmtPct(pm.cagr_pct);
      $("kpi-window").textContent = `${a.window.start} .. ${a.window.end} (${a.window.business_days}d)`;
      $("kpi-sharpe").textContent = `${Number(pm.sharpe || 0).toFixed(2)} / ${Number(pm.calmar || 0).toFixed(2)}`;
      $("kpi-dd").textContent = `MaxDD: -${Number(pm.max_dd_pct || 0).toFixed(2)}%`;
    }

    if (t) {
      $("kpi-live").textContent = t.mt5_heartbeat.status;
      $("kpi-shadow").textContent = `Crypto Shadow: ${t.crypto_shadow.status}`;
    }
  }

  function renderSleeveTogglesAndTable() {
    const a = state.alloc;
    if (!a || !a.available) return;

    const allKeys = ["POD_COMPOSITE", ...a.sleeve_order];
    const tog = $("sleeve-toggles");
    tog.innerHTML = "";
    allKeys.forEach((k, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `pill ${state.activeSeries.has(k) ? "active" : ""}`;
      btn.style.borderLeft = `3px solid ${seriesColor(k, idx)}`;
      btn.textContent = k.replace("POD_COMPOSITE", "POD");
      btn.onclick = () => {
        if (state.activeSeries.has(k)) {
          if (state.activeSeries.size > 1) state.activeSeries.delete(k);
        } else {
          state.activeSeries.add(k);
        }
        renderSleeveTogglesAndTable();
        renderEquityAndDDCharts();
      };
      tog.appendChild(btn);
    });

    const snapLights = {};
    if (state.summary && state.summary.pod_snapshot && Array.isArray(state.summary.pod_snapshot.sleeves)) {
      state.summary.pod_snapshot.sleeves.forEach((row) => {
        snapLights[row.sleeve] = row;
      });
    }

    const tbody = $("tbl-sleeves").querySelector("tbody");
    tbody.innerHTML = "";
    a.sleeves.forEach((sl) => {
      const snap = snapLights[sl.sleeve_id];
      const light = snap ? snap.traffic_light : "DEV_SEALED";
      const lightCls = light === "GREEN" ? "tag-green" : light === "AMBER" ? "tag-amber" : light === "RED" ? "tag-red" : "";
      const lightDetail = snap ? `${light} (${snap.cusum_sigma})` : light;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="mono strong">${sl.sleeve_id}</td>
        <td class="mono">${sl.strategy_name}</td>
        <td class="num mono">${Number(sl.default_weight_pct).toFixed(1)}%</td>
        <td class="num mono ${sl.cagr_pct >= 0 ? "pos" : "neg"}">${fmtPct(sl.cagr_pct)}</td>
        <td class="num mono">${Number(sl.ann_vol_pct).toFixed(2)}%</td>
        <td class="num mono">${Number(sl.sharpe).toFixed(2)}</td>
        <td class="num mono neg">-${Number(sl.max_dd_pct).toFixed(2)}%</td>
        <td class="num mono">${Number(sl.calmar).toFixed(2)}</td>
        <td><span class="tag ${lightCls}">${lightDetail}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderEquityAndDDCharts() {
    const a = state.alloc;
    if (!a || !a.available || !a.dates.length) return;

    const dates = a.dates;
    const keys = ["POD_COMPOSITE", ...a.sleeve_order].filter((k) => state.activeSeries.has(k) && a.equity_curves[k]);
    const W = 820, HE = 230, HD = 120, padL = 48, padR = 14, padT = 12, padB = 22;
    const plotW = W - padL - padR;

    let minE = Infinity, maxE = -Infinity, minD = -1.0;
    keys.forEach((k) => {
      a.equity_curves[k].forEach((v) => { if (v < minE) minE = v; if (v > maxE) maxE = v; });
      a.underwater_dd_pct[k].forEach((v) => { if (v < minD) minD = v; });
    });
    if (!isFinite(minE) || minE === maxE) { minE = 90; maxE = 110; }
    const padRange = (maxE - minE) * 0.06;
    minE -= padRange; maxE += padRange;

    const xOf = (i) => padL + (i / Math.max(1, dates.length - 1)) * plotW;
    const yE = (v) => padT + (1 - (v - minE) / (maxE - minE)) * (HE - padT - padB);
    const yD = (v) => 10 + (v / Math.min(-0.5, minD)) * (HD - 26);

    const svgE = $("svg-equity");
    const svgD = $("svg-dd");
    let hE = "", hD = "";

    // Gridlines Equity
    for (let g = 0; g <= 4; g++) {
      const val = minE + (g / 4) * (maxE - minE);
      const y = yE(val);
      hE += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W - padR}" y2="${y.toFixed(1)}" stroke="#1e2738" stroke-width="1"/>`;
      hE += `<text x="${padL - 6}" y="${(y + 4).toFixed(1)}" fill="#8b97ad" font-size="10" text-anchor="end" font-family="Consolas,monospace">${val.toFixed(0)}</text>`;
    }
    // Gridlines DD
    [0, minD * 0.5, minD].forEach((dv) => {
      const y = yD(dv);
      hD += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${W - padR}" y2="${y.toFixed(1)}" stroke="#1e2738" stroke-width="1"/>`;
      hD += `<text x="${padL - 6}" y="${(y + 4).toFixed(1)}" fill="#8b97ad" font-size="10" text-anchor="end" font-family="Consolas,monospace">${dv.toFixed(1)}%</text>`;
    });

    // Series polylines
    keys.forEach((k, idx) => {
      const col = seriesColor(k, idx);
      const sw = k === "POD_COMPOSITE" ? 2.2 : 1.4;
      const ptsE = a.equity_curves[k].map((v, i) => `${xOf(i).toFixed(1)},${yE(v).toFixed(1)}`).join(" ");
      const ptsD = a.underwater_dd_pct[k].map((v, i) => `${xOf(i).toFixed(1)},${yD(v).toFixed(1)}`).join(" ");
      hE += `<polyline fill="none" stroke="${col}" stroke-width="${sw}" points="${ptsE}"/>`;
      hD += `<polyline fill="none" stroke="${col}" stroke-width="${sw}" points="${ptsD}"/>`;
    });

    // X-axis date ticks
    [0, Math.floor(dates.length * 0.33), Math.floor(dates.length * 0.66), dates.length - 1].forEach((i) => {
      const x = xOf(i);
      hE += `<text x="${x.toFixed(1)}" y="${HE - 4}" fill="#8b97ad" font-size="10" text-anchor="middle" font-family="Consolas,monospace">${dates[i]}</text>`;
    });

    // Crosshair lines
    hE += `<line id="xhair-e" x1="-10" y1="${padT}" x2="-10" y2="${HE - padB}" stroke="#4b5563" stroke-dasharray="3,3" stroke-width="1"/>`;
    hD += `<line id="xhair-d" x1="-10" y1="8" x2="-10" y2="${HD - 12}" stroke="#4b5563" stroke-dasharray="3,3" stroke-width="1"/>`;

    svgE.innerHTML = hE;
    svgD.innerHTML = hD;

    const handleMove = (ev) => {
      const rect = svgE.getBoundingClientRect();
      const relX = ((ev.clientX - rect.left) / Math.max(1, rect.width)) * W;
      const frac = Math.max(0, Math.min(1, (relX - padL) / plotW));
      const idx = Math.round(frac * (dates.length - 1));
      const xPos = xOf(idx).toFixed(1);
      const xe = $("xhair-e"), xd = $("xhair-d");
      if (xe) { xe.setAttribute("x1", xPos); xe.setAttribute("x2", xPos); }
      if (xd) { xd.setAttribute("x1", xPos); xd.setAttribute("x2", xPos); }
      const parts = keys.map((k) => `${k.replace("POD_COMPOSITE", "POD")}: ${a.equity_curves[k][idx].toFixed(1)} (${a.underwater_dd_pct[k][idx].toFixed(2)}%)`);
      $("chart-tooltip").textContent = `${dates[idx]}  |  ${parts.join("  ·  ")}`;
    };
    svgE.onmousemove = handleMove;
    svgD.onmousemove = handleMove;
  }

  function renderCorrelationHeatmap() {
    const a = state.alloc;
    const wrap = $("corr-heatmap");
    if (!a || !a.available) { wrap.innerHTML = "<div class='sub'>No sleeve data</div>"; return; }
    const names = a.sleeve_order;
    const cm = a.correlation_matrix || {};

    const bgFor = (r) => {
      const v = Math.max(-1, Math.min(1, Number(r || 0)));
      if (Math.abs(v) > 0.999) return "#1e293b";
      if (v >= 0) {
        const alpha = Math.min(0.65, v * 0.8);
        return `rgba(245, 158, 11, ${alpha.toFixed(2)})`;
      }
      const alpha = Math.min(0.65, Math.abs(v) * 0.9);
      return `rgba(59, 130, 246, ${alpha.toFixed(2)})`;
    };

    let html = `<table class="hm-table"><thead><tr><th>Sleeve</th>${names.map((n) => `<th>${n.replace(/_/g, " ").slice(0, 10)}</th>`).join("")}</tr></thead><tbody>`;
    names.forEach((rName) => {
      html += `<tr><th>${rName}</th>`;
      names.forEach((cName) => {
        const val = Number((cm[rName] && cm[rName][cName]) || 0);
        html += `<td style="background:${bgFor(val)}">${val >= 0 ? "+" : ""}${val.toFixed(3)}</td>`;
      });
      html += "</tr>";
    });
    html += "</tbody></table>";
    wrap.innerHTML = html;
  }

  function renderTelemetry() {
    const t = state.telemetry;
    if (!t) return;
    $("tel-hb-status").textContent = t.mt5_heartbeat.status;
    $("tel-hb-detail").textContent = t.mt5_heartbeat.source || "Awaiting naqex_heartbeat.json";

    $("tel-sp-status").textContent = `${t.mt5_live_spreads.status} (${t.mt5_live_spreads.count})`;
    $("tel-sp-detail").textContent = t.mt5_live_spreads.latest
      ? JSON.stringify(t.mt5_live_spreads.latest).slice(0, 72)
      : "No mt5_live_spread_log.jsonl rows yet";

    $("tel-cr-status").textContent = `${t.crypto_shadow.status} (${t.crypto_shadow.count})`;
    $("tel-cr-detail").textContent = t.crypto_shadow.latest
      ? JSON.stringify(t.crypto_shadow.latest).slice(0, 72)
      : "No crypto_shadow_log.jsonl rows yet";

    $("tel-rt-status").textContent = t.mt5_realtick_tca.status;
    $("tel-rt-detail").textContent = t.ftmo_live_specs_available
      ? "FTMO Live Specs JSON loaded"
      : "FTMO Live Specs pending capture";

    const tbody = $("tbl-news").querySelector("tbody");
    tbody.innerHTML = "";
    (t.upcoming_red_news || []).forEach((ev) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td class="mono">${ev.utc_iso}</td><td class="num mono">+${ev.hours_away}h</td><td class="mono strong">${ev.ccy}</td><td>${ev.event}</td>`;
      tbody.appendChild(tr);
    });
  }

  async function refreshCalculator() {
    const capVnd = Number($("inp-cap-vnd").value || 250000000);
    const fx = Number($("inp-fx").value || 25500);
    const propUsd = Number($("inp-prop-usd").value || 10000);
    const prof = $("inp-profile").value || "balanced";
    const cm = Number($("slider-stress").value || 1.0);

    $("stress-mult-label").textContent = `${cm.toFixed(2)}×`;
    document.querySelectorAll(".js-mult").forEach((el) => { el.textContent = `${cm.toFixed(2)}×`; });

    const url = `/api/vnd-calculator?capital_vnd=${encodeURIComponent(capVnd)}&usd_vnd=${encodeURIComponent(fx)}&prop_nominal_usd=${encodeURIComponent(propUsd)}&risk_profile=${encodeURIComponent(prof)}&cost_mult=${encodeURIComponent(cm)}`;
    const d = await fetchJson(url);

    // Stress cards
    const p7 = d.red_team_stress.PORT_7E;
    const p9 = d.red_team_stress.PORT_9E;
    $("stress-p7-ann").textContent = fmtPct(p7.ann_pct);
    $("stress-p7-ann").className = `mini-val mono ${p7.ann_pct >= 0 ? "pos" : "neg"}`;
    $("stress-p7-meta").textContent = `DD ${p7.peak_dd_pct}% · Cal ${p7.calmar} · BE ${p7.breakeven_mult}×`;

    $("stress-p9-ann").textContent = fmtPct(p9.ann_pct);
    $("stress-p9-ann").className = `mini-val mono ${p9.ann_pct >= 0 ? "pos" : "neg"}`;
    $("stress-p9-meta").textContent = `DD ${p9.peak_dd_pct}% · Cal ${p9.calmar} · BE ${p9.breakeven_mult}×`;

    // Engine stress bars
    const bars = $("engine-stress-bars");
    bars.innerHTML = "";
    (d.red_team_stress.per_engine || []).forEach((e) => {
      const pct = Math.min(100, Math.max(6, (e.breakeven_mult / 4.0) * 100));
      const col = e.survives ? "var(--green)" : "var(--red)";
      const row = document.createElement("div");
      row.className = "bar-row mono";
      row.innerHTML = `
        <span>${e.engine}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct.toFixed(0)}%;background:${col}"></div></div>
        <span class="num ${e.survives ? "pos" : "neg"}">${e.est_net_usd >= 0 ? "+" : ""}${e.est_net_usd} USD</span>
      `;
      bars.appendChild(row);
    });

    // Comfort verdict
    const assess = d.owner_profile_assessment;
    const badge = $("calc-verdict-badge");
    badge.textContent = assess.verdict;
    badge.className = `tag ${assess.verdict === "COMFORT_GREEN" ? "tag-green" : assess.verdict === "CAUTION_AMBER" ? "tag-amber" : "tag-red"}`;
    $("calc-tier-note").textContent = `${assess.capital_tier} · Ngưỡng xanh <= ${assess.green_dd_cap_pct}% / vàng <= ${assess.amber_dd_cap_pct}%`;

    // Pain table
    const p = d.absolute_pain_table;
    $("tbl-pain").innerHTML = `
      <tr><td>Rủi ro 1 lệnh (1R Stop Loss)</td><td class="num mono">${fmtUSD(p.one_r_stop_usd)}</td><td class="num mono">${fmtVND(p.one_r_stop_vnd)}</td></tr>
      <tr><td>Trả lại lãi thả nổi 2R (Profit Giveback test)</td><td class="num mono warn">${fmtUSD(p.profit_giveback_2r_usd)}</td><td class="num mono warn">${fmtVND(p.profit_giveback_2r_vnd)}</td></tr>
      <tr><td>Lỗ ngày tối đa kỳ vọng (Daily DD)</td><td class="num mono neg">-${fmtUSD(p.daily_dd_usd)}</td><td class="num mono neg">-${fmtVND(p.daily_dd_vnd)}</td></tr>
      <tr><td>Drawdown đỉnh kỳ vọng (${p.expected_peak_dd_pct}%)</td><td class="num mono neg strong">-${fmtUSD(p.expected_peak_dd_usd)}</td><td class="num mono neg strong">-${fmtVND(p.expected_peak_dd_vnd)}</td></tr>
      <tr><td>Kỳ vọng lãi ròng năm (Own Book)</td><td class="num mono pos strong">+${fmtUSD(p.expected_annual_return_usd)}</td><td class="num mono pos strong">+${fmtVND(p.expected_annual_return_vnd)}</td></tr>
    `;

    // Crossover
    const xo = d.crossover;
    $("xo-phase").textContent = xo.recommended_phase;
    $("xo-pct").textContent = `${xo.crossover_progress_pct}%`;
    $("xo-bar").style.width = `${Math.min(100, Math.max(0, xo.crossover_progress_pct))}%`;
    $("xo-meta").textContent = `Own: ${fmtUSD(xo.expected_own_net_annual_usd)}/yr vs Prop: ${fmtUSD(xo.expected_prop_net_annual_usd)}/yr · Ngưỡng giao cắt: ${fmtUSD(xo.crossover_equity_usd)} (${fmtVND(xo.crossover_equity_vnd)})`;

    // Own-book sleeve allocation
    $("tbl-own-alloc").innerHTML = (d.own_book_sleeve_allocation || []).map((r) => `
      <tr><td>${r.label}</td><td class="num mono">${r.weight_pct.toFixed(1)}%</td><td class="num mono">${fmtUSD(r.usd)}</td><td class="num mono">${fmtVND(r.vnd)}</td></tr>
    `).join("");
  }

  async function refreshRebalancer() {
    const mode = $("inp-rebal-mode").value || "M5_VOL_PARITY_TREND_GUARD";
    const capVnd = Number($("inp-cap-vnd").value || 250000000);
    const fx = Number($("inp-fx").value || 25500);
    const eqUsd = Math.max(1000, Math.round(capVnd / fx));
    const plan = await fetchJson(`/api/rebalancer?mode=${encodeURIComponent(mode)}&equity_usd=${eqUsd}`);
    if (plan.available === false) {
      $("rebal-meta").textContent = `Rebalancer standby: ${plan.reason}`;
      return;
    }
    $("rebal-meta").textContent = `As-Of ${plan.as_of_date} · Equity ${fmtUSD(plan.equity_usd)} · Gross ${plan.gross_exposure_pct}% · Cash ${plan.idle_cash_pct}% (${fmtUSD(plan.idle_cash_usd)}) · Tickets ${plan.ticket_count} · OrderSend=${plan.order_send_count}`;
    const tbody = $("tbl-rebal").querySelector("tbody");
    tbody.innerHTML = (plan.allocations || []).map((a) => {
      const actCls = a.action === "BUY" ? "tag-green" : (a.action === "SELL" || a.action === "SHORT") ? "tag-red" : "";
      const tgCls = a.trend_guard === "ABOVE_SMA200" ? "pos" : "warn";
      return `
        <tr>
          <td class="mono strong">${a.symbol}</td>
          <td class="mono">${a.bucket}</td>
          <td class="num mono">${a.price_usd}</td>
          <td class="mono ${tgCls}">${a.trend_guard === "ABOVE_SMA200" ? "> SMA200" : "<= SMA200 (25%)"}</td>
          <td class="num mono">${a.target_weight_pct.toFixed(2)}%</td>
          <td class="num mono">${a.target_shares}</td>
          <td><span class="tag ${actCls}">${a.action}</span></td>
        </tr>
      `;
    }).join("");
  }

  async function refreshAll() {
    const [summary, alloc, telemetry] = await Promise.all([
      fetchJson("/api/summary"),
      fetchJson("/api/allocations"),
      fetchJson("/api/live-telemetry"),
    ]);
    state.summary = summary;
    state.alloc = alloc;
    state.telemetry = telemetry;
    renderTopAndKPIs();
    renderSleeveTogglesAndTable();
    renderEquityAndDDCharts();
    renderCorrelationHeatmap();
    renderTelemetry();
    await Promise.all([refreshCalculator(), refreshRebalancer()]);
  }

  window.addEventListener("DOMContentLoaded", () => {
    $("btn-refresh").addEventListener("click", () => refreshAll());
    ["inp-cap-vnd", "inp-fx", "inp-prop-usd", "inp-profile", "slider-stress"].forEach((id) => {
      $(id).addEventListener("input", () => refreshCalculator());
    });
    $("inp-rebal-mode").addEventListener("change", () => refreshRebalancer());
    refreshAll().catch((err) => {
      $("chart-tooltip").textContent = `Load error: ${err.message}`;
    });
  });
})();
