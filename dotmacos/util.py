from functools import lru_cache
import os
from typing import FrozenSet

from .types import Section


@lru_cache(maxsize = 1)
def accessible_section_names() -> FrozenSet[str]:
    sections = ([Section.system]
                if os.geteuid() == 0 else
                [Section.user, Section.local])
    return frozenset(section.name for section in sections)
