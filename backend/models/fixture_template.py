from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field

class Mapping(BaseModel):
    """Dictionary for enum or labeled u8 values."""
    pass # Mappings are dynamic Dict[str, Union[int, str]] in the template

class MetaChannel(BaseModel):
    label: str
    kind: Literal["u8", "u16", "rgb", "enum"]
    channel: Optional[str] = None
    channels: Optional[List[str]] = None
    mapping: Optional[str] = None
    step: Optional[bool] = False
    arm: Optional[int] = None
    hidden: Optional[bool] = False

class FixtureTemplate(BaseModel):
    id: str
    type: str
    channels: Dict[str, int]
    effects: List[str] = []
    meta_channels: Dict[str, MetaChannel]
    mappings: Dict[str, Dict[str, Union[int, str]]] = {}
