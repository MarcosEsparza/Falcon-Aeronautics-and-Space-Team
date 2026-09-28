# Development rules

- Read the implementation and tests before modifying code. Treat the latest accepted main branch as the baseline.
- Make the smallest coherent change. Keep modules focused and interfaces explicit.
- Do not add redundant wrappers, duplicate functions, duplicate calculations, compatibility patch layers, or speculative abstractions.
- Keep engineering calculations, historical analysis, presentation, and test infrastructure separate.
- Preserve calculations, screening, ranking, defaults, warnings, exports, and historical behavior unless a verified defect or approved requirement calls for a change.
- Never fabricate real ESP performance data or historical outcomes. Label fictional data and engineering assumptions clearly.
- Engineering changes require traceable units, cited assumptions or source data, boundary-case review, and independently derived expected values in tests. Passing software tests does not validate field performance.
- Add or update tests for every behavior change. Prefer unit tests for calculations and deterministic browser tests only for critical rendered flows.
- Before review, run compilation, the complete suite, application startup verification, and required browser checks.
- A pull request is acceptable only when scope is documented, unrelated files are untouched, required checks pass, screenshots are reviewed when presentation changes, limitations are reported, and no unresolved high-risk issue remains.
- Report actual commands and results. Do not claim branch protection, deployment, field validation, or external configuration without direct verification.
