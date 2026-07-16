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

const styles = {
  page: {
    maxWidth: 1100,
    margin: "0 auto",
    padding: "2rem 1.25rem 4rem",
  } as React.CSSProperties,
  brand: {
    fontSize: "clamp(2.2rem, 5vw, 3.4rem)",
    letterSpacing: "-0.03em",
    margin: 0,
    fontWeight: 700,
  } as React.CSSProperties,
  sub: {
    color: "var(--muted)",
    maxWidth: 52,
    lineHeight: 1.7,
    marginTop: "0.75rem",
  } as React.CSSProperties,
  status: (ok: boolean) =>
    ({
      display: "inline-block",
      marginTop: "1.25rem",
      padding: "0.55rem 0.9rem",
      borderRadius: 8,
      border: `1px solid ${ok ? "var(--accent)" : "var(--warn)"}`,
      background: ok ? "rgba(61,155,110,0.12)" : "rgba(212,160,23,0.12)",
      fontWeight: 600,
      fontSize: "0.95rem",
    }) as React.CSSProperties,
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
    gap: "0.85rem",
    marginTop: "1.75rem",
  } as React.CSSProperties,
  field: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 6,
  },
  label: { fontSize: "0.85rem", color: "var(--muted)" } as React.CSSProperties,
  input: {
    background: "rgba(255,255,255,0.04)",
    border: "1px solid var(--line)",
    color: "var(--ink)",
    borderRadius: 8,
    padding: "0.65rem 0.75rem",
    fontSize: "1rem",
  } as React.CSSProperties,
  btn: {
    marginTop: "1.25rem",
    background: "var(--accent)",
    color: "#04140c",
    border: "none",
    borderRadius: 10,
    padding: "0.85rem 1.4rem",
    fontWeight: 700,
    cursor: "pointer",
    fontSize: "1rem",
  } as React.CSSProperties,
  panel: {
    marginTop: "2rem",
    padding: "1.25rem",
    border: "1px solid var(--line)",
    borderRadius: 14,
    background: "rgba(0,0,0,0.22)",
  } as React.CSSProperties,
  mono: {
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: "0.9rem",
  } as React.CSSProperties,
};

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

  const statusValidated = report?.status === "VALIDATED";

  return (
    <main style={styles.page}>
      <p style={{ color: "var(--muted)", marginBottom: 8, letterSpacing: "0.08em" }}>ADGE</p>
      <h1 style={styles.brand}>Adaptive Delta-Gamma Engine</h1>
      <p style={styles.sub}>
        أداة تحليل كمّي تعليمية — v3.1 Clean Architecture على Fly.io. ليست توصية استثمارية.
        الحالة الافتراضية بدون بيانات خيارات مستقلة: UNVALIDATABLE.
      </p>

      <form onSubmit={onSubmit}>
        <div style={styles.grid}>
          {(
            [
              ["S0", "السعر الحالي"],
              ["sigma_base", "التقلب السنوي"],
              ["r", "معدل الخالي من المخاطر"],
              ["Target", "الهدف الفني"],
              ["Capital", "رأس مال الصفقة"],
              ["Total_Portfolio_Value", "إجمالي المحفظة"],
              ["ATR_14", "ATR 14"],
              ["ticker", "الرمز"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} style={styles.field}>
              <span style={styles.label}>{label}</span>
              <input
                style={styles.input}
                value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            </label>
          ))}
          <label style={styles.field}>
            <span style={styles.label}>الاتجاه</span>
            <select
              style={styles.input}
              value={form.Bias}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  Bias: e.target.value as "bullish" | "bearish",
                }))
              }
            >
              <option value="bullish">bullish</option>
              <option value="bearish">bearish</option>
            </select>
          </label>
          <label style={{ ...styles.field, justifyContent: "flex-end" }}>
            <span style={styles.label}>
              <input
                type="checkbox"
                checked={form.allow_short}
                onChange={(e) => setForm((f) => ({ ...f, allow_short: e.target.checked }))}
              />{" "}
              السماح بالشورت
            </span>
            <span style={styles.label}>
              <input
                type="checkbox"
                checked={form.sigma_is_historical_approx}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    sigma_is_historical_approx: e.target.checked,
                  }))
                }
              />{" "}
              σ تاريخي تقريبي
            </span>
          </label>
        </div>
        <button style={styles.btn} type="submit" disabled={loading}>
          {loading ? "جارٍ التحليل…" : "تشغيل التحليل"}
        </button>
      </form>

      {error && (
        <div style={{ ...styles.panel, borderColor: "var(--danger)" }}>
          <strong>خطأ:</strong> <span style={styles.mono}>{error}</span>
        </div>
      )}

      {report && (
        <section style={styles.panel}>
          <div style={styles.status(statusValidated)}>STATUS: {report.status}</div>

          <h2 style={{ marginTop: "1.5rem" }}>الملخص</h2>
          <ul style={{ lineHeight: 1.8, color: "var(--muted)" }}>
            <li>
              DTE: <b style={{ color: "var(--ink)" }}>{report.dte_days ?? "—"}</b> يوم — انتهاء{" "}
              {report.expiry ?? "—"}
            </li>
            <li>
              الاحتمالات: base={report.probabilities.base ?? "—"} | stress=
              {report.probabilities.stress ?? "—"} | crush=
              {report.probabilities.post_crush ?? "—"}
            </li>
            <li>
              Strikes نظرية: Kc={report.kc ?? "—"} / Kp={report.kp ?? "—"}
            </li>
            <li>
              Efficiency_net: <b style={{ color: "var(--ink)" }}>{report.efficiency_net ?? "—"}</b>{" "}
              | RebalanceCost: {report.rebalance_cost ?? "—"} | Premium:{" "}
              {report.premium_total ?? "—"}
            </li>
          </ul>

          {report.composition && (
            <>
              <h3>التركيبة</h3>
              <p style={styles.mono}>
                Stock_Factor={report.composition.stock_factor}, Nc={report.composition.nc}, Np=
                {report.composition.np}
              </p>
              <p style={{ color: "var(--muted)" }}>{report.composition.justification}</p>
            </>
          )}

          {report.greeks && (
            <>
              <h3>Greeks</h3>
              <p style={styles.mono}>
                Δ={report.greeks.delta_net} | Γ={report.greeks.gamma_net} | Vega=
                {report.greeks.vega_net} | Theta={report.greeks.theta_net}
              </p>
            </>
          )}

          <h3>تحذيرات</h3>
          <ul>
            {report.warnings.map((w, i) => (
              <li key={i} style={{ color: "var(--warn)", marginBottom: 6 }}>
                {w}
              </li>
            ))}
          </ul>

          {report.rejections.length > 0 && (
            <>
              <h3>رفض / قيود</h3>
              <ul>
                {report.rejections.map((w, i) => (
                  <li key={i} style={{ color: "var(--danger)" }}>
                    {w}
                  </li>
                ))}
              </ul>
            </>
          )}

          {report.gap_iv_scenarios.length > 0 && (
            <>
              <h3>سيناريوهات Gap × IV</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
                  <thead>
                    <tr>
                      {["gap", "iv", "pnl", "accepted"].map((h) => (
                        <th
                          key={h}
                          style={{
                            textAlign: "right",
                            borderBottom: "1px solid var(--line)",
                            padding: "0.4rem",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.gap_iv_scenarios.map((s, i) => (
                      <tr key={i}>
                        <td style={{ padding: "0.35rem" }}>{s.gap}</td>
                        <td style={{ padding: "0.35rem" }}>{s.iv_scenario}</td>
                        <td style={{ padding: "0.35rem" }}>{s.pnl}</td>
                        <td style={{ padding: "0.35rem" }}>{s.accepted ? "نعم" : "لا"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {chartData.length > 0 && (
            <>
              <h3>شبكة السعر × الزمن — delta_net</h3>
              <div style={{ width: "100%", height: 320, position: "relative" as const }}>
                <ResponsiveContainer>
                  <LineChart data={chartData}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="price" stroke="#8fa398" />
                    <YAxis stroke="#8fa398" />
                    <Tooltip
                      contentStyle={{
                        background: "#14201a",
                        border: "1px solid rgba(255,255,255,0.12)",
                      }}
                    />
                    <Legend />
                    {tauKeys.map((k, idx) => (
                      <Line
                        key={k}
                        type="monotone"
                        dataKey={k}
                        stroke={["#3d9b6e", "#d4a017", "#6ea8fe", "#c44b4b", "#b388ff"][idx % 5]}
                        dot={false}
                        strokeWidth={2}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          )}

          <h3>UNCALIBRATED</h3>
          <pre style={{ ...styles.mono, overflow: "auto" }}>
            {JSON.stringify(report.uncalibrated_placeholders, null, 2)}
          </pre>

          <p style={{ marginTop: "1.5rem", color: "var(--muted)", fontSize: "0.9rem" }}>
            {report.disclaimer}
          </p>
        </section>
      )}

      <section style={styles.panel}>
        <h2 style={{ marginTop: 0 }}>Validation Protocol (A/B/C/D)</h2>
        <p style={{ color: "var(--muted)", lineHeight: 1.7 }}>
          يتطلب <code>DATA_SOURCE_URL</code> لمصدر خيارات/IV مستقل (مثل philippdubach Parquet).
          بدون ذلك تبقى الحالة UNVALIDATABLE. الأسعار التاريخية لا تُشتق من Black-Scholes الداخلي.
        </p>
        <div style={styles.grid}>
          <label style={styles.field}>
            <span style={styles.label}>Tickers</span>
            <input
              style={styles.input}
              value={valTickers}
              onChange={(e) => setValTickers(e.target.value)}
            />
          </label>
          <label style={styles.field}>
            <span style={styles.label}>min_trades</span>
            <input
              style={styles.input}
              value={minTrades}
              onChange={(e) => setMinTrades(e.target.value)}
            />
          </label>
        </div>
        <button
          style={{ ...styles.btn, background: "var(--warn)", color: "#1a1400" }}
          type="button"
          disabled={valLoading}
          onClick={onStartValidation}
        >
          {valLoading ? "التحقق قيد التشغيل…" : "تشغيل Backtest / Validation Job"}
        </button>
        {valError && (
          <p style={{ color: "var(--danger)", marginTop: "1rem" }}>
            <span style={styles.mono}>{valError}</span>
          </p>
        )}
        {valJob && (
          <div style={{ marginTop: "1.25rem" }}>
            <div style={styles.status(valJob.result?.status === "VALIDATED")}>
              JOB {valJob.status}
              {valJob.result ? ` → ${valJob.result.status}` : ""}
            </div>
            {valJob.error && <p style={{ color: "var(--danger)" }}>{valJob.error}</p>}
            {valJob.result?.reason && (
              <p style={{ color: "var(--muted)" }}>{valJob.result.reason}</p>
            )}
            <pre style={{ ...styles.mono, overflow: "auto", marginTop: "1rem" }}>
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
