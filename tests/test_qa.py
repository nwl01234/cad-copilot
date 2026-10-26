import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import qa


def test_consistency_of_real_dataset(tmp_path):
    from core.finetune import build_dataset
    ds = build_dataset(40, str(tmp_path / "ds.jsonl"))
    r = qa.dataset_consistency(ds)
    assert r["valid"] is True and r["conflicts"] == 0


def test_honeypots_pass():
    r = qa.honeypot_check()
    assert r["pass_rate"] == 1.0


def test_eval_trained_model(tmp_path):
    r = qa.eval_trained_model(epochs=2)
    assert r["honeypots"]["pass_rate"] == 1.0
    assert Path("model/intent_model.json").exists()
