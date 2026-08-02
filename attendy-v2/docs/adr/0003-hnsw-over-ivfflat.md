# ADR 0003: HNSW over IVFFlat for the face-embedding index

## Status
Accepted (revisit if enrollment grows past ~50k students)

## Context
`face_embeddings.embedding` (512-d ArcFace vectors) needs a nearest-neighbor search
per detected face per frame (`matcher.find_best_match`, `<=>` cosine-distance
operator). pgvector offers two index types:

- **IVFFlat** — clusters vectors into `lists` buckets at build time, probes the
  nearest `probes` buckets per query. Cheaper to build and smaller on disk, but
  recall depends on choosing `lists` for the *expected* row count up front, and
  quality degrades on a table that grows a lot after the index was built (a fixed
  clustering going stale) unless it's rebuilt periodically.
- **HNSW** — a navigable small-world graph. Better recall/latency at query time and
  degrades more gracefully as rows are added incrementally (no upfront row-count
  tuning parameter to get wrong), at the cost of slower index builds and more
  memory per index.

## Decision
HNSW, default parameters (`m=16`, `ef_construction=64` — not overridden;
see `ix_face_embeddings_embedding_hnsw` in
`3250735fe0bb_initial_schema.py`).

This app's write pattern is "insert a handful of embeddings per student enrollment,
essentially never in bulk," and the read pattern is "one nearest-neighbor query per
detected face, several times a second, every scan session." That favors HNSW's
query-time profile and its tolerance of incremental growth over IVFFlat's
build-time cost advantage, which doesn't matter here since embeddings are never
bulk-loaded.

## Consequences
- At a few thousand students (a school's actual scale) HNSW is comfortably fast
  with no tuning — this hasn't needed benchmarking to justify at this size.
- This stops being a config-free decision well before general "big data" scale:
  once enrollment reaches something like tens of thousands of students, `m`/
  `ef_construction` (build-time) and `hnsw.ef_search` (query-time, session-level
  `SET`) would need actual tuning against real recall/latency numbers, not
  defaults. `scripts/benchmark_face_detect.py` benchmarks the detection pipeline,
  not this index — a follow-up benchmark script seeding synthetic embeddings at
  realistic N would be the right next step before that point, not before it.
