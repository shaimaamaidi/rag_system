from dataclasses import dataclass


@dataclass
class SectionHeading:
    content:     str
    page_number: int
    y_position:  float
    x_position:  float