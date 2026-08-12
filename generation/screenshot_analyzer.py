from pathlib import Path


class ScreenshotAnalyzer:
    def analyze(self, screenshot):
        path = Path(screenshot)
        return {"path": str(path), "exists": path.is_file(), "status": "pending_ai_validation"}
