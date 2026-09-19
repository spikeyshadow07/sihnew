import pytest
from ai_engine.detector import road_class_map
from training.prepare_starter import validate_label, split_records

def test_custom_classes_do_not_use_coco_indices():
    assert road_class_map({0:"truck",1:"car",2:"person",3:"traffic light"}) == {0:"truck",1:"car",2:"pedestrian"}

def test_original_coco_mapping_still_works():
    assert road_class_map(["person","bicycle","car","motorcycle","airplane","bus","train","truck"]) == {0:"pedestrian",1:"bicycle",2:"car",3:"motorcycle",5:"bus",7:"truck"}

@pytest.mark.parametrize("row", ["0 nan .5 .2 .2", "0 .5 .5 0 .2", "80 .5 .5 .2 .2", "0 .5"])
def test_invalid_training_labels_fail(row):
    with pytest.raises(ValueError):
        validate_label(row)

def test_valid_empty_and_road_labels():
    assert validate_label("") == []
    assert validate_label("7 .5 .5 .2 .2\n") == [7]

def test_split_disjoint_complete_and_reproducible():
    records = [(str(i),"",[0,1,2,3,5,7] if i < 6 else [],str(i)) for i in range(128)]
    first = split_records(records,42)
    assert first == split_records(records,42)
    assert [len(first[k]) for k in ("train","val","test")] == [90,19,19]
    combined = [r[0] for rows in first.values() for r in rows]
    assert len(set(combined)) == 128
    for rows in first.values():
        assert {c for r in rows for c in r[2]} == {0,1,2,3,5,7}
