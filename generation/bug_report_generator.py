class BugReportGenerator:
    def generate(self, title, root_cause, steps=None):
        return {"title": title, "status": root_cause.get("status"),
                "probable_cause": root_cause.get("probable_cause"), "steps_to_reproduce": steps or []}
