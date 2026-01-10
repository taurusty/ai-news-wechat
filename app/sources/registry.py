from typing import Dict, Type

from app.sources.base import BaseSource
from app.sources.jiqizhixin import JiqizhixinSource
from app.sources.aiera import AieraSource
from app.sources.venturebeat import VentureBeatSource
from app.sources.engadget import EngadgetSource
from app.sources.cnet import CnetSource
from app.sources.techcrunch_ai import TechCrunchAISource


SOURCE_REGISTRY: Dict[str, Type[BaseSource]] = {
    "jiqizhixin": JiqizhixinSource,
    "aiera": AieraSource,
    "venturebeat": VentureBeatSource,
    "engadget": EngadgetSource,
    "cnet": CnetSource,
    "techcrunch_ai": TechCrunchAISource,
}


def create_source(name: str, **kwargs) -> BaseSource:
    if name not in SOURCE_REGISTRY:
        raise ValueError(f"Unknown source: {name}")
    return SOURCE_REGISTRY[name](**kwargs)
