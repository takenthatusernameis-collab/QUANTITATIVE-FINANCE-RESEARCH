# Asset-Universe Discovery and Scope Policy

**Status: MANDATORY factory-wide rule for every new asset-, security-, instrument- or market-level research project.**

## Governing rule: no repository-wide asset whitelist

The quantitative-finance research factory has **no fixed global asset universe**. ETHUSDT and BTCUSDT are the explicit scope of the current ETH/BTC research and prospective Spot capture work only. They are not a default universe, preferred pair, permanent whitelist, seed list that must be retained, or limit on future research.

The factory must not inherit a prior task's symbols, asset count, exchange, market type, quote currency, asset class, market-cap tier or venue as a universal constraint. The same applies to old model scripts, cached datasets, workflow matrices, provider pilots and examples. Those are project-specific implementation details unless a separate governing research decision explicitly says otherwise.

**Default for new asset-universe hypotheses: discover dynamically from the full set of assets/instruments that are relevant to the research question and can be lawfully and realistically evidenced.** Do not arbitrarily restrict discovery to ETH/BTC, a short hand-picked symbol list, the currently cached assets, or a convenient top-N set.

This does not mean every hypothesis must use every asset. The research question, market/instrument definition, point-in-time availability, liquidity/execution requirements, data quality and compute capacity determine the eligible universe. Any restriction must be explicit, justified, measurable and specific to that experiment—not inherited from the repository.

## Separate three different scopes

1. **Factory opportunity space:** open-ended. Agents should discover new candidate assets, instruments, venues and data sources over time; the prior project's symbols do not define it.
2. **Project research universe:** defined by the new hypothesis and its preregistered eligibility rules. Dynamic discovery is the default for cross-sectional or multi-asset research. A fixed one-asset, pair or small basket is allowed only when the research question genuinely requires it and the reason is documented.
3. **Dataset / engineering task scope:** may be deliberately narrow to verify a particular source, connector, capture process or known experiment. It does not constrain the factory opportunity space or automatically become the next strategy's universe.

The current first scheduled Spot holdout capture intentionally collects Binance Spot 1h ETHUSDT and BTCUSDT for its specified data-validation purpose. The `run_eth_btc.py` and `spot_holdout_capture.py` implementations are pair-/capture-specific. Do not broaden or mutate those scoped implementations merely to create the appearance of a generic factory. Keep their scope explicit and build a separate reusable universe-discovery/data-adapter capability when a future project needs one.

## Mandatory universe-discovery procedure

Before choosing a new model:

1. Identify the instrument classes and markets the hypothesis could reasonably concern. Do not assume a crypto pair or a particular venue merely because prior repository work used it.
2. Enumerate the assets and instruments exposed by each relevant authorized source or market catalogue. Where useful, consider multiple exchanges, quote currencies, spot, dated futures, perpetuals, options, tokenized instruments, equities, ETFs, rates, FX or other supported markets. These are candidate domains, not automatic requirements or accepted data sources.
3. Start with discovery, not a hand-maintained ticker allowlist. A seed list may be used to test an adapter or control, but must be labelled non-exhaustive and must not silently define the final universe.
4. Apply the hypothesis's preregistered, economically meaningful inclusion criteria to the discovered set. Examples include trading activity, executable liquidity, listing/inception history, contract status, point-in-time market capitalization or data completeness.
5. Record all candidate identifiers with venue, instrument type, base/quote, contract multiplier/settlement convention where applicable, listing/inception and delisting/expiry dates, and source provenance. A ticker string alone is not a sufficient instrument identity.
6. Where the research is cross-sectional, reconstruct universe membership as of each historical decision time. Include delisted/expired instruments when needed; do not use today's survivors as a historical universe.
7. Record every exclusion with a reason and timestamp. Distinguish an economic eligibility exclusion from unavailable data, provider access failure, delisting, schema problems or compute limits.
8. Reconcile the observed candidate count with the source's catalogue/pagination/coverage evidence. Do not stop after the first few assets or the first asset that passes.
9. Preserve an expansion path when new instruments or independent sources become available. A completed snapshot is not the permanent asset universe.

## When an experiment may use a fixed universe

A fixed universe is valid only when justified by the question—for example, a predeclared two-leg relative-value relationship, a specific benchmark constituent set, one instrument's microstructure, or a controlled source/adapter test.

The preregistration must explain why the fixed asset(s), pair or basket are intrinsic to the hypothesis rather than a convenience; why alternatives would not answer the same question; whether the set is fixed historically or membership changes point-in-time; the exact inclusion/exclusion rules; and why the limitation must not be generalized to other projects.

A fixed universe is a research-design choice, not a repository capability boundary.

## Handling data and infrastructure limitations

- Verified access to only a small group of assets is evidence about the current source/environment, not proof that the research opportunity space is equally small.
- Do not quietly shrink a broad hypothesis to whatever assets happen to be cached or parse successfully. Quantify missing coverage and assess whether exclusion would create selection or survivorship bias.
- If broader discovery or history is required but not accessible, create a bounded environment-enabling project to test distinct lawful sources, APIs, archives, catalogue routes or data constructions. Do not use paid services, new credentials or permissions without explicit authorization.
- Keep venue and instrument types separate until a valid cross-source identity, clock, contract and economic methodology has been established.
- If an entire provider, asset class or market route is unavailable, record that exact boundary and continue independent research where safe. Do not treat a route failure as a universal asset rejection.
- A compute or API cap is not a justification for an arbitrary permanent top-N rule. If a bounded sample is needed for a pilot, label it as a sample, state its selection method and do not claim universe-wide evidence. For a final experiment, any cap must have a measurable, hypothesis-relevant or technically evidenced rationale.

## Machine-checkable intake

Every new quantitative hypothesis must include an `asset_universe_policy` in its project intake:

- `dynamic_discovery`: default for asset-level or cross-sectional work; requires a discovery method, target scope, inclusion/exclusion criteria, point-in-time membership treatment and an expansion rule.
- `fixed_universe`: requires a specific research-design rationale and explicit inclusion/exclusion criteria.
- `not_applicable`: only for genuinely non-asset-level research, with a rationale.

A dynamic universe may use a finite cap only when `max_asset_count` and its evidence-backed `cap_rationale` are both recorded. Seed assets are allowed only when explicitly marked non-exhaustive. The validator is `research/project_readiness.py`; regression tests are in `research/test_project_readiness.py`.

## Success criterion

A future agent should be able to discover and evaluate assets beyond the symbols currently present in the repository without changing this factory-wide policy. The next project must inherit the discovery method and evidence requirements—not the previous project's asset list.
