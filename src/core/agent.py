"""
Base agent implementation for the collaboration system.
"""
from typing import Dict, Any, Optional
from .messaging import MessageClient

class AgentBase:
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, message_client: Optional[MessageClient] = None):
        self.agent_id = agent_id
        self.message_client = message_client or MessageClient(agent_id)
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await self.message_client.connect()
        
    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.message_client.disconnect()
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message."""
        raise NotImplementedError("Subclasses must implement process_message") 