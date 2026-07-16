from __future__ import annotations

import math
from datetime import date

import numpy as np

from application.dto.analyze_dto import AnalyzeRequestDTO, AnalyzeResponseDTO
from application.ports import ClockPort, MarketDataPort, OptionsHistoryPort, PricingPort
from application.services.market_math import (
    build_sigma_surface,
    get_upcoming_fridays,
    implied_strike,
    prob_reach_target,
)
from domain.entities.composition import Composition
from domain.entities.greeks import NetGreeks
from domain.entities.stress_result import GapIvScenarioResult, StressSummary
from domain.entities.trade_inputs import Bias, TradeInputs
from domain.entities.validation_status import ValidationStatus
from domain.policies import (
    BETA_MAX,
    GAMMA_MAX,
    MAX_RISK_PCT_OF_PORTFOLIO,
    P_FLOOR,
    REBALANCE_TRIGGER,
    UNCALIBRATED_PLACEHOLDERS,
    efficiency_net,
    exceeds_redundancy,
    rebalance_cost_too_high,
    should_reject_gap_loss,
    short_allowed,
)

DISCLAIMER = (
    "النظام تحليلي تعليمي. يتطلب VALIDATED عبر بيانات مستقلة. "
    "لا يغني عن تأكيد الأسعار الحية قبل التنفيذ. ليس نصيحة استثمارية."
)

STRIKE_NOTE = (
    "تقريبي — نطاق خطأ متوقع ±1-2 Strike؛ يتطلب تأكيدًا حيًا من شاشة الخيارات "
    "(Bid/Ask) قبل التنفيذ. Volatility Skew الحقيقي قد يُحدث انحرافًا."
)

MAX_DTE_CANDIDATES = 6


