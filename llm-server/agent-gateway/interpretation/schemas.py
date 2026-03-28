from typing import Literal, Optional

from pydantic import BaseModel


class SectionTimingExtraction(BaseModel):
    intent: Literal["none", "section_timing"]
    section_name: Optional[str] = None
    section_occurrence: int = 1
    boundary: Literal["start", "end"] = "start"
