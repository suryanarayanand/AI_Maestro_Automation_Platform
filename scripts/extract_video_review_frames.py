import argparse
from pathlib import Path

import cv2
import numpy as np


def extract(video_path, output_root, interval=5):
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 30
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frames / fps
    output = output_root / video_path.stem
    output.mkdir(parents=True, exist_ok=True)
    timestamps = list(range(0, max(1, int(duration) + 1), interval))
    previews = []
    for seconds in timestamps:
        capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
        ok, frame = capture.read()
        if not ok:
            continue
        cv2.putText(
            frame, f"{seconds // 60:02d}:{seconds % 60:02d}", (24, 44),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 0), 5, cv2.LINE_AA,
        )
        cv2.putText(
            frame, f"{seconds // 60:02d}:{seconds % 60:02d}", (24, 44),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA,
        )
        cv2.imwrite(str(output / f"frame_{seconds:04d}.jpg"), frame)
        preview = cv2.resize(frame, (480, 270))
        previews.append(preview)
    capture.release()
    if previews:
        columns = 3
        blank = np.full_like(previews[0], 245)
        while len(previews) % columns:
            previews.append(blank.copy())
        rows = [np.hstack(previews[index:index + columns])
                for index in range(0, len(previews), columns)]
        cv2.imwrite(str(output / "contact_sheet.jpg"), np.vstack(rows))
    print(f"{video_path.name}: {duration:.1f}s, {len(timestamps)} samples -> {output}")


parser = argparse.ArgumentParser()
parser.add_argument("videos", nargs="+", type=Path)
parser.add_argument("--output", type=Path, default=Path("VideoReview"))
parser.add_argument("--interval", type=int, default=5)
arguments = parser.parse_args()
for video in arguments.videos:
    extract(video, arguments.output, arguments.interval)
