import pytest
from pydantic import ValidationError

from conftest import make_entry
from designlib.core.schema import new_id, slugify


def test_tags_are_cleaned():
    entry = make_entry(tags=[" Card ", "card", "Hero", ""])
    assert entry.tags == ["card", "hero"]


def test_code_requires_open_license():
    with pytest.raises(ValidationError, match="open licenses"):
        make_entry(code="<div></div>", license="link-only")
    assert make_entry(code="<div></div>", license="MIT").code


def test_rating_must_be_1_to_5():
    with pytest.raises(ValidationError):
        make_entry(my_rating=9)


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        make_entry(type="poster")


def test_local_image_must_stay_in_assets():
    assert make_entry(local_image="assets\\mine\\a.png").local_image == "assets/mine/a.png"
    with pytest.raises(ValidationError):
        make_entry(local_image="assets/mine/../../secret.txt")
    with pytest.raises(ValidationError):
        make_entry(local_image="C:/Windows/a.png")


def test_ids_are_safe_slugs():
    assert slugify("Glass Pricing Card!") == "glass-pricing-card"
    entry_id = new_id("Glass Pricing Card!")
    assert entry_id.startswith("glass-pricing-card-")
    with pytest.raises(ValidationError):
        make_entry(id="../evil")
