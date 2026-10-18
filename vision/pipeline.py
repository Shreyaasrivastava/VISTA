"""Live pipeline: RTSP stream -> YOLOv8 + ByteTrack -> ground points -> per-second count -> API.

Not covered by the unit tests (needs ultralytics, opencv and a video source).

  pip install ultralytics opencv-python
  set VISTA_CAMERA_KEY=<ingest key shown once when the camera was created>
  python pipeline.py --source rtsp://localhost:8554/clip1 --calibration calibration.json --api http://localhost:8000

Use --dry-run to print readings instead of sending them.
Use a live or looped RTSP source (MediaMTX + ffmpeg). Timing uses the wall clock.
ByteTrack IDs are available (r.boxes.id) but the count does not use them yet.
"""
import argparse
import os
import sys
import time

import numpy as np

from vista_vision import calibration
from vista_vision.aggregate import SecondAggregator
from vista_vision.geometry import count_people
from vista_vision.homography import apply_homography
from vista_vision.ingest import Ingestor, IngestRejected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="RTSP URL")
    ap.add_argument("--calibration", required=True)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--conf", type=float, default=0.3)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from ultralytics import YOLO  # imported here so the unit tests do not need it

    cal = calibration.load(args.calibration)
    ingestor = None
    if not args.dry_run:
        key = os.environ.get("VISTA_CAMERA_KEY")
        if not key:
            print("Set VISTA_CAMERA_KEY (or use --dry-run).", file=sys.stderr)
            return 2
        ingestor = Ingestor(args.api, key)

    agg = SecondAggregator()
    model = YOLO(args.model)
    frames, t0 = 0, time.time()

    def emit(res):
        if res is None:
            return
        print(f"{time.strftime('%H:%M:%S', time.localtime(res.second))}  count={res.count}  conf={res.confidence}  "
              f"degraded={res.degraded}  frames={res.frames}")
        if ingestor:
            ingestor.send(res.second, res.count, res.confidence, res.degraded)

    try:
        for r in model.track(source=args.source, stream=True, persist=True, tracker="bytetrack.yaml",
                             classes=[0], conf=args.conf, imgsz=args.imgsz, verbose=False):
            boxes = r.boxes
            if boxes is None or len(boxes) == 0:
                foot, conf = np.empty((0, 2)), None
            else:
                xyxy = boxes.xyxy.cpu().numpy()
                foot = np.c_[(xyxy[:, 0] + xyxy[:, 2]) / 2, xyxy[:, 3]]   # bottom centre of each box
                conf = float(boxes.conf.mean())
            ground = apply_homography(cal.H, foot)
            res = count_people(ground, cal.zone_polygon, cal.camera_xy, cal.range_m)
            emit(agg.add(time.time(), res.count, conf))
            frames += 1
    except IngestRejected as e:
        print(f"Server rejected a reading: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        pass
    emit(agg.flush())
    dt = max(time.time() - t0, 1e-9)
    print(f"{frames} frames in {dt:.1f} s ({frames / dt:.1f} fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
