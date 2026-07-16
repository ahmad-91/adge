"use client";

import { useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  CartesianGrid,
} from "recharts";
import { BffEngineClient } from "@/adapters/http/bff_engine_client";
import { analyzeTrade } from "@/application/analyze_trade";
import type { AnalyzeResponse, ValidationJob } from "@/domain/status";

const client = new BffEngineClient();

function statusTone(status: string | undefined) {
  if (status === "VALIDATED") return "badge--ok";
  if (status === "UNVALIDATABLE" || (status && status.includes("UNVALIDATED"))) {
    return "badge--warn";
  }
  return "badge--warn";
}

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<AnalyzeResponse | null>(null);
  const [valLoading, setValLoading] = useState(false);
  const [valError, setValError] = useState<string | null>(null);
  const [valJob, setValJob] = useState<ValidationJob | null>(null);
  const [valTickers, setValTickers] = useState("SPY,QQQ,AAPL");
  const [minTrades, setMinTrades] = useState("50");
  const [form, setForm] = useState({
    S0: "50",
    sigma_base: "0.40",
    r: "0.045",
    Target: "60",
    Bias: "bullish" as "bullish" | "bearish",
    Capital: "10000",
    Total_Portfolio_Value: "50000",
    allow_short: false,
    ATR_14: "1.5",
    ticker: "SPY",
    sigma_is_historical_approx: true,
  });

  const chartData = useMemo(() => {
    if (!report?.simulation_grid?.length) return [];
    const byPrice = new Map<number, Record<string, number>>();
    for (const row of report.simulation_grid) {
      const key = row.price;
      const cur = byPrice.get(key) || { price: key };
      cur[`t_${row.tau}`] = row.delta_net;
      byPrice.set(key, cur);
    }
    return Array.from(byPrice.values()).sort((a, b) => a.price - b.price);
  }, [report]);

  const tauKeys = useMemo(() => {
    if (!report?.simulation_grid?.length) return [] as string[];
    return Array.from(new Set(report.simulation_grid.map((r) => `t_${r.tau}`)));
  }, [report]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        S0: Number(form.S0),
        sigma_base: Number(form.sigma_base),
        r: Number(form.r),
        Target: Number(form.Target),
        Bias: form.Bias,
        Capital: Number(form.Capital),
        Total_Portfolio_Value: Number(form.Total_Portfolio_Value),
        allow_short: form.allow_short,
        ATR_14: Number(form.ATR_14),
        ticker: form.ticker || undefined,
        sigma_is_historical_approx: form.sigma_is_historical_approx,
      };
      const res = await analyzeTrade(client, payload);
      setReport(res);
    } catch (err) {
      setReport(null);
      setError(err instanceof Error ? err.message : "فشل التحليل");
    } finally {
      setLoading(false);
    }
  }

  async function onStartValidation() {
    setValLoading(true);
    setValError(null);
    setValJob(null);
    try {
      const tickers = valTickers
        .split(",")
        .map((t) => t.trim().toUpperCase())
        .filter(Boolean);
      const started = await client.startValidation({
        tickers,
        min_trades: Number(minTrades) || 50,
        hold_days: 21,
        sample_every_n_days: 5,
      });
      let job = await client.getValidationJob(started.job_id);
      setValJob(job);
      while (job.status === "PENDING" || job.status === "RUNNING") {
        await new Promise((r) => setTimeout(r, 2000));
        job = await client.getValidationJob(started.job_id);
        setValJob(job);
      }
    } catch (err) {
      setValError(err instanceof Error ? err.message : "فشل التحقق");
    } finally {
      setValLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div className="brand-mark">
          <span className="brand-mark__glyph" aria-hidden />
          <h1 className="brand-mark__name">ADGE</h1>
        </div>
        <p className="hero__title">Adaptive Delta-Gamma Engine</p>
        <p className="hero__lede">
          محرّك تحليل كمّي تعليمي لتركيبات الدلتا-غاما — يبني السيناريوهات ويحرسك ببوابة تحقق
          مستقلة قبل أي استخدام برأس مال حقيقي.
        </p>
        <div className="hero__actions">
          <a className="btn btn--primary" href="#workspace">
            ابدأ التحليل
          </a>
          <a className="btn btn--ghost" href="#validation">
            بروتوكول التحقق
          </a>
        </div>
      </header>

      <section id="workspace" className="section">
        <div className="section__head">
          <div>
            <h2 className="section__title">مساحة التحليل</h2>
            <p className="section__hint">
              أدخل معطيات الصفقة. النتائج تعليمية وتتطلب حالة VALIDATED قبل الاعتماد عليها.
            </p>
          </div>
        </div>

        <form onSubmit={onSubmit}>
          <div className="grid">
            {(
              [
                ["S0", "السعر الحالي"],
                ["sigma_base", "التقلب السنوي"],
                ["r", "المعدل الخالي من المخاطر"],
                ["Target", "الهدف الفني"],
                ["Capital", "رأس مال الصفقة"],
                ["Total_Portfolio_Value", "إجمالي المحفظة"],
                ["ATR_14", "ATR 14"],
                ["ticker", "الرمز"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="field">
                <span>{label}</span>
                <input
                  value={form[key]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                />
              </label>
            ))}

            <label className="field">
              <span>الاتجاه</span>
              <select
                value={form.Bias}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    Bias: e.target.value as "bullish" | "bearish",
                  }))
                }
              >
                <option value="bullish">صاعد (bullish)</option>
                <option value="bearish">هابط (bearish)</option>
              </select>
            </label>

            <div className="checks">
              <label>
                <input
                  type="checkbox"
                  checked={form.allow_short}
                  onChange={(e) => setForm((f) => ({ ...f, allow_short: e.target.checked }))}
                />
                السماح بالشورت
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={form.sigma_is_historical_approx}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      sigma_is_historical_approx: e.target.checked,
                    }))
                  }
                />
                σ تاريخي تقريبي
              </label>
            </div>
          </div>

          <div className="form-actions">
            <button className="btn btn--primary" type="submit" disabled={loading}>
              {loading ? "جارٍ التحليل…" : "تشغيل التحليل"}
            </button>
          </div>
        </form>

        {error && <div className="alert">{error}</div>}

        {report && (
          <div className="results block">
            <div className={`badge ${statusTone(report.status)}`}>الحالة: {report.status}</div>

            <div className="metrics">
              <div className="metric">
                <span className="metric__label">DTE</span>
                <span className="metric__value">{report.dte_days ?? "—"}</span>
              </div>
              <div className="metric">
                <span className="metric__label">انتهاء</span>
                <span className="metric__value" style={{ fontSize: "1rem" }}>
                  {report.expiry ?? "—"}
                </span>
              </div>
              <div className="metric">
                <span className="metric__label">Kc / Kp</span>
                <span className="metric__value" style={{ fontSize: "1rem" }}>
                  {report.kc ?? "—"} / {report.kp ?? "—"}
                </span>
              </div>
              <div className="metric">
                <span className="metric__label">Efficiency</span>
                <span className="metric__value">{report.efficiency_net ?? "—"}</span>
              </div>
            </div>

            <div className="block">
              <h3>الاحتمالات</h3>
              <p className="mono">
                base={report.probabilities.base ?? "—"} · stress=
                {report.probabilities.stress ?? "—"} · crush=
                {report.probabilities.post_crush ?? "—"}
              </p>
              <p>
                RebalanceCost: {report.rebalance_cost ?? "—"} · Premium:{" "}
                {report.premium_total ?? "—"} · Capital at risk:{" "}
                {report.capital_at_risk ?? "—"}
              </p>
            </div>

            {report.composition && (
              <div className="block">
                <h3>التركيبة</h3>
                <p className="mono">
                  Stock_Factor={report.composition.stock_factor} · Nc=
                  {report.composition.nc} · Np={report.composition.np}
                </p>
                <p>{report.composition.justification}</p>
              </div>
            )}

            {report.greeks && (
              <div className="block">
                <h3>Greeks</h3>
                <p className="mono">
                  Δ={report.greeks.delta_net} · Γ={report.greeks.gamma_net} · Vega=
                  {report.greeks.vega_net} · Theta={report.greeks.theta_net}
                </p>
              </div>
            )}

            {report.warnings.length > 0 && (
              <div className="block">
                <h3>تحذيرات</h3>
                <ul>
                  {report.warnings.map((w, i) => (
                    <li key={i} style={{ color: "var(--warn)" }}>
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {report.rejections.length > 0 && (
              <div className="block">
                <h3>رفض / قيود</h3>
                <ul>
                  {report.rejections.map((w, i) => (
                    <li key={i} style={{ color: "var(--danger)" }}>
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {report.gap_iv_scenarios.length > 0 && (
              <div className="block">
                <h3>سيناريوهات Gap × IV</h3>
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>gap</th>
                        <th>iv</th>
                        <th>pnl</th>
                        <th>accepted</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.gap_iv_scenarios.map((s, i) => (
                        <tr key={i}>
                          <td>{s.gap}</td>
                          <td>{s.iv_scenario}</td>
                          <td>{s.pnl}</td>
                          <td>{s.accepted ? "نعم" : "لا"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {chartData.length > 0 && (
              <div className="block">
                <h3>شبكة السعر × الزمن — delta_net</h3>
                <div className="chart">
                  <ResponsiveContainer>
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="rgba(20,34,28,0.08)" />
                      <XAxis dataKey="price" stroke="#5f6f66" />
                      <YAxis stroke="#5f6f66" />
                      <Tooltip
                        contentStyle={{
                          background: "#fffdf8",
                          border: "1px solid rgba(20,34,28,0.12)",
                          borderRadius: 10,
                        }}
                      />
                      <Legend />
                      {tauKeys.map((k, idx) => (
                        <Line
                          key={k}
                          type="monotone"
                          dataKey={k}
                          stroke={
                            ["#0f6b4c", "#a86b00", "#2f6fed", "#b42318", "#5b4db8"][idx % 5]
                          }
                          dot={false}
                          strokeWidth={2}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            <div className="block">
              <h3>UNCALIBRATED</h3>
              <pre className="pre">
                {JSON.stringify(report.uncalibrated_placeholders, null, 2)}
              </pre>
            </div>

            <p className="disclaimer">{report.disclaimer}</p>
          </div>
        )}
      </section>

      <section id="validation" className="section">
        <div className="section__head">
          <div>
            <h2 className="section__title">بروتوكول التحقق A/B/C/D</h2>
            <p className="section__hint">
              يعتمد على علامات خيارات تاريخية مستقلة — لا يُشتق من تسعير Black-Scholes الداخلي.
            </p>
          </div>
        </div>

        <div className="grid">
          <label className="field">
            <span>Tickers</span>
            <input value={valTickers} onChange={(e) => setValTickers(e.target.value)} />
          </label>
          <label className="field">
            <span>min_trades</span>
            <input value={minTrades} onChange={(e) => setMinTrades(e.target.value)} />
          </label>
        </div>

        <div className="form-actions">
          <button
            className="btn btn--warn"
            type="button"
            disabled={valLoading}
            onClick={onStartValidation}
          >
            {valLoading ? "التحقق قيد التشغيل…" : "تشغيل Backtest / Validation"}
          </button>
        </div>

        {valError && <div className="alert">{valError}</div>}

        {valJob && (
          <div className="results block">
            <div
              className={`badge ${statusTone(valJob.result?.status ?? valJob.status)}`}
            >
              JOB {valJob.status}
              {valJob.result ? ` → ${valJob.result.status}` : ""}
            </div>
            {valJob.error && <p style={{ color: "var(--danger)" }}>{valJob.error}</p>}
            {valJob.result?.reason && <p>{valJob.result.reason}</p>}
            <pre className="pre">
              {JSON.stringify(
                {
                  phase_a_ok: valJob.result?.phase_a_ok,
                  phase_b: valJob.result?.phase_b,
                  phase_c: valJob.result?.phase_c,
                  phase_d: valJob.result?.phase_d,
                  ci95: valJob.result?.ci95,
                },
                null,
                2
              )}
            </pre>
          </div>
        )}
      </section>
    </main>
  );
}
