from dataclasses import dataclass
from typing import Optional

# Layout constants
ACTOR_WIDTH = 120
ACTOR_HEIGHT = 40
ACTOR_TOP_Y = 20
INTERACTION_START_Y = 120
INTERACTION_V_GAP = 60
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700

# Color fallbacks
LABEL_COLOR = "#222222"
INDEX_COLOR = "#666666"
ACTOR_TEXT_COLOR = "#111111"
PREVIEW_LINE_COLOR = "#999999"

@dataclass
class Actor:
    id: int
    name: str
    x: int  # center x
    y: int = ACTOR_TOP_Y
    rect_id: Optional[int] = None
    text_id: Optional[int] = None

@dataclass
class Interaction:
    source_id: int
    target_id: int
    label: str = ""
    style: str = "solid"  # 'solid' or 'dashed'