class AnalyzeTrade:
    def __init__(
        self,
        pricing: PricingPort,
        market_data: MarketDataPort,
        options_history: OptionsHistoryPort,
        clock: ClockPort,
        mc_paths: int = 80,
    ):
        self.pricing = pricing
        self.market_data = market_data
        self.options_history = options_history
        self.clock = clock
        self.mc_paths = mc_paths

    def execute(self, req: AnalyzeRequestDTO) -> AnalyzeResponseDTO:
        warnings: list[str] = []
        rejections: list[str] = []

        status = self._status_gate()
        if self.options_history.derived_from_internal_bs():
            raise RuntimeError("Circular validation forbidden: options history derived from internal BS")

        if req.sigma_is_historical_approx:
            warnings.append("التقلب المستخدم تقريبي تاريخي (HV) — ليس IV سوقيًا.")

        warnings.append(STRIKE_NOTE)
        warnings.append(
            "الثوابت EVENT_MULTIPLIER / POST_CRUSH / SKEW / REBALANCE_TRIGGER موسومة UNCALIBRATED_PLACEHOLDER."
        )

        bias = Bias(req.bias.lower())
        inputs = TradeInputs(
            s0=req.s0,
            sigma_base=req.sigma_base,
            r=req.r,
            target=req.target,
            bias=bias,
            capital=req.capital,
            total_portfolio_value=req.total_portfolio_value,
            allow_short=req.allow_short,
            atr_14=req.atr_14,
            ticker=req.ticker,
        )

        today = self.clock.today()
        earnings = self.market_data.next_earnings_date(inputs.ticker)
        fridays = get_upcoming_fridays(today)

        candidates = self._dte_candidates(inputs, fridays, today, earnings, warnings)
        if not candidates:
            return self._empty_response(
                status=status,
                warnings=warnings
                + ["الهدف غير واقعي إحصائيًا ضمن هذا التقلب — راجع الهدف الفني."],
                rejections=rejections,
            )

        # Keep nearest viable DTEs (already chronological); cap for latency
        candidates = candidates[:MAX_DTE_CANDIDATES]

        best = None
        best_score = -math.inf
        gap_rows: list[dict] = []
        sim_grid: list[dict] = []

        for expiry, tau, probs in candidates:
            surface = build_sigma_surface(
                inputs.sigma_base, has_earnings_in_window(earnings, today, expiry)
            )

            if bias == Bias.BULLISH:
                kc = implied_strike(inputs.s0, surface.base, inputs.r, tau, 0.40, "call")
                kp = implied_strike(inputs.s0, surface.base, inputs.r, tau, -0.20, "put")
                delta_target = 0.55
            else:
                kc = implied_strike(inputs.s0, surface.base, inputs.r, tau, 0.20, "call")
                kp = implied_strike(inputs.s0, surface.base, inputs.r, tau, -0.40, "put")
                delta_target = -0.55

            solved = self._solve_composition(
                inputs, kc, kp, tau, surface.base, delta_target, rejections
            )
            if solved is None:
                continue

            combo, greeks, premium, car, rc_est, eff_est, stress = solved
            # Refine rebalance cost with light MC only for shortlisted DTE winners
            rc = self._estimate_rebalance_cost(combo, inputs.s0, kc, kp, tau, surface.base, inputs.r)
            if rebalance_cost_too_high(rc, premium):
                rejections.append(f"RebalanceCost مرتفع عند DTE={(expiry-today).days}")
                continue
            eff = efficiency_net(greeks.delta_net, car, rc)

            gap_rows = [
                {
                    "gap": s.gap,
                    "iv_scenario": s.iv_scenario,
                    "pnl": round(s.pnl, 2),
                    "accepted": s.accepted,
                    "reason": s.reason,
                }
                for s in stress.scenarios
            ]
            if stress.rejected:
                rejections.append(stress.reject_reason or "فشل Gap×IV stress")
                continue

            score = eff * probs["base"]
            if score > best_score:
                best_score = score
                sim_grid = self._simulation_grid(
                    combo, inputs.s0, kc, kp, tau, surface.base, inputs.r
                )
                best = {
                    "expiry": expiry,
                    "tau": tau,
                    "probs": probs,
                    "kc": kc,
                    "kp": kp,
                    "combo": combo,
                    "greeks": greeks,
                    "premium": premium,
                    "car": car,
                    "rc": rc,
                    "eff": eff,
                }

        if best is None:
            return self._empty_response(
                status=status,
                warnings=warnings
                + ["لم تُقبل أي تركيبة ضمن القيود (غاما/ميزانية/Gap/تكلفة/تكرار)."],
                rejections=rejections,
                gap_iv_scenarios=gap_rows,
            )

        dte_days = (best["expiry"] - today).days
        warnings.append(
            f"DTE={dte_days} يومًا — p_base≈{best['probs']['base']*100:.1f}% | "
            f"p_stress≈{best['probs']['stress']*100:.1f}% | "
            f"p_crush≈{best['probs']['post_crush']*100:.1f}%"
        )

        combo = best["combo"]
        greeks = best["greeks"]

        return AnalyzeResponseDTO(
            status=status.value,
            warnings=warnings,
            dte_days=dte_days,
            expiry=best["expiry"].isoformat(),
            probabilities={k: round(v, 4) for k, v in best["probs"].items()},
            kc=best["kc"],
            kp=best["kp"],
            strike_note=STRIKE_NOTE,
            composition={
                "stock_factor": combo.stock_factor,
                "nc": combo.nc,
                "np": combo.np,
                "justification": (
                    f"حل رقمي ضمن القيود؛ score=Efficiency_net×p_base="
                    f"{best_score:.6f}; delta_net={greeks.delta_net:.4f}"
                ),
            },
            greeks={
                "delta_net": round(greeks.delta_net, 6),
                "gamma_net": round(greeks.gamma_net, 8),
                "vega_net": round(greeks.vega_net, 6),
                "theta_net": round(greeks.theta_net, 6),
            },
            efficiency_net=round(best["eff"], 8),
            rebalance_cost=round(best["rc"], 2),
            premium_total=round(best["premium"], 2),
            capital_at_risk=round(best["car"], 2),
            gap_iv_scenarios=gap_rows,
            simulation_grid=sim_grid,
            rejections=rejections,
            uncalibrated_placeholders=dict(UNCALIBRATED_PLACEHOLDERS),
            disclaimer=DISCLAIMER,
            extras={
                "stop_loss_share_move": 2 * inputs.atr_14,
                "max_risk_pct": MAX_RISK_PCT_OF_PORTFOLIO,
            },
        )

    def _status_gate(self) -> ValidationStatus:
        if not self.options_history.is_available():
            return ValidationStatus.UNVALIDATABLE
        return ValidationStatus.PENDING_VALIDATION

    def _dte_candidates(
        self,
        inputs: TradeInputs,
        fridays: list[date],
        today: date,
        earnings: date | None,
        warnings: list[str],
    ) -> list[tuple[date, float, dict[str, float]]]:
        out: list[tuple[date, float, dict[str, float]]] = []
        for f in fridays:
            tau = (f - today).days / 365.0
            if tau <= 0:
                continue
            if earnings and 0 <= (f - earnings).days < 5:
                warnings.append(
                    f"تُجاهل {f.isoformat()} بسبب أرباح خلال أقل من 5 أيام من الانتهاء."
                )
                continue
            surface = build_sigma_surface(
                inputs.sigma_base, has_earnings_in_window(earnings, today, f)
            )
            probs = {
                "base": prob_reach_target(
                    inputs.s0, inputs.target, surface.base, inputs.r, tau, inputs.bias
                ),
                "stress": prob_reach_target(
                    inputs.s0, inputs.target, surface.stress, inputs.r, tau, inputs.bias
                ),
                "post_crush": prob_reach_target(
                    inputs.s0, inputs.target, surface.post_crush, inputs.r, tau, inputs.bias
                ),
            }
            if probs["base"] < P_FLOOR:
                continue
            out.append((f, tau, probs))
        return out

    def _solve_composition(
        self,
        inputs: TradeInputs,
        kc: float,
        kp: float,
        tau: float,
        sigma: float,
        delta_target: float,
        rejections: list[str],
    ):
        pricing = self.pricing
        s0, r, capital = inputs.s0, inputs.r, inputs.capital
        stock_factors = [-1, 0, 1] if inputs.allow_short else [0, 1]

        c_px = pricing.price_call(s0, kc, tau, sigma, r)
        p_px = pricing.price_put(s0, kp, tau, sigma, r)
        d_call = pricing.delta_call(s0, kc, tau, sigma, r)
        d_put = pricing.delta_put(s0, kp, tau, sigma, r)
        g_call = pricing.gamma(s0, kc, tau, sigma, r)
        g_put = pricing.gamma(s0, kp, tau, sigma, r)
        v_call = pricing.vega(s0, kc, tau, sigma, r)
        v_put = pricing.vega(s0, kp, tau, sigma, r)
        t_call = pricing.theta_call(s0, kc, tau, sigma, r)
        t_put = pricing.theta_put(s0, kp, tau, sigma, r)

        best = None
        best_rank = math.inf

        for sf in stock_factors:
            for nc in range(0, 8):
                for np_ in range(-6, 7):
                    if nc == 0 and np_ == 0 and sf == 0:
                        continue
                    combo = Composition(sf, nc, np_)
                    if not short_allowed(combo, inputs.allow_short):
                        continue

                    premium = (nc * c_px + abs(np_) * p_px) * 100
                    if premium > BETA_MAX * capital:
                        continue

                    gamma_net = nc * g_call + np_ * g_put
                    if abs(gamma_net * s0**2 * 0.01 / capital) > GAMMA_MAX:
                        continue

                    stock_delta = float(sf)
                    options_delta = nc * d_call + np_ * d_put
                    delta_net = stock_delta + options_delta
                    if exceeds_redundancy(stock_delta, options_delta):
                        continue

                    car = (100 * s0 if sf != 0 else 0.0) + premium
                    if car > MAX_RISK_PCT_OF_PORTFOLIO * inputs.total_portfolio_value:
                        continue

                    # Fast heuristic cost during search (MC refined later)
                    rc_est = self._heuristic_rebalance_cost(sigma, tau, c_px, gamma_net, s0)
                    if rebalance_cost_too_high(rc_est, max(premium, 1.0)):
                        continue

                    stress = self._gap_iv_stress(
                        combo, s0, kc, kp, tau, sigma, r, inputs.total_portfolio_value
                    )
                    if stress.rejected:
                        continue

                    eff = efficiency_net(delta_net, car, rc_est)
                    err = abs(delta_net - delta_target)
                    rank = err - 0.01 * abs(eff)
                    if rank < best_rank:
                        best_rank = rank
                        greeks = NetGreeks(
                            delta_net=delta_net,
                            gamma_net=gamma_net,
                            vega_net=nc * v_call + np_ * v_put,
                            theta_net=nc * t_call + np_ * t_put,
                        )
                        best = (combo, greeks, premium, car, rc_est, eff, stress)

        if best is None:
            rejections.append("لا حل يمر بكل القيود عند هذا DTE/Strikes.")
        return best

    def _heuristic_rebalance_cost(
        self, sigma: float, tau: float, call_price: float, gamma_net: float, s0: float
    ) -> float:
        # Expected rebalances ~ volatility moves / trigger; gamma amplifies delta drift
        expected_moves = max(sigma * math.sqrt(max(tau, 1e-6)) * abs(gamma_net) * s0, 0.0)
        n_est = expected_moves / max(REBALANCE_TRIGGER, 1e-6)
        n_est = min(n_est, 40.0)
        cost_per = 0.05 * abs(call_price) * 100 + 1.0
        return n_est * cost_per

    def _gap_iv_stress(
        self,
        combo: Composition,
        s0: float,
        kc: float,
        kp: float,
        tau: float,
        sigma_base: float,
        r: float,
        total_portfolio: float,
    ) -> StressSummary:
        surface = build_sigma_surface(sigma_base, False)
        iv_map = {"crush": surface.post_crush, "spike": surface.stress}
        gaps = [-0.25, -0.15, 0.15, 0.25]
        tau_next = max(tau - 1 / 365.0, 1e-6)
        val0 = self._portfolio_value(combo, s0, kc, kp, tau, sigma_base, r)
        scenarios: list[GapIvScenarioResult] = []
        worst = 0.0
        for g in gaps:
            s_new = s0 * (1 + g)
            for iv_name, sig in iv_map.items():
                val = self._portfolio_value(combo, s_new, kc, kp, tau_next, sig, r)
                pnl = val - val0
                worst = min(worst, pnl)
                scenarios.append(
                    GapIvScenarioResult(gap=g, iv_scenario=iv_name, pnl=pnl, accepted=True)
                )
        rejected = should_reject_gap_loss(worst, total_portfolio)
        reason = None
        if rejected:
            reason = (
                f"أسوأ خسارة Gap×IV = {worst:.2f} تجاوزت حد "
                f"{1.5 * MAX_RISK_PCT_OF_PORTFOLIO * total_portfolio:.2f}"
            )
            scenarios = [
                GapIvScenarioResult(
                    gap=s.gap,
                    iv_scenario=s.iv_scenario,
                    pnl=s.pnl,
                    accepted=(s.pnl > worst),
                    reason=reason if s.pnl == worst else None,
                )
                for s in scenarios
            ]
        return StressSummary(
            scenarios=tuple(scenarios),
            worst_loss=worst,
            rejected=rejected,
            reject_reason=reason,
        )

    def _portfolio_value(
        self,
        combo: Composition,
        s: float,
        kc: float,
        kp: float,
        tau: float,
        sigma: float,
        r: float,
    ) -> float:
        stock = combo.stock_factor * 100 * s
        calls = combo.nc * self.pricing.price_call(s, kc, tau, sigma, r) * 100
        puts = combo.np * self.pricing.price_put(s, kp, tau, sigma, r) * 100
        return stock + calls + puts

    def _combo_delta(
        self,
        combo: Composition,
        s: float,
        kc: float,
        kp: float,
        tau: float,
        sigma: float,
        r: float,
    ) -> float:
        return (
            float(combo.stock_factor)
            + combo.nc * self.pricing.delta_call(s, kc, tau, sigma, r)
            + combo.np * self.pricing.delta_put(s, kp, tau, sigma, r)
        )

    def _estimate_rebalance_cost(
        self,
        combo: Composition,
        s0: float,
        kc: float,
        kp: float,
        tau: float,
        sigma: float,
        r: float,
    ) -> float:
        steps = 20
        dt = tau / steps if tau > 0 else 0.0
        if dt <= 0:
            return 0.0
        counts = []
        rng = np.random.default_rng(42)
        call_price = self.pricing.price_call(s0, kc, tau, sigma, r)
        for _ in range(self.mc_paths):
            s = s0
            t = tau
            last = self._combo_delta(combo, s, kc, kp, t, sigma, r)
            count = 0
            for _step in range(steps):
                s *= math.exp(
                    (r - 0.5 * sigma**2) * dt
                    + sigma * math.sqrt(dt) * float(rng.standard_normal())
                )
                t = max(t - dt, 1e-6)
                d = self._combo_delta(combo, s, kc, kp, t, sigma, r)
                if abs(d - last) > REBALANCE_TRIGGER:
                    count += 1
                    last = d
            counts.append(count)
        n_avg = float(np.mean(counts)) if counts else 0.0
        cost_per = 0.05 * abs(call_price) * 100 + 1.0
        return n_avg * cost_per

    def _simulation_grid(
        self,
        combo: Composition,
        s0: float,
        kc: float,
        kp: float,
        tau: float,
        sigma: float,
        r: float,
    ) -> list[dict]:
        prices = np.linspace(s0 * 0.85, s0 * 1.15, 13)
        times = [tau, tau * 0.75, tau * 0.5, tau * 0.25, 0.01]
        rows = []
        for t in times:
            tt = max(t, 1e-6)
            for s in prices:
                rows.append(
                    {
                        "price": round(float(s), 2),
                        "tau": round(float(tt), 4),
                        "delta_net": round(
                            self._combo_delta(combo, float(s), kc, kp, tt, sigma, r), 4
                        ),
                        "value": round(
                            self._portfolio_value(combo, float(s), kc, kp, tt, sigma, r), 2
                        ),
                    }
                )
        return rows

    def _empty_response(
        self,
        status: ValidationStatus,
        warnings: list[str],
        rejections: list[str],
        gap_iv_scenarios: list[dict] | None = None,
    ) -> AnalyzeResponseDTO:
        return AnalyzeResponseDTO(
            status=status.value,
            warnings=warnings,
            dte_days=None,
            expiry=None,
            probabilities={},
            kc=None,
            kp=None,
            strike_note=STRIKE_NOTE,
            composition=None,
            greeks=None,
            efficiency_net=None,
            rebalance_cost=None,
            premium_total=None,
            capital_at_risk=None,
            gap_iv_scenarios=gap_iv_scenarios or [],
            simulation_grid=[],
            rejections=rejections,
            uncalibrated_placeholders=dict(UNCALIBRATED_PLACEHOLDERS),
            disclaimer=DISCLAIMER,
        )


def has_earnings_in_window(earnings: date | None, today: date, expiry: date) -> bool:
    if earnings is None:
        return False
    return today <= earnings <= expiry
