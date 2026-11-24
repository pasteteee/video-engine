import pytest
from face_engine.evaluation import evaluate_events, tag_intervals, interval_iou


def test_duplicates_are_false_positives():
    r = evaluate_events([(0, 9), (0, 9)], [(0, 9)])
    assert (r['tp'], r['fp'], r['fn']) == (1, 1, 0)
    assert r['recall'] == 1
    assert r['precision'] == .5


def test_maximum_matching_can_reassign():
    r = evaluate_events([(0, 9), (0, 2)], [(0, 4), (5, 9)])
    assert r['tp'] == 2


def test_strict_threshold_and_inclusive_frames():
    assert interval_iou((2, 2), (2, 2)) == 1
    assert evaluate_events([(0, 0)], [(0, 4)])['tp'] == 0
    assert evaluate_events([(0, 0)], [(0, 3)])['tp'] == 1


def test_empty_predictions_are_not_perfect():
    r = evaluate_events([], [(1, 3)])
    assert r['precision'] is None
    assert r['recall'] == 0
    assert r['f1'] == 0
    assert evaluate_events([], [])['f1'] is None


def test_adjacent_blink_ids_and_gaps_stay_separate():
    rows = [(0,-1),(1,0),(2,0),(3,1),(5,1),(6,-1)]
    text = '#start\n' + '\n'.join(':'.join(map(str,[i,b]+['X']*17)) for i,b in rows)
    spans, frames = tag_intervals(text)
    assert spans == [(1,2),(3,3),(5,5)]
    assert frames == [0,1,2,3,5,6]


@pytest.mark.parametrize('interval', [(-1, 3), (4, 2)])
def test_bad_interval(interval):
    with pytest.raises(ValueError):
        evaluate_events([interval], [])



def test_unknown_frames_are_not_negative_examples():
    from face_engine.evaluation import restrict_to_annotation
    assert restrict_to_annotation([(0,8),(10,15)], [2,3,4,6,7,8,9,10]) == [(2,4),(6,8),(10,10)]
    assert restrict_to_annotation([(0,1)], [2,3]) == []
