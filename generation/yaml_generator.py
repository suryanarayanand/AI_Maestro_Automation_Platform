from scenario_parser import parse_step
from repository_search import RepositorySearch
from maestro_command_builder import MaestroCommandBuilder
from maestro_test_builder import MaestroTestBuilder
from yaml_writer import YAMLWriter
from complex_scenario_planner import plan_category_navigation_case, plan_complex_scenario
from intent_action_planner import IntentActionPlanner


class YAMLGenerator:

    def __init__(
        self,
        app_id="com.mobstac.thehindu",
        allow_candidate_fallback=False,
    ):
        self.app_id = app_id
        self.repository = RepositorySearch(
            allow_candidate_fallback=allow_candidate_fallback
        )
        self.command_builder = MaestroCommandBuilder()
        self.writer = YAMLWriter()
        self.intent_planner = IntentActionPlanner()

    def generate_command(self, step):

        parsed = parse_step(step)

        if parsed is None:
            return None

        action = parsed["action"]
        target = parsed["target"]

        if action is None:
            return {
                "error": f"Unsupported action in step '{step}'"
            }

        if action == "takeScreenshot":
            if not target:
                return {"error": f"Screenshot path missing in step '{step}'"}
            return {
                "command": "takeScreenshot",
                "parameters": {"path": target},
            }

        if parsed.get("explicit_locator"):
            return self.command_builder.build(
                action, {"type": "id", "value": target}
            )

        locator = self._select_locator(action, target)

        if locator is None:
            return {
                "error": f"Locator not found for '{target}'"
            }

        return self.command_builder.build(
            action,
            locator["locator"]
        )

    def _select_locator(self, action, target):
        """Prefer navigation/control IDs for taps and screen IDs for assertions."""
        normalized = "_".join(str(target).strip().lower().split())
        candidates = []
        if action == "tapOn":
            candidates.extend((f"nav_{normalized}", f"cta_{normalized}"))
        elif action in ("assertVisible", "assertNotVisible", "extendedWaitUntil"):
            candidates.append(f"screen_{normalized}")
        candidates.append(target)

        for candidate in candidates:
            locator = self.repository.search(candidate)
            if locator is not None:
                return locator
        return None

    def generate_test(self, steps, tags=None, case_id="GENERATED"):
        test_builder = MaestroTestBuilder()
        test_builder.set_app(self.app_id)
        test_builder.add_tags(tags or [])

        case_commands = plan_category_navigation_case(case_id)
        if case_commands:
            for item in case_commands:
                test_builder.add_step(item["command"], item.get("parameters", {}))
            return test_builder.build()

        for step in steps:
            complex_commands = plan_complex_scenario(step, case_id)
            if complex_commands:
                for item in complex_commands:
                    test_builder.add_step(item["command"], item.get("parameters", {}))
                continue
            intent_commands = self.intent_planner.plan(step, case_id)
            if intent_commands:
                for item in intent_commands:
                    test_builder.add_step(item["command"], item.get("parameters", {}))
                continue
            command = self.generate_command(step)

            if command is None:
                raise ValueError(f"Unable to parse step: {step}")

            if "error" in command:
                raise ValueError(command["error"])

            test_builder.add_step(
                command["command"],
                command.get("parameters", {})
            )

        return test_builder.build()

    def generate_yaml(self, steps, tags=None, case_id="GENERATED"):
        test = self.generate_test(steps, tags, case_id)
        return self.writer.write(test)

    def generate_file(self, steps, output_file, tags=None, case_id="GENERATED"):
        test = self.generate_test(steps, tags, case_id)
        return self.writer.write_file(test, output_file)


if __name__ == "__main__":

    generator = YAMLGenerator()

    scenario = [
        "Open Videos tab",
        "Tap Home",
        "Open Account"
    ]

    print(generator.generate_yaml(scenario, tags=["smoke"]))
