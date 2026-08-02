"""Proves the Hungarian-algorithm assignment in FaceTracker.assign() correctly keeps
each detection matched to the track at its own position regardless of the order faces
come back from detection, and that stale tracks get pruned instead of accumulating
forever on a long-running connection.
"""
from app.services.tracker import MAX_UNMATCHED_FRAMES, FaceTracker

BBOX_A = (0.0, 0.0, 10.0, 10.0)
BBOX_B = (100.0, 100.0, 110.0, 110.0)


def test_assign_keeps_identity_by_position_regardless_of_detection_order():
    tracker = FaceTracker()

    # Frame 1: two faces, at positions A and B, in that order.
    track_a, track_b = tracker.assign([BBOX_A, BBOX_B])
    assert track_a is not track_b

    # Frame 2: same two faces, but the detector this time returns them in the
    # opposite order (B first, then A) -- a real possibility, detection order isn't
    # guaranteed stable frame to frame. A naive "first detection grabs the nearest
    # unclaimed track" greedy match still happens to get this right when boxes don't
    # overlap at all, so nudge both boxes slightly to make the point sharply: the
    # assignment must be by *position*, not by input order.
    nudged_b = (99.0, 99.0, 109.0, 109.0)
    nudged_a = (1.0, 1.0, 11.0, 11.0)
    matched_b_first, matched_a_second = tracker.assign([nudged_b, nudged_a])

    assert matched_b_first is track_b
    assert matched_a_second is track_a


def test_assign_starts_new_track_for_unmatched_detection():
    tracker = FaceTracker()
    tracker.assign([BBOX_A])

    # A third, unrelated face appears far from any existing track.
    far_away = (500.0, 500.0, 510.0, 510.0)
    (only_track,) = tracker.assign([far_away])

    assert only_track.bbox == far_away


def test_stale_tracks_are_pruned_after_enough_unmatched_frames():
    tracker = FaceTracker()
    tracker.assign([BBOX_A])
    assert len(tracker._tracks) == 1

    # The face leaves frame -- no detections for enough consecutive frames that the
    # track should be dropped rather than held onto forever.
    for _ in range(MAX_UNMATCHED_FRAMES + 1):
        tracker.assign([])

    assert tracker._tracks == []
