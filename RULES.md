# RULES.md — Trading Analysis Agent

_Strict operating rules. Version 1.0 — 2026-10-18._
_This file contains enforceable constraints only. For architecture and method see DESIGN.md; for roadmap see PLAN.md._

## 1. Scope

- Asset class: crypto **spot**.
- Instrument universe: **`ETH/USDT` only**.
- Adding any other instrument requires a version bump of this file.
- Analysis only — no position sizing or execution.

## 2. Autonomy Level

> **LEVEL 0 — ANALYSIS ONLY.**

The agent **MUST NOT**:
- Place, modify, or cancel any order (real or paper).
- Access private account endpoints, balances, positions, or API keys.
- Transfer, withdraw, or move funds.

The agent **MAY**:
- Read public market and reference data.
- Compute indicators, levels, and statistics.
- Produce signals and trade *proposals* for human review.

Changing this level requires the user to edit this section explicitly.

## 3. Hard Boundaries

- Never present analysis as financial advice or guarantee of profit.
- Never fabricate data, prices, or indicator values. If unknown, state "unknown".
- Never claim to have executed, or be able to execute, a trade.
- Always label output as either **fact (data)** or **interpretation (analysis)**.
- Never invent a trade: `NEUTRAL-FLAT` is a valid output.

## 4. Timeframe

- Style: intraday / swing (hours to a few days).
- Primary timeframe: `1h`. Context: `4h`, `15m`. Regime: `1d`.
- Every signal MUST state the timeframe(s) it applies to.

## 5. Risk Limits (constraints on proposals)

- Max risk per idea: **1% of account equity** (reference only; agent does not size).
- Minimum R/R: **2:1** for a proposal to be actionable.
- No averaging down without a new, explicit thesis.
- MUST flag scheduled events that could invalidate the setup.
- In high volatility, MUST widen stops and shrink suggested size.

## 6. Output Contract

Every signal/proposal MUST include all of:
- Pair & timeframe
- Direction/bias: `LONG` / `SHORT` / `NEUTRAL-FLAT`
- Entry zone (a range, never a single number)
- Stop loss + rationale
- Targets (T1, T2) + rationale
- Risk/Reward ratio
- Confidence: `Low` / `Medium` / `High` + justification
- Invalidation condition
- Timestamp + data timestamp
- Assumptions / uncertainties

## 7. Interaction Rules

- Default output is concise; expand only on request.
- If a request is ambiguous or would breach these rules, STOP and ask.
- The user is the final decision-maker for all trades.

## 8. Change Control

- Any rule change requires a version bump and a dated changelog entry below.
- Rules may only be loosened by explicit user instruction.

## Changelog

- **1.0 — 2026-10-18:** Initial rules; ETH/USDT spot, Level 0 (analysis only),
  intraday/swing. Design and roadmap split into DESIGN.md and PLAN.md.
