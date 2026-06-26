from pathlib import Path

from devils_receipt.verify import main

FIX = Path(__file__).resolve().parents[1] / "evals" / "fixtures"
EV = str(FIX / "evidence_sample.json")
THESIS = "Brazil's safrinha corn is fine this year"


def test_grounded_memo_passes():
    assert main(["--prose", str(FIX / "brief_good.md"), "--data", EV, "--thesis", THESIS]) == 0


def test_fabricated_memo_fails():
    assert main(["--prose", str(FIX / "brief_fabricated.md"), "--data", EV, "--thesis", THESIS]) == 1


def test_empty_evidence_memo_cites_nothing_passes():
    # the no-bear-case memo quotes nothing, so it's vacuously grounded
    assert main(["--prose", str(FIX / "brief_null.md"),
                 "--data", str(FIX / "evidence_empty.json"), "--thesis", THESIS]) == 0
