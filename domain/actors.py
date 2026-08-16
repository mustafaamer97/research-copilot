"""Canonical actor types."""
from enum import Enum


class ActorType(str, Enum):
    RESEARCHER = "RESEARCHER"
    AI = "AI"
    SYSTEM = "SYSTEM"
