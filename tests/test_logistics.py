from src.logistics_service import choose_image_action


def test_exception_keeps_original_proof_instead_of_resizing():
    assert choose_image_action("DAMAGED_PACKAGE") == "retain-original"
    assert choose_image_action(None) == "make-thumbnail"

