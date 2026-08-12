import json


class LocatorSelector:

    def __init__(self, client, model="gpt-5.4"):
        self.client = client
        self.model = model

    def build_prompt(self, scenario, action, target, candidates):

        prompt = f"""
You are a Senior Mobile Automation Engineer.

Scenario:
{scenario}

Action:
{action}

Target:
{target}

Candidate Locators:

"""

        for i, candidate in enumerate(candidates, start=1):
            locator = candidate["locator"]

            prompt += f"""
{i}.
Name: {candidate['name']}
Type: {locator['type']}
Value: {locator['value']}
Priority: {locator['priority']}
"""

        prompt += """

Rules:
- Prefer resource-id over text.
- Prefer accessibilityText over text.
- Ignore Android system IDs.
- Ignore dynamic text.
- Return ONLY valid JSON.

Example:

{
    "selected": 1,
    "reason": "resource-id is the most stable locator"
}
"""

        return prompt

    def select_locator(self, scenario, parsed_step, candidates):

        prompt = self.build_prompt(
            scenario,
            parsed_step["action"],
            parsed_step["target"],
            candidates
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        text = response.output_text.strip()
        result = json.loads(text)
        selected = result.get("selected")
        if not isinstance(selected, int) or not 1 <= selected <= len(candidates):
            raise ValueError("AI returned an invalid locator selection")
        return result
