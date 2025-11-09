# CloudCopilot - Development Context

This document provides context for AI assistants (like Claude) working on the CloudCopilot project.

## Project Overview

CloudCopilot is a multi-agent cloud management platform built with Google's Agent Development Kit (ADK). It consists of multiple specialized agent services that communicate via ADK's A2A (Agent-to-Agent) protocol.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudCopilot Platform                     │
│                       (Monorepo)                             │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌─────▼──────┐   ┌────▼─────────┐
   │ K8s     │ A2A  │ Cost       │   │ Unified      │
   │ Copilot │◄────►│ Copilot    │   │ Dashboard    │
   │ Service │      │ Service    │   │ (Planned)    │
   └─────────┘      └────────────┘   └──────────────┘
        │                 │
        │                 │
   ┌────▼────┐      ┌─────▼──────┐
   │   GKE   │      │ GCP Billing│
   │ Cluster │      │ & Assets   │
   └─────────┘      └────────────┘
```

## Services

### 1. K8s Copilot (`services/k8s-copilot/`)

**Status**: ✅ Production Ready
**Purpose**: Kubernetes cluster troubleshooting and management with cost analysis
**Port**: 8000 (local dev)

**Agent Architecture**:
- **Root Agent**: `KubernetesCopilot` (orchestrator)
- **Sub-Agents**:
  1. `DiagnosticAgent` - Cluster health, resource monitoring
     - 9 tools (get_cluster_info, list_namespaces, get_namespace_resources, get_cluster_resources, etc.)
  2. `InvestigatorAgent` - Root cause analysis
     - 3 tools (analyze_pod_logs, get_pod_description, check_deployment_history)
  3. `RemediationAdvisorAgent` - Fix suggestions
     - 3 tools (remediation strategies, kubectl commands, YAML patches)
  4. `CostCopilotRemote` - Cost analysis (via A2A)
     - Remote agent connected to Cost Copilot service

**Key Features**:
- Multi-agent troubleshooting workflow (Diagnose → Investigate → Remediate)
- Integrated cost analysis for namespaces
- A2A integration with Cost Copilot for cost queries
- Resource allocation tracking tools

**Files**:
- `src/agents/kubernetes_copilot/agent.py` - Root orchestrator
- `src/agents/diagnostic_agent/` - Cluster diagnostics
- `src/agents/investigator_agent/` - Log analysis
- `src/agents/remediation_advisor_agent/` - Fix suggestions

### 2. Cost Copilot (`services/cost-copilot/`)

**Status**: ✅ Production Ready
**Purpose**: GCP cost analysis and Kubernetes cost estimation
**Port**: 8001 (local dev - A2A server)

**Agent Architecture**:
- **Root Agent**: `CostCopilot` (orchestrator)
- **Sub-Agents**:
  1. `CostDiscoveryAgent` - Find idle/wasted GCP resources
     - 5 tools (find_idle_vms, find_unattached_disks, find_unused_ips, etc.)
  2. `CostAnalysisAgent` - Cost optimization and K8s cost estimation
     - 9 tools (6 GCP tools + 3 K8s cost tools)

**K8s Cost Tools** (NEW):
- `estimate_namespace_cost()` - Estimates namespace cost from resource requests
- `estimate_cluster_cost()` - Estimates total cluster cost
- `compare_namespace_costs()` - Compares costs across multiple namespaces

**Pricing**: Uses GKE Autopilot pricing ($0.042588/core/hour, $0.005722/GB/hour)

**A2A Exposure**:
- Exposes agent card at: `http://localhost:8001/.well-known/agent-card.json`
- Started via: `python start_a2a.py`
- K8s Copilot consumes this via `RemoteA2aAgent`

**Files**:
- `src/agents/cost_copilot/agent.py` - Root orchestrator
- `src/agents/cost_discovery_agent/` - Idle resource detection
- `src/agents/cost_analysis_agent/` - Cost optimization
- `src/agents/cost_analysis_agent/k8s_cost_tools.py` - K8s cost estimation
- `start_a2a.py` - A2A server script

### 3. Unified Dashboard (`services/unified-dashboard/`)

**Status**: ✅ Production Ready
**Purpose**: Central management UI for agent discovery and orchestration
**Port**: 3000 (local dev)
**Tech Stack**: TanStack Start, React, TypeScript, Tailwind CSS, shadcn/ui

