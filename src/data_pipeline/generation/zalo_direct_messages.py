"""Combined static direct-message catalog for all 60 Zalo lineages."""

from __future__ import annotations

from src.data_pipeline.generation.zalo_direct_messages_01_20 import (
    DIRECT_MESSAGE_TEMPLATES_01_20,
)
from src.data_pipeline.generation.zalo_direct_messages_21_40 import (
    DIRECT_MESSAGE_TEMPLATES_21_40,
)
from src.data_pipeline.generation.zalo_direct_messages_41_60 import (
    DIRECT_MESSAGE_TEMPLATES_41_60,
)


DIRECT_MESSAGE_TEMPLATES: dict[str, tuple[str, str, str, str, str]] = {
    **DIRECT_MESSAGE_TEMPLATES_01_20,
    **DIRECT_MESSAGE_TEMPLATES_21_40,
    **DIRECT_MESSAGE_TEMPLATES_41_60,
}
