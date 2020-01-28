from dataclasses import dataclass
from packaging.version import Version

@dataclass
class Package:
    version: Version

