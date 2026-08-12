import argparse
import json
from pathlib import Path

from excel_reader import ExcelReader
from yaml_generator import YAMLGenerator

ROOT = Path(__file__).resolve().parent.parent


class AITestGenerator:
    def __init__(self, config_path=ROOT / "config.json"):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.reader = ExcelReader()
        self.generator = YAMLGenerator(self.config["app_id"])

    def generate(self, excel_path, output_dir=None):
        generation = self.config.get("generation", {})
        output = Path(output_dir or ROOT / generation.get("generatedFolder", "GeneratedTests"))
        generated = []
        for case in self.reader.group_cases(excel_path):
            filename = "".join(c if c.isalnum() or c in "-_" else "_" for c in case["id"])
            destination = output / f"{filename}.yaml"
            self.generator.generate_file(
                case["steps"], destination, tags=["generated"], case_id=case["id"]
            )
            generated.append(destination)
        return generated


def main():
    parser = argparse.ArgumentParser(description="Generate Maestro suites from Excel test cases")
    parser.add_argument("excel", help="Path to the Excel workbook")
    parser.add_argument("--output", help="Output directory")
    args = parser.parse_args()
    for path in AITestGenerator().generate(args.excel, args.output):
        print(path)


if __name__ == "__main__":
    main()
