"""
Tests for Message Bus Communication
"""

import pytest
from src.communication.message_bus import MessageBus, MessageProtocol


@pytest.fixture
def message_bus():
    """Create message bus instance."""
    return MessageBus()


@pytest.mark.unit
class TestMessageBus:
    """Test message bus functionality."""
    
    def test_send_receive(self, message_bus):
        """Test basic send and receive."""
        message = {"data": "test message"}
        
        result = message_bus.send("agent1", "agent2", message)
        assert result is True
        
        messages = message_bus.receive("agent2")
        assert len(messages) == 1
        assert messages[0]["data"] == "test message"
        assert messages[0]["_sender"] == "agent1"
    
    def test_receive_clears_mailbox(self, message_bus):
        """Receive should clear mailbox."""
        message_bus.send("agent1", "agent2", {"msg": 1})
        
        # First receive gets messages
        messages1 = message_bus.receive("agent2")
        assert len(messages1) == 1
        
        # Second receive gets empty list
        messages2 = message_bus.receive("agent2")
        assert len(messages2) == 0
    
    def test_broadcast(self, message_bus):
        """Test broadcasting to multiple agents."""
        recipients = ["agent2", "agent3", "agent4"]
        message = {"broadcast": "data"}
        
        delivered = message_bus.broadcast("agent1", recipients, message)
        assert delivered == 3
        
        # Each recipient should have the message
        for recipient in recipients:
            messages = message_bus.receive(recipient)
            assert len(messages) == 1
            assert messages[0]["broadcast"] == "data"
    
    def test_disabled_link(self, message_bus):
        """Test communication failure simulation."""
        message_bus.disable_link("agent1", "agent2")
        
        result = message_bus.send("agent1", "agent2", {"msg": "blocked"})
        assert result is False
        
        messages = message_bus.receive("agent2")
        assert len(messages) == 0
        
        # Re-enable should work
        message_bus.enable_link("agent1", "agent2")
        result = message_bus.send("agent1", "agent2", {"msg": "unblocked"})
        assert result is True
    
    def test_disable_agent_communication(self, message_bus):
        """Test isolating an agent."""
        neighbors = ["agent2", "agent3"]
        
        message_bus.disable_agent_communication("agent1", neighbors)
        
        # Cannot send to neighbors
        assert message_bus.send("agent1", "agent2", {}) is False
        assert message_bus.send("agent1", "agent3", {}) is False
        
        # Neighbors cannot send to agent
        assert message_bus.send("agent2", "agent1", {}) is False
    
    def test_has_messages(self, message_bus):
        """Test checking for pending messages."""
        assert message_bus.has_messages("agent1") is False
        
        message_bus.send("agent2", "agent1", {"msg": "hello"})
        assert message_bus.has_messages("agent1") is True
        
        message_bus.receive("agent1")
        assert message_bus.has_messages("agent1") is False
    
    def test_peek(self, message_bus):
        """Test peeking without removing messages."""
        message_bus.send("agent1", "agent2", {"msg": 1})
        
        # Peek should not remove
        peeked = message_bus.peek("agent2")
        assert len(peeked) == 1
        
        # Messages still there
        assert message_bus.has_messages("agent2") is True
        
        # Receive should remove
        messages = message_bus.receive("agent2")
        assert len(messages) == 1
        assert message_bus.has_messages("agent2") is False
    
    def test_statistics(self, message_bus):
        """Test message statistics."""
        message_bus.send("agent1", "agent2", {"msg": 1})
        message_bus.send("agent1", "agent3", {"msg": 2})
        
        message_bus.disable_link("agent1", "agent4")
        message_bus.send("agent1", "agent4", {"msg": 3})  # Blocked
        
        stats = message_bus.get_statistics()
        
        assert stats['messages_sent'] == 3
        assert stats['messages_delivered'] == 2
        assert stats['messages_blocked'] == 1
        assert stats['disabled_links'] == 1


@pytest.mark.unit
class TestMessageProtocol:
    """Test standardized message formats."""
    
    def test_traffic_state_message(self):
        """Test traffic state message format."""
        msg = MessageProtocol.traffic_state_message(
            sender="I4",
            timestamp=100,
            phase="ns_green",
            queue_ns=10,
            queue_ew=5,
            pressure=150.0
        )
        
        assert msg['type'] == 'traffic_state'
        assert msg['sender'] == "I4"
        assert msg['timestamp'] == 100
        assert msg['phase'] == "ns_green"
        assert msg['queue']['ns'] == 10
        assert msg['queue']['ew'] == 5
        assert msg['pressure'] == 150.0
    
    def test_incident_notification(self):
        """Test incident notification format."""
        msg = MessageProtocol.incident_notification(
            sender="I4",
            timestamp=50,
            location="Road I4->I5",
            blocked_road=("I4", "I5"),
            severity="high"
        )
        
        assert msg['type'] == 'incident'
        assert msg['sender'] == "I4"
        assert msg['blocked_road'] == ("I4", "I5")
        assert msg['severity'] == "high"
    
    def test_coordination_request(self):
        """Test coordination request format."""
        msg = MessageProtocol.coordination_request(
            sender="I4",
            timestamp=75,
            requested_phase="ns_green",
            priority=8
        )
        
        assert msg['type'] == 'coordination_request'
        assert msg['sender'] == "I4"
        assert msg['requested_phase'] == "ns_green"
        assert msg['priority'] == 8


@pytest.mark.integration
def test_multi_agent_communication(message_bus):
    """Test realistic multi-agent communication pattern."""
    # Simulate 3 intersections communicating
    intersections = ["I3", "I4", "I5"]
    
    # I4 broadcasts state to neighbors
    state_msg = MessageProtocol.traffic_state_message(
        sender="I4",
        timestamp=100,
        phase="ns_green",
        queue_ns=8,
        queue_ew=3,
        pressure=160.0
    )
    
    delivered = message_bus.broadcast("I4", ["I3", "I5"], state_msg)
    assert delivered == 2
    
    # Neighbors receive and respond
    for neighbor in ["I3", "I5"]:
        messages = message_bus.receive(neighbor)
        assert len(messages) == 1
        assert messages[0]['sender'] == "I4"
        
        # Send acknowledgment
        ack_msg = {"type": "ack", "received_from": "I4"}
        message_bus.send(neighbor, "I4", ack_msg)
    
    # I4 receives acknowledgments
    acks = message_bus.receive("I4")
    assert len(acks) == 2
    assert all(msg['type'] == "ack" for msg in acks)
