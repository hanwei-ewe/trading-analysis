from collections import OrderedDict
from typing import Generic, Iterator, TypeVar


T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, name):
        self.name = name
        self._items = OrderedDict()

    def register(self, item=None):
        if item is None:
            return self.register
        if isinstance(item, type):
            item = item()
        key = getattr(item, "id", None)
        if not key:
            raise ValueError(f"{self.name} plugin needs an id")
        if key in self._items:
            raise ValueError(f"duplicate {self.name} plugin: {key}")
        self._items[key] = item
        return item

    def get(self, key):
        try:
            return self._items[key]
        except KeyError as err:
            raise KeyError(f"unknown {self.name} plugin: {key}") from err

    def maybe_get(self, key):
        return self._items.get(key)

    def ids(self):
        return tuple(self._items)

    def all(self):
        return tuple(self._items.values())

    def __contains__(self, key):
        return key in self._items

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __len__(self):
        return len(self._items)
