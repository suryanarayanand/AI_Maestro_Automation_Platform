class ExecutionAnalyzer:
    def analyze(self, return_code, stdout="", stderr=""):
        return {"status": "passed" if return_code == 0 else "failed", "return_code": return_code,
                "stdout": stdout, "stderr": stderr}
