"""Standalone proof: InsightFace detection + embedding + cosine similarity actually
separates distinct people, before any camera UI or DB code depends on it.

Run with: python -m scripts.calibrate_threshold <path_to_image_dir_of_subfolders_per_person>
Each subfolder should contain one or more images of one person.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app.services.face_engine import FaceEngine, cosine_similarity  # noqa: E402


def main() -> None:
    root = Path(sys.argv[1])
    engine = FaceEngine(model_pack="buffalo_l")

    people: dict[str, list[np.ndarray]] = {}
    for person_dir in sorted(root.iterdir()):
        if not person_dir.is_dir():
            continue
        embeddings = []
        for img_path in sorted(person_dir.iterdir()):
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            faces = engine.detect(img)
            if not faces:
                print(f"  [NO FACE DETECTED] {img_path}")
                continue
            best = max(faces, key=lambda f: f.det_score)
            print(f"  [OK] {img_path.name}: det_score={best.det_score:.3f}")
            embeddings.append(best.embedding)
        if embeddings:
            people[person_dir.name] = embeddings

    print("\n--- Same-person similarities (want HIGH) ---")
    for name, embs in people.items():
        for i in range(len(embs)):
            for j in range(i + 1, len(embs)):
                sim = cosine_similarity(embs[i], embs[j])
                print(f"  {name} #{i} vs #{j}: {sim:.4f}")

    print("\n--- Cross-person similarities (want LOW) ---")
    names = list(people.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            for a in people[names[i]]:
                for b in people[names[j]]:
                    sim = cosine_similarity(a, b)
                    print(f"  {names[i]} vs {names[j]}: {sim:.4f}")


if __name__ == "__main__":
    main()