**Features**:
- Agent discovery and status monitoring
- Static configuration-based agent display
- Agent detail pages with architecture flow diagrams
- Responsive design with modern UI
- Environment-configurable agent URLs
- Custom branding (Cloud AI Copilots logo)

**Architecture**:
- Static agent configuration (no dynamic discovery)
- Instant page loads (no network calls for discovery)
- Agent cards display features, descriptions, and links
- Direct links to agent web UIs
- Detailed agent pages with features and architecture flows

**Files**:
- `src/config/agents.ts` - Static agent configuration
- `src/routes/index.tsx` - Homepage with agent cards
- `src/routes/agents.$id.tsx` - Agent detail pages
- `src/components/AgentCard.tsx` - (deprecated, inline now)
- `src/types/agent.ts` - (deprecated, moved to config)
- `public/logo.svg` - Custom cloud + AI logo
- `public/favicon.svg` - Custom favicon

**Environment Variables** (`.env.local`):
```bash
VITE_K8S_COPILOT_URL=http://localhost:8000  # or https://k8s.agents.hunt3r.dev
VITE_COST_COPILOT_URL=http://localhost:8001  # or https://cost.agents.hunt3r.dev
```

**Development**:
```bash
cd services/unified-dashboard
npm install
npm run dev  # Starts on port 3000
```

## A2A Integration

The K8s Copilot and Cost Copilot communicate via ADK's A2A (Agent-to-Agent) protocol:

**Setup**:
1. Cost Copilot exposes itself via A2A:
   ```python
   # start_a2a.py
   from google.adk.a2a.utils.agent_to_a2a import to_a2a
   a2a_app = to_a2a(root_agent, port=8001)
   ```

2. K8s Copilot consumes Cost Copilot:
   ```python
   # k8s-copilot/src/agents/kubernetes_copilot/agent.py
   from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

   CostCopilotRemote = RemoteA2aAgent(
       name="cost_copilot",
       description="Remote GCP cost optimization agent...",
       agent_card="http://localhost:8001/.well-known/agent-card.json"
   )
   ```

**Workflow** (Namespace Cost Query):
1. User asks K8s Copilot: "What's the cost of test-scenarios namespace?"
2. K8s Copilot delegates to DiagnosticAgent
3. DiagnosticAgent calls `get_namespace_resources("test-scenarios")`
4. K8s Copilot transfers to Cost Copilot with resource data
5. Cost Copilot calls `estimate_namespace_cost()` with the data
6. Returns cost breakdown to user

**Current Status**:
- ✅ Namespace cost queries work end-to-end
- ⚠️  Cluster/comparison cost queries need LLM to follow multi-step workflow (partially working)

## Development Setup

### Local Development:

**K8s Copilot**:
```bash
cd services/k8s-copilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your-key" > .env
adk web src/agents --port 8000 --host 0.0.0.0
```

**Cost Copilot (A2A Server)**:
```bash
cd services/cost-copilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your-key" > .env
python start_a2a.py
```

### Key Dependencies:
- `google-adk[a2a]>=0.1.0` - Google Agent Development Kit with A2A support
- `kubernetes>=28.1.0` - K8s Python client
- `google-cloud-*` libraries - GCP service clients

## Known Issues & Future Work

### Cost Analysis UX Issues:
1. **Verbose output**: K8s Copilot shows "For context:" messages during delegation
   - **Fix**: Added communication style instruction to reduce verbosity

2. **Cluster/comparison queries**: LLM doesn't always follow multi-step workflow
   - **Issue**: K8s Copilot should gather resource data FIRST, then delegate to Cost Copilot
   - **Status**: Namespace queries work, cluster/comparison queries need improvement

3. **Agent card caching**: Changes to tools require restarting A2A server
   - **Workaround**: Always restart Cost Copilot A2A server after tool changes

### Future Enhancements:
1. Add direct K8s Metrics API integration for actual usage data (vs. requests)
2. Implement cost alerting and budget tracking
3. Add multi-cluster cost comparison
4. Build Unified Dashboard for cross-agent orchestration
5. Add cost optimization automation (not just recommendations)

## File Structure

