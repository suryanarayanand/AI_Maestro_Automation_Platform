# AI Maestro Automation Platform

Consolidated Flask, Maestro, AI test-generation, visual-analysis, and reporting framework.

## Current components

- `web/`: Flask dashboard, routes, templates, and execution services
- `generation/`: Excel reader, locator selection, Maestro command generation, and YAML generation
- `Uploads/`: uploaded Excel workbooks
- `ApprovalQueue/`: generated YAML awaiting manual review
- `GeneratedTests/`: generated output before approval
- `Scenarios/`: approved runnable Maestro scenarios
- `Suites/`: smoke, sanity, and regression definitions
- `Utils/`: screenshot AI, visual regression, and report generation
- `Reports/`: execution reports and consolidated bug summaries

Start the portal with `Run_Framework.bat` or `python app.py`, then open
`http://127.0.0.1:5000`. Suite execution is queued through the portal; do not
use the old command-line suite menu.

## Portal workflow

1. Sign in and upload an `.xlsx` workbook from **Generate & Approve**.
2. Review or edit each generated YAML draft.
3. Approve the draft into smoke, sanity, or regression.
4. Queue a suite from **Test Suites** or **Execution Jobs**.
5. Run `python maestro_agent.py` on the machine that has Maestro and the device.
6. Follow current-case progress and consolidated failures from the job page.

The initial development login is `admin` / `admin`. Set `PORTAL_ADMIN_USER`,
`PORTAL_ADMIN_PASSWORD`, `PORTAL_SECRET_KEY`, and `MAESTRO_AGENT_TOKEN` before
the first production start. The portal and agent must use the same agent token.

For a remote agent, set `MAESTRO_PORTAL_URL` to the hosted portal URL.

Authenticated scenarios read credentials from `credentials.local.json`, which
is intentionally excluded from Git. Update that one file whenever the test
account changes. The optional `MAESTRO_TEST_EMAIL` and
`MAESTRO_TEST_PASSWORD` environment variables override the local file.
