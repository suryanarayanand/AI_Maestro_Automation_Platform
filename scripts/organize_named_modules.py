import json
from pathlib import Path


root = Path(__file__).resolve().parents[1] / "Suites"
mapping = {
    "ANON_HOME_": "Home", "SUB_HOME_": "Home",
    "ANON_TREND_": "Trending", "SUB_TREND_": "Trending",
    "ANON_PREM_": "Premium", "SUB_PREM_": "Premium",
    "ANON_EBOOK_": "eBooks", "SUB_EBOOK_": "eBooks",
    "ANON_GAMES_": "Games", "SUB_GAMES_": "Games",
    "ANON_HAM_": "Hamburger Menu", "SUB_HAM_": "Hamburger Menu",
    "CPLX_HAM_": "Hamburger Menu", "HAM_OPT_": "Hamburger Menu",
    "ANON_ACCOUNT_": "Account Settings", "SUB_ACCOUNT_": "Account Settings",
    "ANON_LOGIN_": "Login", "SUB_LOGIN_": "Login", "LOGIN_": "Login",
    "ANON_SEARCH_": "Search", "SUB_SEARCH_": "Search",
    "ANON_ARTICLE_": "Article Page", "SUB_ARTICLE_": "Article Page",
    "ANON_VIDEO_": "Videos", "SUB_VIDEO_": "Videos",
    "ANON_PHOTO_": "Photos", "SUB_PHOTO_": "Photos",
    "ANON_EDITORIAL_": "Editorial", "SUB_EDITORIAL_": "Editorial",
    "ANON_OPINION_": "Opinion", "SUB_OPINION_": "Opinion",
    "ANON_PODCAST_": "Podcast", "SUB_PODCAST_": "Podcast",
}
changed_files = changed_cases = 0
for path in root.glob("*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for test in data.get("tests", []):
        case_id = str(test.get("id", "")).upper()
        module = next((name for prefix, name in mapping.items() if case_id.startswith(prefix)), None)
        if module and (test.get("module") != module or test.get("section") != module):
            test["module"] = module
            test["section"] = module
            changed += 1
    if changed:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        changed_files += 1
        changed_cases += changed
        print(path.name, changed)
print({"files": changed_files, "case_entries": changed_cases})
