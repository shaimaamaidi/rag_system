"""Model for section heading metadata extracted from documents."""

from dataclasses import dataclass


@dataclass
class SectionHeading:
    """Section heading coordinates and content.

    :ivar content: Heading text.
    :ivar page_number: Page number where the heading appears.
    :ivar y_position: Vertical position of the heading.
    :ivar x_position: Horizontal position of the heading.
    """
    content:     str
    page_number: int
    y_position:  float
    x_position:  float