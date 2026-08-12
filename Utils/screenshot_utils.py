from pathlib import Path

def get_screenshots(folder):
    """
    Returns all PNG screenshots inside a folder recursively.
    """

    folder = Path(folder)

    if not folder.exists():
        return []

    screenshots = sorted(folder.rglob("*.png"))

    return screenshots


def get_scenario_folder(screenshot_root, scenario_id):
    """
    Example:
    Screenshots/
        SC_02/
        SC_05/
    """

    folder = Path(screenshot_root) / scenario_id

    if folder.exists():
        return folder

    return None


def count_screenshots(folder):

    folder = Path(folder)

    return len(list(folder.rglob("*.png")))

