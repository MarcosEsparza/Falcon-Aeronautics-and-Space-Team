# Reusable development template

Use this checklist for an entirely new repository. Adapt paths and commands; do not copy ESP code, datasets, calculations, assumptions, or directory structure.

## Repository contract

- Add a concise AGENTS.md with scope boundaries, validation expectations, required checks, and PR acceptance criteria.
- Select and document supported runtime versions. Separate runtime and development dependencies.
- Commit example environment configuration only when needed; never commit credentials or production data.
- Choose the framework for the new project's needs. Streamlit is not required.

## Tests and evidence

- Put deterministic domain behavior in fast unit tests with independently derived expectations.
- Add integration tests only at real boundaries.
- For a rendered UI, add a small browser smoke test that asserts a visible readiness signal, critical interaction state, and responsive overflow.
- Use semantic selectors and condition-based waits, never fixed sleeps or retries that hide flakes.
- Capture screenshots or traces so CI failures can be diagnosed without a rerun.

## Continuous integration

Run the required workflow for every pull request and support workflow_dispatch; do not add path filters. Adapt these gates:

1. Check out the exact revision.
2. Install the pinned runtime and dependencies.
3. Compile or statically validate sources.
4. Run the complete automated suite.
5. Start the application and verify readiness, when an application exists.
6. Run mobile and desktop browser checks, when a UI exists.
7. Upload evidence with a finite retention period.

Keep framework-specific startup and screenshot commands in small project scripts, outside domain logic.

## Local and pull-request verification

Document exact environment, installation, compilation, test, startup, and browser commands so contributors can reproduce CI without production credentials. Before opening a PR, update from accepted main, inspect the complete diff, run the same checks as CI, review screenshots, and record limitations and manual checks.

## Merge protection

In GitHub, open **Settings → Branches** or **Settings → Rules → Rulesets**, target the default branch, and consider:

- requiring a pull request and at least one approving review;
- dismissing stale approvals and requiring conversation resolution;
- requiring the repository's stable CI check;
- requiring an up-to-date branch when it fits the merge strategy;
- blocking force pushes and branch deletion;
- restricting bypass permission to named maintainers.

After saving, verify the rule in repository settings and with a test PR. Record the exact required-check name because workflow and job renames can change it. Documentation alone does not enable protection; never claim it is active without direct verification.

## Transfer checklist

- Replace repository names, paths, runtime versions, commands, readiness assertions, artifact names, and check names.
- Remove UI steps for non-UI projects and choose browser coverage from supported clients.
- Define new domain requirements, validation sources, data governance, and acceptance thresholds independently.
- Verify permissions, secrets, environments, and protection rules directly in the new repository.
