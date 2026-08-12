# AI Maestro Automation Platform — Session Handoff

Date: 10 August 2026  
Project: `D:\AI_Maestro_Automation_Platform`  
Device: Samsung `R9ZY40T6PHN` (`SM_E066B`)  
Application: `com.mobstac.thehindu`

## Objective

Build a self-contained portal workflow that accepts Excel test scenarios, normalizes them, converts unsupported natural-language steps into repository-grounded actions using AI, generates Maestro YAML, and presents the result for human approval without requiring an external assistant.

## Current portal workflow

1. Open `http://127.0.0.1:5000/generator`.
2. Upload an `.xlsx` workbook.
3. Keep **Automatically adapt unsupported steps with AI** selected.
4. Click **Convert Excel & Generate YAML**.
5. The portal first tries deterministic generation.
6. Only cases containing unsupported steps use the OpenAI structured-output fallback.
7. AI output is grounded against existing Common flows, locator screens, and validated locator names.
8. The AI steps are compiled by the existing YAML generator.
9. The review page displays generation mode, confidence, assumptions, errors, and YAML.
10. Nothing enters a suite until a reviewer approves it.

## Excel workbook under investigation

`C:\Users\12503\Downloads\Automation_Test_Cases_TH_0006_to_TH_0010.xlsx`

Sheet: `Automation_Test_Cases`

Columns:

- Scenario No
- Test Scenario
- Test Steps
- Expected Result
- Automation Coverage

Cases: `TH_0006` through `TH_0010`.

Original deterministic blockers included:

- `TH_0006`: Keep the application running in foreground or idle in background.
- `TH_0007`: Ensure user is not logged in.
- `TH_0008`: Navigate to onboarding screen.
- `TH_0009`: Navigate to onboarding screen.
- `TH_0010`: Locator not found for Home load completely.

The workbook format itself is supported. These failures were caused by unsupported or ungrounded actions, not by Excel parsing.

## Changes completed on 10 August 2026

### Portal AI fallback

Updated `web/services/generation_service.py`:

- `create_drafts(excel_path, use_ai=True)` now attempts deterministic YAML first.
- Unsupported cases are sent to `AIScenarioExpander`.
- AI-generated steps are compiled by `YAMLGenerator`.
- Drafts record `rules` or `ai` generation mode.
- Failed AI adaptation preserves both the deterministic and AI error.

### Database migration

Updated `web/portal_db.py` with additive draft columns:

- `generation_mode`
- `ai_confidence`
- `ai_assumptions`

No existing draft or job data was deleted.

### Portal interface

Updated:

- `web/routes/generator.py`
- `web/templates/generator.html`
- `web/templates/review_yaml.html`

The upload page now includes a checked AI fallback option. The approval queue shows how each draft was generated. The review screen shows AI confidence and assumptions.

### AI grounding and timeout

Existing `AI/ai_scenario_expander.py` uses the OpenAI Responses API with a strict JSON schema. Its prompt is grounded to:

- Existing `Common/*.yaml` files
- Validated locator repository screens
- Validated locator names
- Known modules and pages
- A restricted executable sentence grammar

The OpenAI client now has configurable bounds:

- `OPENAI_SCENARIO_TIMEOUT`, default `90` seconds
- `OPENAI_SCENARIO_RETRIES`, default `1`
- `OPENAI_SCENARIO_MODEL`, currently defaults to `gpt-5.6-sol`

`OPENAI_API_KEY` was confirmed as configured without exposing its value.

### Supported common-flow parsing

`generation/intent_action_planner.py` recognizes instructions such as:

`Run OPEN_HOME_FOR_LOCATOR_SMOKE.yaml`

It emits a grounded Maestro `runFlow` command only when that file exists under `Common`.

## Validation completed

- Portal database migration: successful.
- API key presence check: successful.
- Twenty regression tests passed across AI expansion, intent planning, and portal behavior.
- Ten focused AI/planner tests passed again after adding API timeout controls.
- Portal restarted successfully and is listening at `http://127.0.0.1:5000`.

The five-case live AI conversion diagnostic was stopped because the API request remained active for too long before timeout controls were added. Therefore, the exact workbook still needs a fresh upload through the restarted portal.

## SC-29 category work completed earlier

The oversized category flow was split into:

- `Scenarios/SC_29_INDIA.yaml`
- `Scenarios/SC_29_WORLD.yaml`
- `Scenarios/SC_29_SPORT.yaml`
- Suite: `Suites/SC29Split.json`

Portal execution evidence:

- India: PASS
- Sport: PASS
- World initial run: timing failure
- World retry with destination wait: PASS
- Portal jobs: `59` and successful World retry `60`

The split files are preferable to restoring the monolithic `SC_29_gen.yaml` because the original 130-command flow exceeded direct Maestro control timeouts.

## SC-27 Games status

Games work included Sudoku, Cryptic Crossword, The Hindu Mini, Easy Down, Word Row, Word Flower, Word Search, and News Quiz. Sudoku was reported as passed. Cryptic Crossword remains dependent on subscriber authentication and a verified subscriber-only locator. The complete Games suite still needs systematic execution and correction one game at a time.

Validated Games locator names previously added include:

- Sudoku
- The Hindu Mini
- Easy Down

Do not weaken assertions or invent subscriber-only locators. Validate missing targets on the connected Samsung first.

## Known Maestro lesson

Studio and CLI can behave differently because of state, timing, credentials, WebView transitions, and duplicated labels. Use explicit waits, stable resource IDs, contextual/indexed selectors, and independent reset routes. Generic selectors such as `tapOn: "India"` or `tapOn: "News"` are unsafe when duplicate labels exist.

## Immediate next steps after restart

1. Start the portal if it is not listening on port 5000.
2. Confirm `OPENAI_API_KEY` is available to the portal process.
3. Open `/generator` and upload `Automation_Test_Cases_TH_0006_to_TH_0010.xlsx`.
4. Leave AI adaptation enabled.
5. Record the draft IDs and inspect every generated YAML, confidence score, and assumption.
6. Do not approve a draft whose assumptions omit a core requirement.
7. Run approved YAML through the portal agent on `R9ZY40T6PHN`.
8. Correct the first reproducible Maestro failure before moving to the next case.
9. After this workbook passes, resume the remaining SC-27 Games scenarios.

## Restart prompt for the next assistant session

Use this exact instruction after providing this document:

> Continue the AI Maestro Automation Platform work from this handoff. First verify the portal, database migration, API-key availability, device connection, and current draft/job status. Then upload `C:\Users\12503\Downloads\Automation_Test_Cases_TH_0006_to_TH_0010.xlsx` through the portal with AI fallback enabled. Inspect the resulting drafts and fix the first genuine conversion or Maestro execution failure. Preserve existing user changes and do not approve YAML with unresolved core requirements.

## Important safety and operating rules

- Preserve existing portal drafts, suites, reports, screenshots, and user edits.
- Do not run competing Maestro flows simultaneously.
- Keep the Samsung connected, unlocked, and awake during execution.
- Never print or store the OpenAI API key in logs or handoff documents.
- AI output must remain reviewable; approval is always a human action.
- Use only repository-backed flows and validated selectors.
