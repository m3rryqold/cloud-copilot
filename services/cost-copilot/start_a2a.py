"""
Cost Copilot A2A Server
Exposes the Cost Copilot agent via A2A protocol
"""

import sys
from pathlib import Path

# Add agents directory to path
agents_dir = Path(__file__).parent / "src" / "agents"
sys.path.insert(0, str(agents_dir))

from cost_copilot.agent import root_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Create A2A app
a2a_app = to_a2a(root_agent, port=8001)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Cost Copilot A2A Server on http://0.0.0.0:8001")
    print("📋 Agent card available at: http://0.0.0.0:8001/.well-known/agent-card.json")
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
