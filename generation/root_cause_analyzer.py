class RootCauseAnalyzer:
    def analyze(self, execution, logs=None, screenshot=None):
        if execution.get("status") == "passed":
            cause = "No failure detected"
        elif logs and logs.get("errors"):
            cause = logs["errors"][0]
        else:
            cause = execution.get("stderr") or "Undetermined execution failure"
        return {"status": execution.get("status"), "probable_cause": cause, "screenshot": screenshot}
