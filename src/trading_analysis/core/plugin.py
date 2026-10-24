from typing import Protocol, runtime_checkable


@runtime_checkable
class Plugin(Protocol):
    id: str
    label: str
    description: str
