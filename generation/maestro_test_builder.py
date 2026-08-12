class MaestroTestBuilder:

    def __init__(self):
        self.test = {
            "appId": "",
            "tags": [],
            "steps": []
        }

    # -------------------------
    # Metadata
    # -------------------------

    def set_app(self, app_id):
        self.test["appId"] = app_id

    def add_tag(self, tag):
        self.test["tags"].append(tag)

    def add_tags(self, tags):
        self.test["tags"].extend(tags)

    # -------------------------
    # Generic
    # -------------------------

    def add_step(self, command, parameters=None):
        if not command:
            raise ValueError("A Maestro step must contain a command.")

        if parameters is None:
            parameters = {}

        if not isinstance(parameters, dict):
            raise TypeError("Step parameters must be a dictionary.")

        self.test["steps"].append({
            "command": command,
            "parameters": parameters
        })

    # -------------------------
    # Maestro Commands
    # -------------------------

    def launch_app(self, clear_state=True):
        self.add_step("launchApp", {"clearState": clear_state})

    def run_flow(self, path):
        self.add_step("runFlow", {"path": path})

    def tap_on(self, **locator):
        self.add_step("tapOn", locator)

    def assert_visible(self, **locator):
        self.add_step("assertVisible", locator)

    def scroll(self):
        self.add_step("scroll")

    def swipe(self, direction):
        self.add_step("swipe", {"direction": direction})

    def take_screenshot(self, path):
        self.add_step("takeScreenshot", {"path": path})

    def wait_for_animation(self):
        self.add_step("waitForAnimationToEnd")

    # -------------------------

    def build(self):
        return self.test
