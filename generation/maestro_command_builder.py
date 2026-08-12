class MaestroCommandBuilder:

    def build(self, action, locator):

        locator_type = locator["type"]
        locator_value = locator["value"]

        command = {
            "command": action,
            "parameters": {}
        }

        if locator_type == "id":
            command["parameters"]["id"] = locator_value

        elif locator_type == "text":
            command["parameters"]["text"] = locator_value

        elif locator_type == "accessibilityText":
            # Maestro matches accessibility labels through its text selector.
            command["parameters"]["text"] = locator_value

        return command
