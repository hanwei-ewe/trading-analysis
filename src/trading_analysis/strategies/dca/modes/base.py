from abc import ABC


class Mode(ABC):
    id: str = ""
    label: str = ""
    description: str = ""
