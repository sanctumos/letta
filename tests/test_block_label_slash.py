import pytest
from pydantic import ValidationError

from letta.schemas.block import CreateBlock


def test_create_block_rejects_slash_in_label():
    with pytest.raises(ValidationError):
        CreateBlock(label="songs/fourth_of_july", value="lyrics")


def test_create_block_accepts_plain_label():
    block = CreateBlock(label="persona", value="hello")
    assert block.label == "persona"
