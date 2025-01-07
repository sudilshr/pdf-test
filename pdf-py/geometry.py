from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import uuid
import json


@dataclass
class BoundingPoly:
    """
    Represents a bounding polygon with vertex coordinates.

    Provides methods for creating bounding polygons from different input types.
    """
    vertices: List[Dict[str, float]]

    def __post_init__(self):
        """
        Validate vertices after initialization.
        Ensures each vertex contains 'x' and 'y' coordinates.
        """
        for vertex in self.vertices:
            if not all(key in vertex for key in ['x', 'y']):
                raise ValueError(
                    "Each vertex must contain 'x' and 'y' coordinates")

    @classmethod
    def from_bbox(cls, bbox: tuple) -> 'BoundingPoly':
        """
        Create a bounding polygon from a bounding box tuple.

        :param bbox: Tuple of (x0, y0, x1, y1) coordinates
        :return: BoundingPoly instance
        :raises ValueError: If bbox does not contain exactly 4 coordinates
        """
        if len(bbox) != 4:
            raise ValueError(
                "Bounding box must contain 4 coordinates (x0, y0, x1, y1)")

        return cls([
            {"x": bbox[0], "y": bbox[1]},  # Bottom-left
            {"x": bbox[2], "y": bbox[1]},  # Bottom-right
            {"x": bbox[2], "y": bbox[3]},  # Top-right
            {"x": bbox[0], "y": bbox[3]}   # Top-left
        ])

    def to_dict(self) -> Dict[str, List[Dict[str, float]]]:
        """
        Convert BoundingPoly to a dictionary representation.

        :return: Dictionary with 'vertices' key
        """
        return {"vertices": self.vertices}


@dataclass
class Block:
    """
    Represents a text block with type, ID, description, and bounding box.

    Provides flexible initialization and conversion to dictionary.
    """
    block_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    bounding_poly: Optional[BoundingPoly] = None
    relationships: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """
        Perform additional validation after initialization.
        """
        if not self.block_type:
            raise ValueError("Block type cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Block to a dictionary representation.

        :return: Dictionary with block details
        """
        return {
            "blockType": self.block_type,
            "id": self.id,
            "description": self.description,
            "boundingPoly": self.bounding_poly.to_dict() if self.bounding_poly else None,
            "relationships": self.relationships
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """
        Create a Block instance from a dictionary.

        :param data: Dictionary containing block details
        :return: Block instance
        """
        bounding_poly = BoundingPoly(data.get('boundingPoly', {}).get(
            'vertices', [])) if data.get('boundingPoly') else None

        return cls(
            block_type=data.get('blockType', ''),
            id=data.get('id', str(uuid.uuid4())),
            description=data.get('description', ''),
            bounding_poly=bounding_poly,
            relationships=data.get('relationships', [])
        )
