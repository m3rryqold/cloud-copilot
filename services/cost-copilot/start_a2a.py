"""
Cost Copilot A2A Server
Exposes the Cost Copilot agent via A2A protocol
"""

import os
import sys
from pathlib import Path

# Add agents directory to path
agents_dir = Path(__file__).parent / "src" / "agents"
sys.path.insert(0, str(agents_dir))

from cost_copilot.agent import root_agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# Get port from environment or use default
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")
# Get public hostname and port for agent card (required for A2A invocations)
# In Cloud Run: PUBLIC_HOST is the full domain, PORT should be 443 for HTTPS
PUBLIC_HOST = os.getenv("PUBLIC_HOST", "localhost")
PUBLIC_PORT = int(os.getenv("PUBLIC_PORT", str(PORT)))  # Use listening port as default
PROTOCOL = os.getenv("PROTOCOL", "http")

# Create A2A app with correct host/port/protocol for agent card
a2a_app = to_a2a(root_agent, host=PUBLIC_HOST, port=PUBLIC_PORT, protocol=PROTOCOL)

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Cost Copilot A2A Server on http://{HOST}:{PORT}")
    print(f"📋 Agent card available at: http://{HOST}:{PORT}/.well-known/agent-card.json")
    uvicorn.run(a2a_app, host=HOST, port=PORT)
