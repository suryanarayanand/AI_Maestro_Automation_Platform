class LogAnalyzer:
    ERROR_MARKERS = ("error", "exception", "failed", "fatal")

    def analyze(self, text):
        lines = str(text).splitlines()
        errors = [line for line in lines if any(marker in line.lower() for marker in self.ERROR_MARKERS)]
        return {"error_count": len(errors), "errors": errors}
