"""
Message Bus for ATLAS
Facilitates communication between traffic signal agents
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


class MessageBus:
    """
    Message passing system for multi-agent communication.
    
    Enables traffic signal agents to share information with neighbors:
    - Queue lengths and pressure values
    - Signal phases and timing
    - Incident notifications
    
    Supports:
    - Point-to-point messaging
    - Broadcast to multiple recipients
    - Communication failure simulation
    """
    
    def __init__(self):
        """Initialize message bus."""
        # Message storage: {recipient_id: [messages]}
        self.mailboxes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Communication failures: set of (sender, receiver) tuples to block
        self.disabled_links: Set[Tuple[str, str]] = set()
        
        # Statistics
        self.messages_sent = 0
        self.messages_delivered = 0
        self.messages_blocked = 0
    
    def send(
        self,
        sender: str,
        recipient: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Send a message from one agent to another.
        
        Args:
            sender: Sender agent ID
            recipient: Recipient agent ID
            message: Message data dictionary
            
        Returns:
            True if message was delivered, False if blocked
        """
        self.messages_sent += 1
        
        # Check if link is disabled (communication failure)
        if (sender, recipient) in self.disabled_links:
            self.messages_blocked += 1
            return False
        
        # Add sender to message
        message['_sender'] = sender
        
        # Deliver to mailbox
        self.mailboxes[recipient].append(message)
        self.messages_delivered += 1
        
        return True
    
    def broadcast(
        self,
        sender: str,
        recipients: List[str],
        message: Dict[str, Any]
    ) -> int:
        """
        Broadcast a message to multiple recipients.
        
        Args:
            sender: Sender agent ID
            recipients: List of recipient agent IDs
            message: Message data dictionary
            
        Returns:
            Number of successful deliveries
        """
        delivered = 0
        
        for recipient in recipients:
            if self.send(sender, recipient, message.copy()):
                delivered += 1
        
        return delivered
    
    def receive(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all messages for an agent and clear mailbox.
        
        Args:
            agent_id: Agent ID to retrieve messages for
            
        Returns:
            List of messages (may be empty)
        """
        messages = self.mailboxes[agent_id]
        self.mailboxes[agent_id] = []
        return messages
    
    def peek(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        View messages without removing them from mailbox.
        
        Args:
            agent_id: Agent ID to peek at
            
        Returns:
            Copy of messages in mailbox
        """
        return self.mailboxes[agent_id].copy()
    
    def has_messages(self, agent_id: str) -> bool:
        """
        Check if agent has pending messages.
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            True if agent has messages, False otherwise
        """
        return len(self.mailboxes[agent_id]) > 0
    
    def disable_link(self, sender: str, recipient: str):
        """
        Disable communication link (simulate failure).
        
        Args:
            sender: Sender agent ID
            recipient: Recipient agent ID
        """
        self.disabled_links.add((sender, recipient))
    
    def enable_link(self, sender: str, recipient: str):
        """
        Re-enable communication link.
        
        Args:
            sender: Sender agent ID
            recipient: Recipient agent ID
        """
        self.disabled_links.discard((sender, recipient))
    
    def disable_agent_communication(self, agent_id: str, neighbors: List[str]):
        """
        Disable all communication for an agent.
        
        Args:
            agent_id: Agent to isolate
            neighbors: List of the agent's neighbors
        """
        for neighbor in neighbors:
            self.disable_link(agent_id, neighbor)
            self.disable_link(neighbor, agent_id)
    
    def enable_agent_communication(self, agent_id: str, neighbors: List[str]):
        """
        Re-enable all communication for an agent.
        
        Args:
            agent_id: Agent to reconnect
            neighbors: List of the agent's neighbors
        """
        for neighbor in neighbors:
            self.enable_link(agent_id, neighbor)
            self.enable_link(neighbor, agent_id)
    
    def clear_all(self):
        """Clear all mailboxes."""
        self.mailboxes.clear()
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get communication statistics.
        
        Returns:
            Dictionary with message counts
        """
        pending = sum(len(msgs) for msgs in self.mailboxes.values())
        
        return {
            'messages_sent': self.messages_sent,
            'messages_delivered': self.messages_delivered,
            'messages_blocked': self.messages_blocked,
            'messages_pending': pending,
            'disabled_links': len(self.disabled_links)
        }
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self.messages_sent = 0
        self.messages_delivered = 0
        self.messages_blocked = 0


class MessageProtocol:
    """
    Standardized message formats for traffic signal communication.
    """
    
    @staticmethod
    def traffic_state_message(
        sender: str,
        timestamp: int,
        phase: str,
        queue_ns: int,
        queue_ew: int,
        pressure: float,
        outgoing_flow: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Create a traffic state update message.
        
        Args:
            sender: Intersection ID
            timestamp: Current simulation step
            phase: Current signal phase
            queue_ns: North-South queue length
            queue_ew: East-West queue length
            pressure: Total traffic pressure
            outgoing_flow: Expected outgoing traffic by direction
            
        Returns:
            Formatted message dictionary
        """
        return {
            'type': 'traffic_state',
            'sender': sender,
            'timestamp': timestamp,
            'phase': phase,
            'queue': {
                'ns': queue_ns,
                'ew': queue_ew
            },
            'pressure': pressure,
            'outgoing_flow': outgoing_flow or {}
        }
    
    @staticmethod
    def incident_notification(
        sender: str,
        timestamp: int,
        location: str,
        blocked_road: Tuple[str, str],
        severity: str = "high"
    ) -> Dict[str, Any]:
        """
        Create an incident notification message.
        
        Args:
            sender: Reporting intersection
            timestamp: When incident detected
            location: Incident location description
            blocked_road: (source, destination) of blocked road
            severity: "low", "medium", or "high"
            
        Returns:
            Formatted message dictionary
        """
        return {
            'type': 'incident',
            'sender': sender,
            'timestamp': timestamp,
            'location': location,
            'blocked_road': blocked_road,
            'severity': severity
        }
    
    @staticmethod
    def coordination_request(
        sender: str,
        timestamp: int,
        requested_phase: str,
        priority: int = 1
    ) -> Dict[str, Any]:
        """
        Request phase coordination from neighbors.
        
        Args:
            sender: Requesting intersection
            timestamp: Request time
            requested_phase: Desired phase
            priority: Request priority (1-10)
            
        Returns:
            Formatted message dictionary
        """
        return {
            'type': 'coordination_request',
            'sender': sender,
            'timestamp': timestamp,
            'requested_phase': requested_phase,
            'priority': priority
        }