```
cloudcopilot/
├── services/
│   ├── k8s-copilot/
│   │   ├── src/agents/
│   │   │   ├── kubernetes_copilot/agent.py    # Root orchestrator
│   │   │   ├── diagnostic_agent/
│   │   │   │   ├── agent.py
│   │   │   │   └── tools.py                   # 9 tools including get_namespace_resources
│   │   │   ├── investigator_agent/
│   │   │   └── remediation_advisor_agent/
│   │   ├── requirements.txt
│   │   └── .env
│   │
│   ├── cost-copilot/
│   │   ├── src/agents/
│   │   │   ├── cost_copilot/agent.py          # Root orchestrator
│   │   │   ├── cost_discovery_agent/
│   │   │   └── cost_analysis_agent/
│   │   │       ├── agent.py
│   │   │       ├── tools.py                   # 6 GCP cost tools
│   │   │       └── k8s_cost_tools.py          # 3 K8s cost tools
│   │   ├── start_a2a.py                       # A2A server
│   │   ├── requirements.txt
│   │   └── .env
│   │
│   └── unified-dashboard/
│       ├── src/
│       │   ├── routes/
│       │   │   ├── __root.tsx                 # Root layout
│       │   │   ├── index.tsx                  # Homepage
│       │   │   └── agents.$id.tsx             # Agent detail pages
│       │   ├── config/agents.ts               # Static agent config
│       │   └── styles.css
│       ├── public/
│       │   ├── logo.svg                       # Custom logo
│       │   └── favicon.svg                    # Custom favicon
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       └── .env.example
│
├── docs/
│   └── A2A-INTEGRATION.md
├── scripts/
│   └── setup-all.sh
├── cloudbuild.yaml
├── README.md
├── CLAUDE.md (this file)
└── .gitignore
```

## Testing

### Test Namespace Cost Query:
```
User: "Tell me the cost of test-scenarios namespace"

Expected Flow:
1. K8s Copilot → DiagnosticAgent.get_namespace_resources("test-scenarios")
2. Returns: 2.0 cores, 8.0 GB memory, 0 GB storage, 4 pods
3. K8s Copilot → Cost Copilot (via A2A)
4. Cost Copilot → CostAnalysisAgent.estimate_namespace_cost(...)
5. Returns: ~$69.92/month cost breakdown
```

### Verify A2A Connection:
```bash
# Check Cost Copilot agent card
curl http://localhost:8001/.well-known/agent-card.json | python3 -m json.tool | grep "estimate_namespace_cost"

# Should see:
# "name": "cost_analysis_agent: estimate_namespace_cost"
```

## Common Commands

```bash
# Clean temporary files
find . -type f \( -name "*.log" -o -name "*.pyc" \) -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Check running services
ps aux | grep "adk web\|start_a2a"

# Kill all agent instances
pkill -f "adk web"
pkill -f "start_a2a"

# Git status (ignore venv, logs, etc)
git status --ignored
```

## Deployment

**Cloud Run** (via Cloud Build):
```bash
# Deploy all services
gcloud builds submit --config cloudbuild.yaml --project=hunt3r

# Services deployed:
# - k8s-copilot: https://k8s-copilot-xxx.run.app
# - cost-copilot: https://cost-copilot-xxx.run.app
```

## Environment Variables

**K8s Copilot** (`.env`):
```bash
GOOGLE_API_KEY=your-gemini-api-key
COST_COPILOT_URL=http://localhost:8001  # or Cloud Run URL in production
```

**Cost Copilot** (`.env`):
```bash
GOOGLE_API_KEY=your-gemini-api-key
GCP_PROJECT_ID=hunt3r
```

## Key Learnings

1. **A2A requires explicit agent card refresh**: Restart A2A server after tool changes
2. **Type annotations matter**: Use `float = 0.0` not `float = 0` for tool parameters
3. **LLM workflow instructions**: Hard to enforce multi-step workflows via instructions alone
4. **Agent orchestration**: Root agents work best when sub-agents are well-defined
5. **Cost estimation**: Resource requests != actual usage; need metrics for accuracy

---

**Last Updated**: November 8, 2024
**Author**: Built with Claude Code
**Project**: CloudCopilot - Multi-Agent Cloud Management Platform
