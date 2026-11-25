/* Naqex Quant Pod Local Control Room — Zero-Dependency Interactive Client */
(() => {
  "use strict";

  const PALETTE = {
    POD_COMPOSITE: "#e6ebf5",
    S1_PROP_FX_IDX: "#3b82f6",
    S2_CRYPTO_SPOT: "#f59e0b",
    S3A_FUND_CARRY: "#16c784",
    S3B_MACRO_ETF: "#06b6d4",
    S4_ETF40_MULTIFACTOR: "#a855f7",
    S5_CME_FUTURES_PROP: "#ec4899",
  };

  const state = {
    summary: null,
    alloc: null,
    telemetry: null,
    stress: null,
    activeSeries: new Set([
      "POD_COMPOSITE",
      "S1_PROP_FX_IDX",
      "S2_CRYPTO_SPOT",
      "S3A_FUND_CARRY",
      "S3B_MACRO_ETF",
      "S4_ETF40_MULTIFACTOR",
      "S5_CME_FUTURES_PROP",
    ]),
  };

  const $ = (id) => document.getElementById(id);
  const fmtUSD = (v) => `${Number(v || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })} USD`;
  const fmtVND = (v) => `${Math.round(Number(v || 0)).toLocaleString("vi-VN")} VND`;
  const fmtPct = (v, sign = true) => {
    const n = Number(v || 0);
    return `${sign && n > 0 ? "+" : ""}${n.toFixed(2)}%`;
  };
  const escHtml = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

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

    // 1. Crypto Shadow Runner (Live L2 TCA)
    const cs = t.crypto_shadow || {};
    if (cs.status === "ACTIVE") {
      const tca = cs.tca_summary || {};
      const ok = tca.within_budget_10k !== false;
      $("tel-cr-status").textContent = `ACTIVE · Cycle #${cs.cycle_num || cs.count}`;
      $("tel-cr-status").className = `mini-val mono ${ok ? "pos" : "warn"}`;
      $("tel-cr-detail").textContent = `10k slip ${Number(tca.median_slip_10k_bps || 0).toFixed(2)}/${tca.budget_10k_bps || 5.0} bps · Med spread ${Number(tca.median_spread_bps || 0).toFixed(2)} bps · F4 ${cs.sleeve2_regime_bull ? "BULL" : "FLAT"}`;
    } else {
      $("tel-cr-status").textContent = "PENDING";
      $("tel-cr-status").className = "mini-val mono warn";
      $("tel-cr-detail").textContent = "Awaiting crypto_shadow_latest.json";
    }

    // 2. Crypto Maker Shadow Probe (M2B)
    const mk = t.crypto_maker_shadow || {};
    if (mk.status === "ACTIVE" && mk.latest) {
      const ml = mk.latest;
      $("tel-mk-status").textContent = `ACTIVE · Cycle #${mk.cycle_num || mk.count}`;
      $("tel-mk-status").className = "mini-val mono pos";
      const eff = ml.effective_cost_bps ?? ml.eff_cost_bps;
      const fr = ml.fill_rate_pct ?? ml.touch_through_fill_rate_pct;
      $("tel-mk-detail").textContent = (eff != null || fr != null)
        ? `Fill ${fr != null ? `${Number(fr).toFixed(1)}%` : "—"} · Eff Cost ${eff != null ? `${Number(eff).toFixed(2)} bps` : "—"} vs 6.15 bps M2`
        : `Captured at ${mk.timestamp_utc || "—"}`;
    } else {
      $("tel-mk-status").textContent = "PENDING";
      $("tel-mk-status").className = "mini-val mono warn";
      $("tel-mk-detail").textContent = "Awaiting crypto_maker_shadow_latest.json (M2B probe)";
    }

    // 3. MT5 Demo Account & Live Spread Monitor
    const sp = t.mt5_live_spreads || {};
    const acct = sp.demo_account || null;
    if (sp.status === "ACTIVE" && sp.latest) {
      $("tel-sp-status").textContent = `ACTIVE (${sp.count} rows)`;
      $("tel-sp-status").className = "mini-val mono pos";
      const bal = acct && acct.balance != null ? `Bal ${fmtUSD(acct.balance)}` : "";
      const eq = acct && acct.equity != null ? `Eq ${fmtUSD(acct.equity)}` : "";
      $("tel-sp-detail").textContent = `${acct && acct.server ? `${acct.server} #${acct.login}` : "MT5 Live"} · ${bal} ${eq}`.trim();
    } else if (acct) {
      $("tel-sp-status").textContent = `DEMO ${acct.login || ""} · SPREAD PENDING`;
      $("tel-sp-status").className = "mini-val mono accent";
      $("tel-sp-detail").textContent = `${acct.server || "FTMO-Demo"} · Bal ${fmtUSD(acct.balance)} · Eq ${fmtUSD(acct.equity)} · 1:${acct.leverage || 30}`;
    } else {
      $("tel-sp-status").textContent = "PENDING";
      $("tel-sp-status").className = "mini-val mono warn";
      $("tel-sp-detail").textContent = "Awaiting mt5_live_spread_log.jsonl";
    }

    // 4. MT5 Real-Tick Model=4 Matrix
    const rt = t.mt5_realtick_tca || {};
    if (rt.status === "AVAILABLE") {
      const lats = (rt.latencies_ms || []).map((x) => `${x}ms`).join("/");
      $("tel-rt-status").textContent = `Model=${rt.model ?? 4} · ${rt.engines_run || 0} EA(s)`;
      $("tel-rt-status").className = "mini-val mono accent";
      $("tel-rt-detail").textContent = `${rt.window || "—"} · Lat [${lats || "—"}] · ${t.ftmo_live_specs_available ? "Live Specs OK" : "Specs pending"}`;
    } else {
      $("tel-rt-status").textContent = "PENDING";
      $("tel-rt-status").className = "mini-val mono warn";
      $("tel-rt-detail").textContent = "Awaiting realtick_matrix_summary.json";
    }

    // Majors L2 Strip (BTC/ETH/SOL)
    const majors = cs.majors_l2 || {};
    const mParts = ["BTCUSDT", "ETHUSDT", "SOLUSDT"].filter((k) => majors[k]).map((k) => {
      const m = majors[k];
      return `${k.replace("USDT", "")} mid=${m.mid} sp=${Number(m.spread_bps || 0).toFixed(3)}bps slip10k=${Number(m.slip_10k_bps || 0).toFixed(2)}bps`;
    });
    const fundStr = cs.sleeve3a_funding_btc_ann_pct != null
      ? ` · Perp Ann Fund BTC ${fmtPct(cs.sleeve3a_funding_btc_ann_pct)} / ETH ${fmtPct(cs.sleeve3a_funding_eth_ann_pct)}`
      : "";
    $("tel-majors-strip").textContent = mParts.length
      ? `LIVE L2: ${mParts.join("  |  ")}${fundStr}`
      : "LIVE L2: pending crypto_shadow_latest.json";

    // Real-Tick Reconciliation Table
    const rtBody = $("tbl-realtick").querySelector("tbody");
    rtBody.innerHTML = "";
    const rtEngines = rt.engines || [];
    if (!rtEngines.length) {
      rtBody.innerHTML = `<tr><td colspan="5" class="mono warn">Pending MT5 Real-Tick Model=4 matrix rows...</td></tr>`;
    } else {
      rtEngines.forEach((e) => {
        const vCls = e.verdict === "MATCH" || e.verdict === "PASS" ? "tag-green" : e.verdict === "NEEDS_REVIEW" ? "tag-amber" : "tag-red";
        const latKeys = Object.keys(e.latency_curve || {}).join("/") || "—";
        const drag = e.latency_drag_50_to_250ms_usd != null ? fmtUSD(e.latency_drag_50_to_250ms_usd) : "—";
        const pyRef = e.python_ref_trades != null ? `${e.python_ref_trades} tr / ${fmtUSD(e.python_ref_net_usd)}` : "—";
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="mono strong">${e.engine_id}</td>
          <td><span class="tag ${vCls}">${e.verdict}</span></td>
          <td class="num mono">${latKeys}</td>
          <td class="num mono">${drag}</td>
          <td class="num mono">${pyRef}</td>
        `;
        rtBody.appendChild(tr);
      });
    }

    const tbody = $("tbl-news").querySelector("tbody");
    tbody.innerHTML = "";
    (t.upcoming_red_news || []).forEach((ev) => {
      const tr = document.createElement("tr");
      const cd = ev.countdown_vi || `+${ev.hours_away}h`;
      const cdCls = ev.in_blackout_window ? "tag tag-red" : (ev.hours_away <= 2 ? "warn strong" : "");
      tr.innerHTML = `<td class="mono strong">${ev.vn_iso || ev.utc_iso}</td><td class="mono">${ev.utc_iso}</td><td class="num mono"><span class="${cdCls}">${cd}</span></td><td class="mono strong">${ev.ccy}</td><td>${ev.event}</td>`;
      tbody.appendChild(tr);
    });

    // Render Live MT5 Open Positions (with real MAE / MFE pips when observed)
    const posBody = $("tbl-live-pos").querySelector("tbody");
    const openPos = (t.mt5_live_spreads && t.mt5_live_spreads.open_positions) || [];
    if (!openPos.length) {
      posBody.innerHTML = `<tr><td colspan="9" class="mono">0 vị thế mở (flat)</td></tr>`;
    } else {
      posBody.innerHTML = openPos.map((p) => {
        const maeTxt = p.mae_pips != null ? `${Number(p.mae_pips).toFixed(1)}` : "—";
        const mfeTxt = p.mfe_pips != null ? `+${Number(p.mfe_pips).toFixed(1)}` : "—";
        const mmCell = (p.mae_pips != null || p.mfe_pips != null)
          ? `<span class="neg">${maeTxt}</span> / <span class="pos">${mfeTxt}</span>`
          : "—";
        return `
        <tr>
          <td class="mono">${p.ticket}</td>
          <td class="mono strong">${p.symbol}</td>
          <td class="mono ${p.type === "BUY" ? "pos" : "neg"}">${p.type}</td>
          <td class="num mono">${Number(p.volume).toFixed(2)}</td>
          <td class="num mono">${Number(p.price_open).toFixed(3)}</td>
          <td class="num mono">${Number(p.sl).toFixed(3)}</td>
          <td class="num mono">${mmCell}</td>
          <td class="num mono">${Number(p.swap || 0).toFixed(2)}</td>
          <td class="num mono ${Number(p.profit) >= 0 ? "pos" : "neg"}">${Number(p.profit) >= 0 ? "+" : ""}${Number(p.profit).toFixed(2)}</td>
        </tr>`;
      }).join("");
    }

    // Render Recent Execution Audit CSV rows
    const audBody = $("tbl-exec-audit").querySelector("tbody");
    const audRows = (t.mt5_live_spreads && t.mt5_live_spreads.exec_audit_recent) || [];
    if (!audRows.length) {
      audBody.innerHTML = `<tr><td colspan="8" class="mono">Chưa có dòng khớp lệnh nào</td></tr>`;
    } else {
      audBody.innerHTML = audRows.slice(-8).reverse().map((r) => `
        <tr>
          <td class="mono">${r.event_type || "—"}</td>
          <td class="mono strong">${r.symbol || "—"}</td>
          <td class="mono">${r.side || "—"}</td>
          <td class="num mono">${r.lots || "—"}</td>
          <td class="num mono">${r.signal_price || "—"}</td>
          <td class="num mono">${r.fill_price || "—"}</td>
          <td class="num mono">${r.sl_price || "—"}</td>
          <td class="num mono">${r.latency_ms || "—"}</td>
        </tr>
      `).join("");
    }

    // Render 2-step emergency cover status
    if (t.emergency_cover) {
      renderEmergencyState(t.emergency_cover);
    }
  }

  let coverOpened = false;

  function renderEmergencyState(st) {
    const badge = $("emg-state-badge");
    const note = $("emg-status-note");
    const stateStr = st.state || "NORMAL_COVER_CLOSED";
    badge.textContent = stateStr;
    badge.className = `tag ${stateStr.startsWith("ARMED_") ? "tag-red" : "tag-green"}`;
    const localOnlyWarn = (stateStr.startsWith("ARMED_") && st.mt5_bridge_written === false)
      ? " · ⚠️ CHỈ GHI NHẬT KÝ CỤC BỘ (CHƯA GỬI SANG MT5/VPS — mở RDP nếu cần đóng lệnh thật!)"
      : (st.mt5_bridge_written === true ? " · Đã ghi cờ cầu nối MT5 (chờ Orchestrator xác nhận)" : "");
    note.textContent = `Trạng thái: ${stateStr} · Action: ${st.action || "NONE"} · Updated: ${st.updated_utc || "—"} · Lý do: ${st.reason || "—"}${localOnlyWarn}`;
  }

  async function submitEmergencyCover() {
    const action = $("inp-emg-action").value;
    const code = ($("inp-emg-code").value || "").trim().toUpperCase();
    const reason = ($("inp-emg-reason").value || "").trim();
    const res = await fetch("/api/emergency-cover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cover_opened: coverOpened, action, confirm_code: code, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      $("emg-status-note").textContent = `Bị chặn (fail-closed): ${data.error || "invalid request"}`;
      return;
    }
    renderEmergencyState(data);
    $("inp-emg-code").value = "";
    coverOpened = false;
    $("emg-controls").classList.add("hidden");
    $("btn-toggle-cover").textContent = "Lật nắp bảo vệ";
  }

  async function runPropTermsAudit() {
    const firm = $("inp-pta-firm").value;
    const termsText = $("inp-pta-text").value || "";
    const useTypesafe = Boolean($("inp-pta-typesafe").checked);
    $("pta-output").textContent = useTypesafe ? "Đang gọi TypeSafe jev-1.14.0 kiểm toán..." : "Đang đọc chuẩn baseline...";
    const res = await fetch("/api/prop-terms-audit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ firm, terms_text: termsText, use_typesafe: useTypesafe }),
    });
    const data = await res.json();
    const b = $("pta-badge");
    if (!res.ok) {
      b.textContent = "FAIL_CLOSED";
      b.className = "tag tag-red";
      $("pta-output").textContent = JSON.stringify(data, null, 2);
      return;
    }
    b.textContent = data.verdict || data.mode || "OK";
    b.className = `tag ${data.verdict === "DRIFT_DETECTED_REVIEW_REQUIRED" ? "tag-red" : "tag-green"}`;
    $("pta-output").textContent = JSON.stringify(data, null, 2);
  }

  async function refreshStress() {
    const capVnd = Number($("inp-cap-vnd").value || 1275000000);
    const fx = Number($("inp-fx").value || 25500);
    const capUsd = Math.max(1000, capVnd / Math.max(1000, fx));
    const st = await fetchJson(`/api/stress?capital_usd=${encodeURIComponent(capUsd.toFixed(2))}&usd_vnd=${encodeURIComponent(fx)}`);
    state.stress = st;

    $("stress-cap-echo").textContent = `${Math.round(capUsd).toLocaleString("en-US")} USD · ${(capVnd / 1e6).toFixed(1)} tr VND`;

    const bsBody = $("tbl-blackswan").querySelector("tbody");
    const mpBody = $("tbl-multiprop").querySelector("tbody");
    if (!st.available) {
      bsBody.innerHTML = `<tr><td colspan="6" class="mono warn">Black-Swan stress report pending...</td></tr>`;
      mpBody.innerHTML = `<tr><td colspan="7" class="mono warn">Multi-Prop budget matrix pending...</td></tr>`;
      return;
    }

    if (st.cex_group_cap_recommendation) {
      const rec = st.cex_group_cap_recommendation;
      $("stress-cex-cap-note").textContent = `CEX Group Cap <= ${rec.max_combined_cex_pct}% -> -50% CEX còn -${rec.capped_cex50_loss.usd.toLocaleString("en-US", { maximumFractionDigits: 0 })} USD (-${rec.capped_cex50_loss.vnd_m} tr)`;
    }

    bsBody.innerHTML = (st.black_swan_matrix || []).map((r) => {
      const vCls = r.verdict === "COMFORT_GREEN" ? "tag-green" : r.verdict === "CAUTION_AMBER" ? "tag-amber" : "tag-red";
      const fmtHit = (h) => `-${Math.round(h.usd).toLocaleString("en-US")} USD / -${h.vnd_m} tr`;
      return `
        <tr>
          <td class="mono strong">${r.allocator}</td>
          <td class="num mono ${r.cex_weight_pct > 50 ? "neg" : r.cex_weight_pct > 25 ? "warn" : "pos"}">${r.cex_weight_pct.toFixed(1)}%</td>
          <td class="num mono warn">${fmtHit(r.cex_30)}</td>
          <td class="num mono neg strong">${fmtHit(r.cex_50)}</td>
          <td class="num mono">${fmtHit(r.corr085_p99)}</td>
          <td><span class="tag ${vCls}">${r.verdict}</span></td>
        </tr>
      `;
    }).join("");

    mpBody.innerHTML = (st.multi_prop_highlights || []).map((m) => `
      <tr>
        <td class="mono strong">${m.budget_usd.toLocaleString("en-US")} USD</td>
        <td class="mono">${m.architecture}</td>
        <td class="mono">${m.profile}</td>
        <td class="num mono ${m.wipeout_pct <= 0.5 ? "pos" : m.wipeout_pct <= 1.5 ? "warn" : "neg"}">${m.wipeout_pct.toFixed(1)}%</td>
        <td class="num mono ${m.double_fail_pct <= 5.0 ? "pos" : "neg"}">${m.double_fail_pct.toFixed(1)}%</td>
        <td class="num mono pos">+${m.ev_per_fee.toFixed(2)}x</td>
        <td class="num mono">${m.ob_60m_raw}</td>
      </tr>
    `).join("");
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

  async function refreshPropMetrix() {
    const sel = $("inp-mx-program");
    if (!sel) return;
    const prog = sel.value || "ftmo_free_trial_10k";
    const d = await fetchJson(`/api/prop-metrix?program=${encodeURIComponent(prog)}`);
    const src = d.source || {};
    const ac = d.account || {};
    const buf = d.buffers || {};

    const srcBadge = $("mx-source-badge");
    const ageTxt = src.age_sec != null ? ` · ${src.age_sec}s` : "";
    srcBadge.textContent = `${src.label || "STANDBY"}${ageTxt}`;
    srcBadge.className = `tag ${src.status === "OK" ? "tag-green" : src.status === "CACHED" ? "tag-amber" : "tag-red"}`;

    $("mx-acct-line").textContent = `Số dư: ${fmtUSD(ac.balance_usd)} · Equity: ${fmtUSD(ac.equity_usd)} · Lệnh mở: ${ac.open_positions} · Thiếu SL: ${ac.orphan_no_sl} · Chế độ: ${ac.regime}`;

    $("mx-buf-daily").textContent = fmtUSD(buf.permitted_daily_loss_usd);
    $("mx-buf-daily").className = `mini-val mono ${buf.permitted_daily_loss_usd <= buf.daily_limit_usd * 0.25 ? "neg" : "pos"}`;
    $("mx-buf-daily-sub").textContent = `Ngưỡng ngày: -${fmtUSD(buf.daily_limit_usd)} · Mốc ngày: ${fmtUSD(ac.day_anchor_usd)}`;

    $("mx-buf-max").textContent = fmtUSD(buf.permitted_max_loss_usd);
    $("mx-buf-max").className = `mini-val mono ${buf.permitted_max_loss_usd <= buf.max_limit_usd * 0.25 ? "neg" : "pos"}`;
    $("mx-buf-max-sub").textContent = `Ngưỡng tổng: -${fmtUSD(buf.max_limit_usd)} · Vốn đầu: ${fmtUSD(ac.initial_usd)}`;

    const tPnl = Number(ac.today_pnl_usd || 0);
    $("mx-buf-today").textContent = `${tPnl >= 0 ? "+" : ""}${fmtUSD(tPnl)} (${ac.today_pnl_pct >= 0 ? "+" : ""}${ac.today_pnl_pct}%)`;
    $("mx-buf-today").className = `mini-val mono ${tPnl >= 0 ? "pos" : "neg"}`;
    const totPnl = Number(ac.total_pnl_usd || 0);
    $("mx-buf-today-sub").textContent = `Tổng PnL: ${totPnl >= 0 ? "+" : ""}${fmtUSD(totPnl)} (${ac.total_pnl_pct >= 0 ? "+" : ""}${ac.total_pnl_pct}%)`;

    const stLabel = { PASS: "ĐẠT", PENDING: "CHỜ", IN_PROGRESS: "ĐANG CHẠY", FUNDED: "FUNDED", BREACH: "VI PHẠM" };
    const stCls = { PASS: "tag-green", PENDING: "tag-amber", IN_PROGRESS: "tag-amber", FUNDED: "tag-green", BREACH: "tag-red" };
    const rBody = $("tbl-mx-rules").querySelector("tbody");
    rBody.innerHTML = (d.rules || []).map((r) => `
      <tr>
        <td>${r.label}</td>
        <td class="num mono">${r.value_text}</td>
        <td><span class="tag ${stCls[r.status] || ""}">${stLabel[r.status] || r.status}</span></td>
      </tr>
    `).join("");

    // Render compact 4-layer R4 -> R3 -> R2 -> R1 risk attribution strip
    const ra = d.risk_attribution || null;
    const raLayersEl = $("mx-risk-layers");
    if (ra && raLayersEl) {
      const act = ra.active_label || "OK";
      const actLayer = ra.layers && ra.layers[act];
      const actStatus = act === "OK" ? "OK" : ((actLayer && actLayer.status) || "WARN");
      const actBadge = $("mx-risk-active");
      if (actBadge) {
        actBadge.textContent = act === "OK" ? "OK · 4/4 SẠCH" : `${act} · ${actStatus === "ALERT" ? "CẢNH BÁO" : "LƯU Ý"}`;
        actBadge.className = `tag ${act === "OK" ? "tag-green" : actStatus === "ALERT" ? "tag-red" : "tag-amber"}`;
      }
      const hl = $("mx-risk-headline");
      if (hl) hl.textContent = ra.headline_vi || "";
      const order = ra.check_order || ["R4", "R3", "R2", "R1"];
      const layerTag = { OK: "tag-green", WARN: "tag-amber", ALERT: "tag-red" };
      const layerTxt = { OK: "XANH", WARN: "LƯU Ý", ALERT: "ĐỎ" };
      raLayersEl.innerHTML = order.map((code) => {
        const item = (ra.layers && ra.layers[code]) || { code, title: code, status: "OK", detail: "—" };
        const st = item.status || "OK";
        const cellCls = st === "ALERT" ? "is-alert" : st === "WARN" ? "is-warn" : "";
        return `<div class="mx-risk-cell ${cellCls}">
          <div class="mx-risk-cell-top">
            <strong class="mono">${item.code} · ${item.title}</strong>
            <span class="tag ${layerTag[st] || "tag-green"}">${layerTxt[st] || st}</span>
          </div>
          <div class="mx-risk-cell-detail">${item.detail || ""}</div>
        </div>`;
      }).join("");
    }

    const tRule = (d.rules || []).find((r) => r.id === "profit_target");
    const tBox = $("mx-target-box");
    if (tRule && tRule.progress_pct != null) {
      tBox.classList.remove("hidden");
      $("mx-target-pct").textContent = `${tRule.progress_pct}%`;
      $("mx-target-bar").style.width = `${Math.min(100, Math.max(0, tRule.progress_pct))}%`;
    } else {
      tBox.classList.add("hidden");
    }

    const cal = d.calendar || {};
    $("mx-cal-month").textContent = cal.month_label || "—";
    const grid = $("mx-cal-grid");
    grid.innerHTML = (cal.cells || []).map((c) => {
      if (c.empty) return `<div class="mx-cell empty"></div>`;
      if (!c.has_trade) return `<div class="mx-cell"><span class="mx-cell-day">${c.day_num}</span><span class="mx-cell-pnl"></span></div>`;
      const p = Number(c.pnl_usd || 0);
      const cls = `mx-cell ${p >= 0 ? "win" : "loss"} ${c.state === "LIVE_OPEN" ? "live" : ""}`;
      const tag = c.state === "LIVE_OPEN" ? "mở" : "";
      return `<div class="${cls}" title="${c.day}: ${p >= 0 ? "+" : ""}${p.toFixed(2)} USD (${c.state})">
        <span class="mx-cell-day">${c.day_num} ${tag}</span>
        <span class="mx-cell-pnl ${p >= 0 ? "pos" : "neg"}">${p >= 0 ? "+" : ""}$${Math.abs(p).toFixed(1)}</span>
      </div>`;
    }).join("");
  }

  function renderBlackFridaySprint(d) {
    if (!d || !$("panel-bf-sprint")) return;
    const cdText = d.countdown_vi || `${d.remaining_hours ?? 0}h ${d.remaining_minutes ?? 0}m`;
    const cdBadge = $("bf-countdown-badge");
    cdBadge.textContent = cdText;
    cdBadge.className = `tag ${d.expired ? "tag-red" : (Number(d.remaining_hours || 0) <= 24 ? "tag-amber" : "tag-green")}`;

    $("bf-countdown-val").textContent = d.expired
      ? "Đã đến hạn"
      : `${d.remaining_hours} giờ ${String(d.remaining_minutes ?? 0).padStart(2, "0")} phút`;
    $("bf-countdown-val").className = `mini-val mono ${d.expired ? "neg" : "warn"}`;
    $("bf-countdown-sub").textContent = `Hạn chốt: ${d.deadline_ict || "30/11/2026 16:00 ICT"} (${cdText})`;

    const vaultEl = $("bf-vault-badge");
    const mounted = d.private_vault_status === "MOUNTED";
    vaultEl.textContent = mounted ? "Kho bảo mật lớp 2: ĐÃ GẮN" : "Kho bảo mật lớp 2: CHƯA GẮN";
    vaultEl.className = `tag ${mounted ? "tag-green" : "tag-amber"}`;

    $("bf-seal-badge").textContent = `OrderSend=${d.order_send_count ?? 0} · ${d.holdout_sealed ? "Holdout khóa" : "Kiểm tra Holdout"}`;

    // Mũi 3 summary & 5-scenario table (Model=4 Real Ticks vs Model=1 1m OHLC)
    const m3 = d.mui3_realtick || {};
    const m3Latest = m3.latest || null;
    if (m3.available && m3Latest) {
      const m4c = m3.model4_count != null ? m3.model4_count : (m3.scenarios || []).filter((x) => x.model === 4).length;
      const m1c = m3.model1_count != null ? m3.model1_count : (m3.scenarios || []).filter((x) => x.model === 1).length;
      const allSwapOk = (m3.scenarios || []).every((x) => x.swap_zero_ok !== false);
      $("bf-mui3-val").textContent = `${m3.scenarios_count} kịch bản ĐẠT (${m4c} M4 · ${m1c} M1)`;
      $("bf-mui3-val").className = "mini-val mono pos";
      const net = m3Latest.total_net_profit_usd;
      const netStr = net != null ? `${net >= 0 ? "+" : ""}${Number(net).toFixed(2)} USD` : "—";
      const pfStr = m3Latest.profit_factor != null ? `PF ${Number(m3Latest.profit_factor).toFixed(2)}` : "PF —";
      $("bf-mui3-sub").textContent = `Mới nhất: ${m3Latest.label} (${netStr}, ${pfStr}) · ${allSwapOk ? "Swap=0 ĐẠT" : "Kiểm tra Swap"}`;
    } else {
      $("bf-mui3-val").textContent = "Đang chờ";
      $("bf-mui3-val").className = "mini-val mono warn";
      $("bf-mui3-sub").textContent = "Chưa có tệp kết quả Master_Prop7E";
    }

    const m3Body = $("tbl-bf-mui3").querySelector("tbody");
    const scList = m3.scenarios || [];
    if (!scList.length) {
      m3Body.innerHTML = `<tr><td colspan="9" class="mono">Chưa có kết quả chạy thử Master_Prop7E (trạng thái chờ).</td></tr>`;
    } else {
      m3Body.innerHTML = scList.map((sc) => {
        const net = sc.total_net_profit_usd;
        const netCls = net == null ? "" : (net >= 0 ? "pos" : "neg");
        const netTxt = net == null ? "—" : `${net >= 0 ? "+" : ""}${Number(net).toFixed(2)} USD`;
        const winTxt = (sc.from_date && sc.to_date) ? `${sc.from_date}–${sc.to_date}` : (sc.period || "—");
        const isM4 = sc.model === 4 || sc.is_real_ticks === true;
        const mBadge = sc.model_badge || (isM4 ? "Model=4 Real Ticks" : "Model=1 1m OHLC");
        const mCls = isM4 ? "tag-green" : "tag-amber";
        const shortLbl = String(sc.label || "").replace(/^MASTER_PROP7E_/, "");
        return `
          <tr>
            <td class="mono strong" title="${escHtml(sc.label)}">${escHtml(shortLbl)}</td>
            <td><span class="tag ${mCls}">${escHtml(mBadge)}</span></td>
            <td class="mono">${escHtml(winTxt)}</td>
            <td class="num mono">${sc.total_trades != null ? sc.total_trades : "—"}</td>
            <td class="num mono ${netCls}">${netTxt}</td>
            <td class="num mono">${sc.profit_factor != null ? Number(sc.profit_factor).toFixed(2) : "—"}</td>
            <td class="num mono">${sc.sharpe_ratio != null ? Number(sc.sharpe_ratio).toFixed(2) : "—"}</td>
            <td class="num mono">${sc.equity_dd_pct != null ? `${Number(sc.equity_dd_pct).toFixed(2)}%` : "—"}</td>
            <td><span class="tag ${sc.swap_zero_ok ? "tag-green" : "tag-red"}">${sc.swap_zero_ok ? "ĐẠT" : "LỖI"}</span></td>
          </tr>`;
      }).join("");
    }

    // Mũi 1-2 live calibration progress strip + summary & table
    const m12 = d.mui1_mui2 || {};
    const rf = m12.realized_friction || {};
    const cp = m12.calibration_progress || {};
    const ls = m12.live_spreads || {};

    const cpDone = Number(cp.completed_round_trips || 0);
    const cpTarget = Number(cp.target_round_trips || 28);
    const cpOpen = Number(cp.open_in_progress_count || 0);
    const cpPct = Math.min(100, Math.max(0, Number(cp.progress_pct || 0)));
    const cpBadge = $("bf-calib-status-badge");
    if (cpBadge) {
      const cpMap = { COMPLETED: ["HOÀN TẤT", "tag-green"], IN_PROGRESS: ["ĐANG ĐO", "tag-amber"], pending: ["CHỜ", ""] };
      const [lbl, cls] = cpMap[cp.status] || ["CHỜ", ""];
      cpBadge.textContent = lbl;
      cpBadge.className = `tag ${cls}`;
    }
    const cpBar = $("bf-calib-bar");
    if (cpBar) cpBar.style.width = `${cpPct}%`;
    const cpHead = $("bf-calib-headline");
    if (cpHead) {
      const slipMean = cp.mean_adverse_slip_bps != null ? `${Number(cp.mean_adverse_slip_bps).toFixed(2)} bps` : "—";
      const slipMax = cp.max_adverse_slip_bps != null ? `tối đa ${Number(cp.max_adverse_slip_bps).toFixed(2)} bps` : "";
      const latP50 = cp.median_latency_ms != null ? `${Number(cp.median_latency_ms).toFixed(1)} ms` : "—";
      const swapStr = cp.available ? (cp.swap_zero_ok ? "Swap=0 ĐẠT" : "Swap LỆCH") : "Swap=0";
      const openPart = cpOpen > 0 ? ` · Đang mở: ${cpOpen}` : "";
      const slipPart = slipMax ? `${slipMean} (${slipMax})` : slipMean;
      cpHead.textContent = `${cpDone} / ${cpTarget} lệnh probe thực địa${openPart} · Trượt giá TB: ${slipPart} · Độ trễ P50: ${latP50} · ${swapStr}`;
    }
    const cpSymEl = $("bf-calib-sym-pills");
    if (cpSymEl) {
      const perSym = cp.per_symbol_fills || {};
      const keys = Object.keys(perSym);
      cpSymEl.innerHTML = keys.map((sym) => {
        const item = perSym[sym] || {};
        const comp = Number(item.completed || 0);
        const tgt = Number(item.target || 7);
        const op = Number(item.open || 0);
        const tone = comp >= tgt ? "is-ok" : (comp > 0 || op > 0 ? "is-warn" : "");
        const openTxt = op > 0 ? ` (+${op} mở)` : "";
        return `<span class="bf-pill ${tone}"><span class="bf-pill-lbl">${escHtml(sym)}:</span> <strong>${comp}/${tgt}${openTxt}</strong></span>`;
      }).join("");
    }

    if (rf.available) {
      const p50 = rf.p50_friction_mult != null ? `P50 ${Number(rf.p50_friction_mult).toFixed(2)}×` : "P50 —";
      const p90 = rf.p90_friction_mult != null ? `P90 ${Number(rf.p90_friction_mult).toFixed(2)}×` : "P90 —";
      const ok = rf.p50_friction_mult == null || rf.p50_friction_mult <= 1.5;
      $("bf-friction-val").textContent = `${p50} / ${p90}`;
      $("bf-friction-val").className = `mini-val mono ${ok ? "pos" : "warn"}`;
      $("bf-friction-sub").textContent = `${rf.fills_count ?? cpDone} lệnh khớp · ${ls.samples_count ?? 0} mẫu spread · ${rf.verdict || "OK"}`;
      $("bf-friction-note").textContent = `Tổng hợp Mũi 1–2 (${rf.generated_utc || "mới nhất"}): trượt giá P50=${rf.p50_slippage_bps != null ? `${rf.p50_slippage_bps} bps` : "—"} · P90=${rf.p90_slippage_bps != null ? `${rf.p90_slippage_bps} bps` : "—"}.`;
    } else if (cp.available) {
      $("bf-friction-val").textContent = `${cpDone} / ${cpTarget} lệnh probe`;
      $("bf-friction-val").className = `mini-val mono ${cpDone >= cpTarget ? "pos" : "accent"}`;
      const latTxt = cp.median_latency_ms != null ? ` · P50 ${Number(cp.median_latency_ms).toFixed(0)}ms` : "";
      $("bf-friction-sub").textContent = `${ls.samples_count ?? 0} mẫu spread trực tiếp${latTxt} · đang thu thập`;
      $("bf-friction-note").textContent = `Đang đọc trực tiếp tiến độ từ bảng khớp lệnh mẫu (cập nhật: ${cp.latest_fill_utc || ls.latest_captured_utc || "—"}). Tệp tổng hợp cuối sẽ có sau khi hoàn tất phiên đo.`;
    } else if (ls.available) {
      $("bf-friction-val").textContent = `${ls.samples_count} mẫu spread`;
      $("bf-friction-val").className = "mini-val mono accent";
      $("bf-friction-sub").textContent = "Đang chờ tổng hợp trượt giá Mũi 1 · Spread trực tiếp đã có";
      $("bf-friction-note").textContent = `Chưa có tệp đo trượt giá Mũi 1 — đang hiển thị spread thực từ ${ls.samples_count} mẫu gần nhất (${ls.latest_captured_utc || "—"}).`;
    } else {
      $("bf-friction-val").textContent = "Đang chờ";
      $("bf-friction-val").className = "mini-val mono warn";
      $("bf-friction-sub").textContent = "Chưa có dữ liệu trượt giá và spread trực tiếp";
      $("bf-friction-note").textContent = "Chưa có dữ liệu Mũi 1–2 (hệ thống tự cập nhật khi tệp thực địa sẵn sàng).";
    }

    const frBody = $("tbl-bf-friction").querySelector("tbody");
    const symRows = m12.symbol_table || [];
    if (!symRows.length) {
      frBody.innerHTML = `<tr><td colspan="7" class="mono">Chưa có mẫu spread trực tiếp cho 4 mã cốt lõi.</td></tr>`;
    } else {
      frBody.innerHTML = symRows.map((r) => {
        const ratio = r.ratio_vs_dev_1x;
        const rTag = ratio == null
          ? `<span class="tag">CHỜ</span>`
          : (ratio <= 1.25
            ? `<span class="tag tag-green">TỐT</span>`
            : (ratio <= 1.75 ? `<span class="tag tag-amber">THEO DÕI</span>` : `<span class="tag tag-red">CAO</span>`));
        const fillTxt = r.fills_count != null ? `${r.fills_count}/7` : "—";
        return `
          <tr>
            <td class="mono strong">${escHtml(r.symbol)}</td>
            <td class="num mono">${fillTxt}</td>
            <td class="num mono">${r.live_median_spread_bps != null ? Number(r.live_median_spread_bps).toFixed(2) : "—"}</td>
            <td class="num mono">${r.live_p90_spread_bps != null ? Number(r.live_p90_spread_bps).toFixed(2) : "—"}</td>
            <td class="num mono strong">${ratio != null ? `${Number(ratio).toFixed(2)}×` : "—"}</td>
            <td class="num mono">${r.samples != null ? r.samples : "—"}</td>
            <td>${rTag}</td>
          </tr>`;
      }).join("");
    }
  }

  function renderNode1Summary(n) {
    if (!n || !$("bf-node-pills")) return;
    const isLive = n.source === "live_ssh" && n.connected === true;
    const srcBadge = $("n1-source-badge");
    srcBadge.textContent = isLive ? "SSH trực tiếp" : "Dự phòng cục bộ";
    srcBadge.className = `tag ${isLive ? "tag-green" : "tag-amber"}`;

    $("bf-node1-val").textContent = isLive
      ? (n.mt5_running ? "Trực tuyến · MT5 chạy" : "Trực tuyến · MT5 dừng")
      : "Chế độ dự phòng";
    $("bf-node1-val").className = `mini-val mono ${isLive && n.mt5_running ? "pos" : (isLive ? "neg" : "warn")}`;

    const balTxt = n.balance != null ? fmtUSD(n.balance) : "—";
    const eqTxt = n.equity != null ? fmtUSD(n.equity) : "—";
    $("bf-node1-sub").textContent = `Số dư ${balTxt} · Equity ${eqTxt} · Vị thế: ${n.open_positions != null ? n.open_positions : "—"}`;

    const mkPill = (lbl, val, tone = "") =>
      `<span class="bf-pill ${tone}"><span class="bf-pill-lbl">${escHtml(lbl)}:</span> <strong>${escHtml(val)}</strong></span>`;

    const mt5Txt = n.mt5_running === true ? "Đang chạy" : (n.mt5_running === false ? "Đã dừng" : "Chưa rõ");
    const mt5Tone = n.mt5_running === true ? "is-ok" : (n.mt5_running === false ? "is-bad" : "");
    const pgOk = n.propguard_ok_count != null ? n.propguard_ok_count : "—";
    const pgWarn = n.propguard_warn_count != null ? n.propguard_warn_count : "—";
    const pgTone = n.propguard_warn_count != null ? (n.propguard_warn_count > 0 ? "is-bad" : "is-ok") : "";
    const alTxt = n.auto_logon === true ? "Bật" : (n.auto_logon === false ? "Tắt" : "—");
    const alTone = n.auto_logon === true ? "is-ok" : (n.auto_logon === false ? "is-warn" : "");
    const hkTone = n.heroku_status === "OK" ? "is-ok" : (n.heroku_status === "ERROR" ? "is-bad" : "is-warn");
    const ramTxt = n.free_ram_gb != null ? `${Number(n.free_ram_gb).toFixed(1)} GB` : "—";
    const diskTxt = n.c_free_gb != null ? `${Number(n.c_free_gb).toFixed(1)} GB` : "—";
    const diskTone = n.c_free_gb != null ? (n.c_free_gb < 10 ? "is-bad" : "is-ok") : "";

    $("bf-node-pills").innerHTML = [
      mkPill("Kết nối", n.connected ? "Trực tiếp" : "Ngoại tuyến", n.connected ? "is-ok" : "is-warn"),
      mkPill("MT5", mt5Txt, mt5Tone),
      mkPill("Lệnh mở", n.open_positions != null ? String(n.open_positions) : "—"),
      mkPill("Số dư / Equity", `${balTxt} / ${eqTxt}`),
      mkPill("PropGuard", `OK ${pgOk} · Cảnh báo ${pgWarn}`, pgTone),
      mkPill("Lệch giờ NTP", n.ntp_offset || "—", n.ntp_offset && n.ntp_offset !== "unknown" ? "is-ok" : ""),
      mkPill("Tự đăng nhập", alTxt, alTone),
      mkPill("Giám sát Heroku", n.heroku_status || "—", hkTone),
      mkPill("RAM trống", ramTxt),
      mkPill("Ổ C trống", diskTxt, diskTone),
    ].join("");
  }

  async function refreshBlackFridayAndNode1(forceFresh = false) {
    const q = forceFresh ? "?nocache=1" : "";
    const [bfRes, n1Res] = await Promise.allSettled([
      fetchJson(`/api/blackfriday-sprint${q}`),
      fetchJson(`/api/node1-summary${q}`),
    ]);
    if (bfRes.status === "fulfilled") renderBlackFridaySprint(bfRes.value);
    if (n1Res.status === "fulfilled") renderNode1Summary(n1Res.value);
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
    await Promise.all([
      refreshBlackFridayAndNode1(),
      refreshPropMetrix(),
      refreshCalculator(),
      refreshStress(),
      refreshRebalancer(),
    ]);
  }

  function syncCapitalFromUsd(usd) {
    const fx = Number($("inp-fx").value || 25500);
    const vnd = Math.round(usd * fx);
    $("inp-cap-vnd").value = vnd;
    $("slider-cap-usd").value = Math.min(200000, Math.max(10000, usd));
    $("cap-slider-lbl").textContent = `${Math.round(usd).toLocaleString("en-US")} USD`;
    document.querySelectorAll(".js-tier-btn").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.usd) === Math.round(usd));
    });
  }

  window.addEventListener("DOMContentLoaded", () => {
    $("btn-refresh").addEventListener("click", () => refreshAll());
    const bfRefBtn = $("btn-bf-refresh");
    if (bfRefBtn) {
      bfRefBtn.addEventListener("click", async () => {
        bfRefBtn.disabled = true;
        bfRefBtn.textContent = "Đang làm mới…";
        try {
          await refreshBlackFridayAndNode1(true);
        } finally {
          bfRefBtn.disabled = false;
          bfRefBtn.textContent = "Làm mới dữ liệu";
        }
      });
    }
    $("slider-cap-usd").addEventListener("input", () => {
      syncCapitalFromUsd(Number($("slider-cap-usd").value || 50000));
      refreshCalculator();
      refreshStress();
    });
    document.querySelectorAll(".js-tier-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        syncCapitalFromUsd(Number(btn.dataset.usd || 50000));
        refreshCalculator();
        refreshStress();
      });
    });
    ["inp-cap-vnd", "inp-fx", "inp-prop-usd", "inp-profile", "slider-stress"].forEach((id) => {
      $(id).addEventListener("input", () => {
        const capVnd = Number($("inp-cap-vnd").value || 1275000000);
        const fx = Number($("inp-fx").value || 25500);
        const capUsd = capVnd / Math.max(1000, fx);
        $("cap-slider-lbl").textContent = `${Math.round(capUsd).toLocaleString("en-US")} USD`;
        $("slider-cap-usd").value = Math.min(200000, Math.max(10000, Math.round(capUsd / 5000) * 5000));
        refreshCalculator();
        refreshStress();
      });
    });
    const mxSel = $("inp-mx-program");
    if (mxSel) {
      const savedProg = window.localStorage && window.localStorage.getItem("naqex_mx_program");
      if (savedProg && Array.from(mxSel.options).some((o) => o.value === savedProg)) {
        mxSel.value = savedProg;
      }
      mxSel.addEventListener("change", () => {
        if (window.localStorage) window.localStorage.setItem("naqex_mx_program", mxSel.value);
        refreshPropMetrix();
      });
    }
    $("inp-rebal-mode").addEventListener("change", () => refreshRebalancer());
    $("btn-toggle-cover").addEventListener("click", () => {
      coverOpened = !coverOpened;
      $("emg-controls").classList.toggle("hidden", !coverOpened);
      $("btn-toggle-cover").textContent = coverOpened ? "Đóng nắp bảo vệ" : "Lật nắp bảo vệ";
    });
    $("btn-emg-confirm").addEventListener("click", () => submitEmergencyCover());
    $("btn-pta-run").addEventListener("click", () => runPropTermsAudit());
    refreshAll().catch((err) => {
      $("chart-tooltip").textContent = `Load error: ${err.message}`;
    });
  });
})();
