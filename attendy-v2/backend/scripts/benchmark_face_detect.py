"""One-off benchmark: measures FaceEngine.detect() wall time at different det_size
settings against a real enrolled photo, to decide the detection-resolution tradeoff
for /ws/recognize latency. Not part of the test suite -- run manually.
"""
import time

import cv2
from insightface.app import FaceAnalysis

PHOTO_PATH = "uploads/students/6e83643b-8020-4daa-98e8-b3f0c5ddaa1e.jpg"
N_RUNS = 15


def bench(det_size: tuple[int, int], allowed_modules: list[str] | None) -> None:
    app = FaceAnalysis(name="buffalo_l", allowed_modules=allowed_modules, providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=det_size)

    image = cv2.imread(PHOTO_PATH)

    app.get(image)  # warm-up, excluded from timing

    times = []
    for _ in range(N_RUNS):
        start = time.perf_counter()
        faces = app.get(image)
        times.append(time.perf_counter() - start)

    times.sort()
    p50 = times[len(times) // 2]
    p95 = times[int(len(times) * 0.95)]
    label = "all-5-models" if allowed_modules is None else "+".join(allowed_modules)
    print(
        f"det_size={det_size} modules={label}: faces={len(faces)} "
        f"p50={p50*1000:.1f}ms p95={p95*1000:.1f}ms min={min(times)*1000:.1f}ms max={max(times)*1000:.1f}ms"
    )


if __name__ == "__main__":
    for size in [(640, 640), (320, 320)]:
        bench(size, allowed_modules=None)
        bench(size, allowed_modules=["detection", "recognition"])
