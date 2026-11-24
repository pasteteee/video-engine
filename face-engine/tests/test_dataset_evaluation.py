import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('dataset_evaluation', Path(__file__).parents[1] / 'examples/evaluate_blink_dataset.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_aggregate_is_micro_and_requires_all_reports(tmp_path):
    for name, predicted in [('a', True), ('b', False)]:
        folder = tmp_path / name
        folder.mkdir()
        (folder/'clip.tag').write_text(':'.join(['0','0']+['X']*17))
        events = [{'type':'blink','frame_start':0,'frame_end':0}] if predicted else []
        (folder/'report.json').write_text(json.dumps({'meta':{'frames':1,'fps':30},'events':events}))
    result = module.evaluate_dataset(tmp_path)
    assert result['n_clips'] == 2
    assert (result['tp'],result['fp'],result['fn']) == (1,0,1)
    assert result['precision'] == 1
    assert result['recall'] == .5
    assert result['f1'] == pytest.approx(2/3)
    (tmp_path/'b/report.json').unlink()
    with pytest.raises(FileNotFoundError):
        module.evaluate_dataset(tmp_path)
