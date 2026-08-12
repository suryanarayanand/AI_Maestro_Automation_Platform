"""Translate common business-step intents into deterministic Maestro commands."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAVIGATION_REPOSITORY = ROOT / "LocatorRepository" / "navigation_repository.json"
COMMON_FOLDER = ROOT / "Common"


class IntentActionPlanner:
    def __init__(self, navigation_repository=NAVIGATION_REPOSITORY):
        self.navigation = self._load_navigation(navigation_repository)

    @staticmethod
    def _load_navigation(path):
        path = Path(path)
        if not path.is_file():
            return {}
        entries = json.loads(path.read_text(encoding="utf-8"))
        return {str(entry["page"]).casefold(): entry for entry in entries if entry.get("page")}

    @staticmethod
    def _command(command, parameters=None):
        return {"command": command, "parameters": parameters or {}}

    @staticmethod
    def _screenshot_path(case_id, text):
        safe_case = re.sub(r"[^A-Za-z0-9_-]", "_", str(case_id))
        description = re.sub(
            r"\b(capture|take|a|the|screenshot|screenshots|showing|of|after|during|for)\b",
            " ", text, flags=re.IGNORECASE,
        )
        safe_description = re.sub(r"[^A-Za-z0-9]+", "_", description).strip("_").lower()[:55]
        return f"Screenshots/Generated/{safe_case}_{safe_description or 'evidence'}"

    def plan(self, step, case_id="GENERATED"):
        text = " ".join(str(step).split())
        lowered = text.casefold()
        commands = []

        common_flow = re.search(r"\b([A-Za-z0-9_.-]+\.yaml)\b", text, re.IGNORECASE)
        if common_flow and lowered.startswith(("run ", "execute ")):
            requested = Path(common_flow.group(1)).name
            match = next(
                (path.name for path in COMMON_FOLDER.glob("*.yaml") if path.name.casefold() == requested.casefold()),
                None,
            )
            if match:
                return [self._command("runFlow", {"path": f"../Common/{match}"})]

        if lowered.startswith("launch "):
            return [self._command("launchApp", {"clearState": "fresh" in lowered})]
        if lowered.startswith("relaunch ") or lowered == "relaunch application":
            return [self._command("launchApp", {"clearState": False, "stopApp": True})]
        if lowered.startswith("skip ") and "onboarding" in lowered:
            return [self._command("runFlow", {"path": "../Common/Anonymous_account_onboarding.yaml"})]
        if (lowered.startswith("log in") or lowered.startswith("login")) and "subscriber" in lowered:
            return [self._command("runFlow", {"path": "../Common/LOGIN.yaml"})]
        if lowered.startswith("navigate back") or lowered.startswith("go back"):
            return [self._command("back")]

        if lowered.startswith("open the application menu/settings") or lowered.startswith("open application menu/settings"):
            return [self._command("tapOn", {"id": "nav_account"})]
        if lowered.startswith("navigate to the appearance") or lowered.startswith("open appearance"):
            return [self._command("tapOn", {"text": "Appearance"})]
        if lowered.startswith("verify") and "dark mode option" in lowered:
            return [self._command("assertVisible", {"text": "Dark\\nMode"})]
        if lowered.startswith("enable dark mode"):
            return [self._command("tapOn", {"text": "Dark\\nMode"})]

        if lowered.startswith("open") and "hamburger menu" in lowered:
            return [self._command("tapOn", {"id": "nav_menu"})]

        if lowered.startswith("navigate to") and "games section" in lowered:
            return [self._command("tapOn", {"id": "nav_games"})]
        if lowered.startswith("navigate back to") and "games section" in lowered:
            return [self._command("tapOn", {"id": "nav_games"})]

        expanded = re.match(r"expand the (.+?) category", lowered)
        if expanded:
            category = expanded.group(1).strip().title()
            return [self._command("tapOn", {"text": category})]
        if lowered.startswith("navigate back to the category list"):
            return [self._command("tapOn", {"id": "nav_menu"})]

        for game in ("Sudoku", "The Hindu Mini", "Easy Down"):
            if lowered.startswith("open") and game.casefold() in lowered:
                return [self._command("tapOn", {"text": game})]

        if lowered in {"verify home page", "verify the home page", "home page is displayed"} or (
            lowered.startswith("verify")
            and re.search(r"\bhome\b", lowered)
            and re.search(r"\b(loads?|loaded|displayed|visible|successfully)\b", lowered)
            and "header" not in lowered
        ):
            return [self._command("assertVisible", {"id": "screen_home"})]
        if lowered.startswith("verify") and "games page" in lowered:
            return [self._command("assertVisible", {"id": "screen_games"})]
        if lowered.startswith("verify") and "hamburger menu" in lowered:
            return [self._command("assertVisible", {"id": "screen_hamburger"})]

        navigation = self._navigation_intent(lowered)
        if navigation:
            for raw in navigation.get("steps", []):
                command, parameters = next(iter(raw.items()))
                commands.append(self._command(command, parameters if isinstance(parameters, dict) else {"text": parameters}))
            return commands

        if lowered.startswith("verify"):
            for page, entry in self.navigation.items():
                if page in lowered and ("page" in lowered or "section" in lowered):
                    return [self._command("assertVisible", entry.get("identity", {"text": entry["page"]}))]

        if lowered.startswith("scroll") or lowered.startswith("swipe"):
            commands = [
                self._command("swipe", {"direction": "UP"}),
                self._command("waitForAnimationToEnd"),
            ]
            if "screenshot" in lowered:
                commands.append(self._command("takeScreenshot", {"path": self._screenshot_path(case_id, text)}))
            return commands

        if lowered.startswith("capture screenshot") or lowered.startswith("capture a screenshot") \
                or lowered.startswith("capture screenshots") or lowered.startswith("take screenshot"):
            return [self._command("takeScreenshot", {"path": self._screenshot_path(case_id, text)})]

        return None

    def _navigation_intent(self, lowered):
        if not (lowered.startswith("navigate to") or lowered.startswith("open")):
            return None
        for page, entry in self.navigation.items():
            if re.search(rf"\b{re.escape(page)}\b", lowered):
                return entry
        return None
