from maestro_test_builder import MaestroTestBuilder
from yaml_writer import YAMLWriter
from pathlib import Path

builder = MaestroTestBuilder()

builder.set_app("com.mobstac.thehindu")

builder.add_tags([
    "smoke",
    "article"
])

builder.run_flow("../Common/LOGIN.yaml")
builder.tap_on(id="nav_home")
builder.scroll()

test = builder.build()

writer = YAMLWriter()
output_file = Path(__file__).resolve().parent.parent / "GeneratedTests" / "demo_test.yaml"
saved_file = writer.write_file(test, output_file)

print(writer.write(test))
print(f"Saved to: {saved_file}")
