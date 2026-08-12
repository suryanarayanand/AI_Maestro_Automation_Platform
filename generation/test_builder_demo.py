from maestro_test_builder import MaestroTestBuilder

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

print(test)
