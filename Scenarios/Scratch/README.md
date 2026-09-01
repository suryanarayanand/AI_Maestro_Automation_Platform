# Scratch Flow Workspace

Create new Maestro flows here without modifying validated existing flows.

## Recommended first-flow method

1. Write one observable test objective.
2. Declare exactly one user state: Anonymous, Registered, Subscriber, or Expired.
3. Start from a known fresh app state.
4. Use verified IDs/test tags before text selectors.
5. Add scrolling before interacting with an off-screen element.
6. Keep one action per Maestro command.
7. Assert the actual expected result, not only that a screen opened.
8. Run the flow alone before adding it to a suite.
9. If it fails, verify the locator, user state, test data, and timing before calling it an app bug.

## Suggested folder layout

```text
Scenarios/Scratch/
  anonymous/
  registered/
  subscriber/
  expired/
```

## Minimal flow skeleton

```yaml
appId: com.mobstac.thehindu
tags: [scratch, functional, anonymous]
---
- runFlow: ../../Common/OPEN_ANONYMOUS_HOME.yaml
- assertVisible:
    id: "screen_home"
# Add scenario actions and outcome assertions below.
```

