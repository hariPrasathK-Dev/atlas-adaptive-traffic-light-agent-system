"""
Communication module for ATLAS
Message passing between traffic signal agents
"""

from .message_bus import MessageBus, MessageProtocol

__all__ = [
    'MessageBus',
    'MessageProtocol'
]
