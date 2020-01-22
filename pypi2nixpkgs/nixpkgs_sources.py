from typing import Sequence
from dataclasses import dataclass
from packaging.utils import canonicalize_name

@dataclass
class PyDerivation:
    attr: str
    version: str


class NixpkgsData:
    def __init__(self, data):
        self.__data = data

    def from_pypi_name(self, name: str) -> Sequence[PyDerivation]:
        return [
            PyDerivation(attr=data['attr'], version=data['version'])
            for data in self.__data[canonicalize_name(name)]
        ]
