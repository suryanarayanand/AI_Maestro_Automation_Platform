from pathlib import Path


class YAMLWriter:

    SIMPLE_COMMANDS = {
        "back",
        "hideKeyboard",
        "scroll",
        "stopApp",
    }

    @staticmethod
    def _scalar(value):
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return str(value)
        return f'"{value}"'

    def _write_mapping(self, lines, mapping, indent):
        prefix = " " * indent
        for key, value in mapping.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                self._write_mapping(lines, value, indent + 2)
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                self._write_list(lines, value, indent + 2)
            else:
                lines.append(f"{prefix}{key}: {self._scalar(value)}")

    def _write_list(self, lines, values, indent):
        prefix = " " * indent
        for value in values:
            if isinstance(value, dict):
                first, *remaining = value.items()
                key, nested = first
                if isinstance(nested, dict):
                    lines.append(f"{prefix}- {key}:")
                    self._write_mapping(lines, nested, indent + 4)
                else:
                    lines.append(f"{prefix}- {key}: {self._scalar(nested)}")
                if remaining:
                    self._write_mapping(lines, dict(remaining), indent + 2)
            else:
                lines.append(f"{prefix}- {self._scalar(value)}")

    def write(self, test):

        lines = []

        # App ID
        lines.append(f'appId: {test["appId"]}')

        # Tags
        if test["tags"]:
            lines.append("tags:")
            for tag in test["tags"]:
                lines.append(f"  - {tag}")

        lines.append("---")
        lines.append("")

        # Steps
        for step in test["steps"]:

            command = step["command"]
            parameters = step.get("parameters", {})

            # Commands with no parameters use Maestro's short form.
            if not parameters:
                lines.append(f"- {command}")
                lines.append("")
                continue

            # Flow and screenshot paths are represented as scalars in Maestro YAML.
            if command in {"runFlow", "takeScreenshot"} and set(parameters) == {"path"}:
                lines.append(f'- {command}: "{parameters["path"]}"')
                lines.append("")
                continue

            # Commands with parameters
            lines.append(f"- {command}:")

            self._write_mapping(lines, parameters, 4)

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def write_file(self, test, output_file):
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.write(test), encoding="utf-8")
        return output_path
