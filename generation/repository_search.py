import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATED_REPOSITORY = (
    PROJECT_ROOT / "LocatorRepository" / "validated_locator_repository.json"
)
CANDIDATE_REPOSITORY = (
    PROJECT_ROOT / "LocatorRepository" / "smart_locator_repository.json"
)


class RepositorySearch:
    """Search device-validated locators, with an explicit candidate fallback."""

    def __init__(
        self,
        validated_repository=VALIDATED_REPOSITORY,
        candidate_repository=CANDIDATE_REPOSITORY,
        allow_candidate_fallback=False,
    ):
        self.validated_repository = Path(validated_repository)
        self.candidate_repository = Path(candidate_repository)
        self.allow_candidate_fallback = allow_candidate_fallback
        self.validated_locators = self._load(self.validated_repository)
        self.candidate_locators = (
            self._load(self.candidate_repository)
            if allow_candidate_fallback
            else []
        )
        self.last_match_source = None

    @staticmethod
    def _load(path):
        if not path.is_file():
            return []
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"Locator repository must contain a list: {path}")
        return data

    @staticmethod
    def _matches(item, target, partial=False):
        name = str(item.get("name", "")).lower()
        value = str(item.get("locator", {}).get("value", "")).lower()
        if partial:
            return target in name or target in value
        return name == target or value == target

    def _search_collection(self, locators, target):
        for partial in (False, True):
            for item in locators:
                if self._matches(item, target, partial=partial):
                    return item
        return None

    def search(self, target):
        target = str(target).strip().lower()
        self.last_match_source = None
        if not target:
            return None

        result = self._search_collection(self.validated_locators, target)
        if result:
            self.last_match_source = "validated"
            return result

        if self.allow_candidate_fallback:
            result = self._search_collection(self.candidate_locators, target)
            if result:
                self.last_match_source = "candidate"
                return result

        return None


if __name__ == "__main__":
    repository = RepositorySearch(allow_candidate_fallback=True)
    for test in ("HOME", "TRENDING", "Account", "India", "Search"):
        print(test, repository.last_match_source, repository.search(test))
