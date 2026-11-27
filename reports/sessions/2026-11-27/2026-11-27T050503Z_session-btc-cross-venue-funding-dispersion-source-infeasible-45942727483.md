# Wake-up session — 2026-11-27T050503Z

## Objective

Reconcile the current README contract, mainline, research workstreams, daily KPI and recent workflow outcomes. Complete the active BTC cross-venue funding-dispersion source-feasibility cycle without weakening its frozen source gates or duplicating a backtest.

## Starting repository state — VERIFIED

- Starting `main`: `6c9d95ce5a7af3b3f3e1fc137ae4701e0be6537a` (`fix: include next-session close in funding dispersion source preflight`).
- The current README is the self-contained operating contract; no historical task file was treated as a standing assignment.
- No active, queued or waiting Actions runs were present at the final pre-commit inspection.
- No open pull requests or standalone open issues were present.
- The repository already contained a successful real-data backtest for a distinct 2026-11-27 hypothesis, so the daily minimum did not require a duplicate run.

## Research output — source feasibility only

Active hypothesis: `QFR-2026-11-27-BTC-CROSS-VENUE-FUNDING-DISPERSION-DOWNSIDE-01`.

The frozen preregistration requires exact timestamp-matched MEXC and Binance USD-M BTC perpetual funding settlements at 00:00, 08:00 and 16:00 UTC, with a fixed 2025-06-15 through 2026-11-23 signal window and a checksummed Binance Spot daily target calendar. It explicitly requires closure as INCONCLUSIVE/INFEASIBLE if a source or coverage gate fails. No model or backtest is authorized until the source preflight passes.

### Attempt 1 — deterministic fixture failure

- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45942535156
- Triggering commit: `6076b4868ff4099ea33a9c18f67179e878833bbd`.
- All source retrieval was skipped because two deterministic fixture assertions failed: the synthetic Spot calendar had one extra date relative to the frozen price boundary, and the fixture produced three rather than four accepted events.
- This was a test-fixture boundary defect, not market evidence.

### Repair and attempt 2 — source endpoint blocked

- Boundary repair: commit `6c9d95ce5a7af3b3f3e1fc137ae4701e0be6537a` added the next-session close to the frozen Spot price calendar.
- Workflow run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45942727483
- The source-preflight deterministic suite passed all 11 tests. The admission-guard workflow also passed: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45942727412.
- The live source step then failed at 2026-11-27T04:55:43Z with non-retryable `HTTP 451` for the frozen request:
  `https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1749916800000&endTime=1795478400000&limit=1000`.
- The source-preflight function calls and validates MEXC history before requesting Binance history. Execution reached the Binance request, so the MEXC fetch/validation calls returned without raising in this invocation. However, the run produced no artifact or durable source manifest; MEXC coverage is therefore not promoted to a separately verified accepted-source result.
- Binance Spot archive retrieval, matched-date construction and event-count validation were not reached.
- GitHub Actions reported no artifacts for either source-preflight attempt.

## Disposition

**CLOSED — INCONCLUSIVE/INFEASIBLE (source-access gate failed).**

This is not a performance rejection and says nothing about whether cross-venue funding dispersion predicts Spot downside loss. The authorized runner could not retrieve the preregistered Binance USD-M funding endpoint. The frozen protocol requires stopping before model implementation when a source gate fails. No API proxy, source substitution, shortened window, imputation, model fit or empirical backtest was attempted.

The preregistration remains frozen. Any materially different Binance source route, venue, or data representation must be assessed under a new hypothesis identity and a new timebox; this identity is not silently reopened.

## Daily research KPI — MET

The minimum for 2026-11-27 was already satisfied by the distinct real-data forecast backtest:

- Hypothesis: `QFR-2026-11-27-BTC-TAKER-ABSORPTION-DOWNSIDE-01`.
- Successful run: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45926394994.
- Source preflight: https://github.com/takenthatusernameis-collab/QUANTITATIVE-FINANCE-RESEARCH/actions/runs/45925248340.
- 561 accepted six-session-spaced events; 159 validation and 298 test forecasts.
- RMSE improvement: +0.3119% validation, -1.0491% test.
- Paired test squared-loss 95% block-bootstrap interval: [-0.037146, 0.001898].
- Frozen disposition: INCONCLUSIVE. This is a forecast-only screen, not trading P&L or strategy validation.

## Changed

- Updated `research/HYPOTHESIS-REGISTRY.md` to close the cross-venue funding-dispersion hypothesis as INCONCLUSIVE/INFEASIBLE and link this report.
- Added this timestamped session report.
- Both changes are committed atomically. No source-preflight or empirical workflow was retriggered by the registry/report-only handoff.

## Verified

- Mainline source commit and workflow run IDs above.
- Source-preflight tests: 11/11 passed on run 45942727483.
- Admission guard: passed on run 45942727412.
- The source failure was HTTP 451, not a parser, cadence, timestamp or model-performance failure.
- No artifacts were published by the two failed source-preflight runs.
- No active/queued/waiting Actions runs, open PRs or standalone issues at the final pre-commit inspection.

## Unverified / blocked

- No durable MEXC funding manifest from the cross-venue preflight.
- No Binance USD-M funding history, matched cross-venue panel, Binance Spot target panel or accepted source manifest for this hypothesis.
- No forecast metrics or performance disposition for the cross-venue funding-dispersion hypothesis.
- The HTTP 451 cause beyond the returned status is not established; it must not be generalized into a claim that Binance has no historical data.

## Research versus operations

This session completed a source-feasibility diagnosis and a durable evidence handoff. It did not complete a new empirical backtest; the daily KPI was already met. No raw market observations were committed, no paid data or credentials were acquired, and no live orders or capital deployment occurred.

## Next

Select a materially distinct, feasible research hypothesis or a separately preregistered source representation. Do not retry the same Binance API request unchanged, reopen this closed identity, or count this source-preflight work as a backtest.
