import sys, cv2, numpy as np
from ultralytics import YOLO
from vista_vision import calibration
from vista_vision.homography import apply_homography
from vista_vision.geometry import count_people

clip, calf = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(clip)
n = int(cap.get(7))
print("frame size:", int(cap.get(3)), "x", int(cap.get(4)), "frames:", n, "fps:", cap.get(5))
cap.set(1, n // 2)
ok, frame = cap.read()
assert ok, "frame nahi padha"
cal = calibration.load(calf)
model = YOLO("yolov8n.pt")
for imgsz in (640, 1280):
    r = model.predict(frame, classes=[0], conf=0.25, imgsz=imgsz, verbose=False)[0]
    b = r.boxes
    if len(b) == 0:
        print(f"imgsz {imgsz}: 0 people detected")
        continue
    xyxy = b.xyxy.cpu().numpy()
    foot = np.c_[(xyxy[:, 0] + xyxy[:, 2]) / 2, xyxy[:, 3]]
    res = count_people(apply_homography(cal.H, foot), cal.zone_polygon, cal.camera_xy, cal.range_m)
    print(f"imgsz {imgsz}: detected {len(b)}, counted in zone {res.count}, outside zone {res.outside_zone}, out of range {res.out_of_range}")
    if imgsz == 1280:
        cv2.imwrite("diag.jpg", r.plot())
print("diag.jpg saved")
