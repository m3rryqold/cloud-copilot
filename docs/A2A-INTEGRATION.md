# A2A Integration Guide

Agent-to-Agent (A2A) protocol enables K8s Copilot to communicate with Cost Copilot for cross-service cost analysis.

## Architecture

```
┌─────────────────────┐         A2A Protocol          ┌─────────────────────┐
│   K8s Copilot       │◄──────────────────────────────►│   Cost Copilot      │
│   (Port 8000)       │   HTTP + JSON Agent Cards     │   (Port 8001)       │
│                     │                                │                     │
│ - DiagnosticAgent   │                                │ - CostDiscovery     │
│ - InvestigatorAgent │                                │ - CostAnalysis      │
│ - RemediationAgent  │                                │                     │
│ - CostCopilotRemote ├────────────────────────────────┤                     │
└─────────────────────┘                                └─────────────────────┘
```

## How It Works

1. **ADK Web Auto-Exposure**: Both services automatically expose their agents via A2A:
   - Agent Card: `GET /.well-known/agent-card.json`
   - Execution: `POST /agent/execute`

2. **Remote Agent**: K8s Copilot creates a `RemoteAgent` pointing to Cost Copilot:
   ```python
   CostCopilotRemote = RemoteAgent(
       url="http://localhost:8001",  # or Cloud Run URL
       name="cost_copilot_remote",
       description="Remote Cost Copilot agent..."
   )
   ```

3. **Delegation**: K8s Copilot can delegate cost queries to Cost Copilot:
   ```
   User: "What's the cost of my production namespace?"

   K8s Copilot:
     1. Delegates to diagnostic_agent → get namespace info
     2. Delegates to cost_copilot_remote → analyze costs
     3. Synthesizes response with both K8s and cost data
   ```

## Local Development Setup

### Step 1: Start Cost Copilot (Port 8001)

```bash
cd services/cost-copilot
source venv/bin/activate
adk web src/agents --port 8001 --host 0.0.0.0
```

Verify it's running:
```bash
curl http://localhost:8001/.well-known/agent-card.json
```

### Step 2: Start K8s Copilot (Port 8000)

```bash
cd services/k8s-copilot
source venv/bin/activate

# Make sure COST_COPILOT_URL is set in .env
echo "COST_COPILOT_URL=http://localhost:8001" >> .env

adk web src/agents --port 8000 --host 0.0.0.0
```

### Step 3: Test A2A Integration

Visit http://localhost:8000 and try these queries:

#### Cost-Only Queries:
- "Show me my GCP costs"
- "Find idle resources in my project"
- "What are my cost optimization opportunities?"

#### Cross-Service Queries (K8s + Cost):
- "What's the cost of my production namespace?"
- "Find expensive idle resources in my cluster"
- "Show me cost breakdown by namespace"
- "Which namespaces are most expensive?"

#### Expected Behavior:
- K8s Copilot should delegate to `cost_copilot_remote`
- You should see agent communication in the UI
- Response should combine K8s resource data with cost analysis

## Cloud Run Deployment

### Step 1: Deploy Both Services

```bash
cd cloudcopilot
gcloud builds submit --config cloudbuild.yaml
```

This deploys:
- `k8s-copilot` service
- `cost-copilot` service

### Step 2: Get Cost Copilot URL

```bash
gcloud run services describe cost-copilot --region europe-west1 --format 'value(status.url)'
# Output: https://cost-copilot-xxx-uc.a.run.app
```

### Step 3: Update K8s Copilot Environment

```bash
# Update environment variable in Cloud Run
gcloud run services update k8s-copilot \
  --region europe-west1 \
  --update-env-vars COST_COPILOT_URL=https://cost-copilot-xxx-uc.a.run.app
```

### Step 4: Configure Service-to-Service Auth (Optional)

For production, you may want to require authentication:

```bash
# Make cost-copilot require authentication
gcloud run services update cost-copilot \
  --region europe-west1 \
  --no-allow-unauthenticated

# Grant k8s-copilot permission to invoke cost-copilot
gcloud run services add-iam-policy-binding cost-copilot \
  --region europe-west1 \
  --member="serviceAccount:k8s-copilot-sa@hunt3r.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Troubleshooting

### Cost Copilot Not Connecting

**Symptom**: K8s Copilot logs show:
```
Warning: Could not connect to Cost Copilot at http://localhost:8001
Cost analysis features will be unavailable.
```

**Solutions**:
1. Verify Cost Copilot is running: `curl http://localhost:8001/.well-known/agent-card.json`
2. Check `COST_COPILOT_URL` in k8s-copilot/.env
3. Ensure both services use correct ports (8000 vs 8001)

### Agent Card 404

**Symptom**: `404 Not Found` when accessing agent card

**Solution**: ADK web automatically exposes this endpoint. Check:
- Service is running with `adk web src/agents`
- Agent has `root_agent` variable defined
- No errors in service startup logs

### Cross-Service Queries Not Working

**Symptom**: K8s Copilot doesn't delegate to Cost Copilot

**Debug**:
1. Check K8s Copilot startup logs for RemoteAgent connection
2. Verify `has_cost_copilot` is `True` in the code
3. Test Cost Copilot independently first
4. Check if K8s Copilot instructions mention `cost_copilot_remote`

## Example Queries & Expected Flow

### Query: "What's the cost of my production namespace?"

**Expected Flow**:
```
1. User → K8s Copilot (port 8000)
   Query: "What's the cost of my production namespace?"

2. K8s Copilot → diagnostic_agent (local)
   Request: "Get info about production namespace"
   Response: "production namespace has 15 pods, 32GB memory, 8 CPUs"

3. K8s Copilot → cost_copilot_remote (port 8001, A2A)
   Request: "Analyze costs for project hunt3r"
   HTTP: POST http://localhost:8001/agent/execute
   Response: "Idle resources found, cost breakdown..."

4. K8s Copilot → User
   Synthesized: "The production namespace uses 32GB/8CPU.
                 Based on GCP cost analysis, estimated cost is $X/month.
                 Recommendations: ..."
```

## Benefits of A2A Integration

✅ **Separation of Concerns**: K8s expertise separate from cost analysis
✅ **Independent Scaling**: Scale services based on different load patterns
✅ **Modularity**: Add/remove cost analysis without changing K8s service
✅ **Service Reusability**: Cost Copilot can serve multiple clients
✅ **Development Flexibility**: Teams can work on services independently

## Next Steps

- [ ] Test A2A locally with both services running
- [ ] Deploy to Cloud Run and configure cross-service communication
- [ ] Implement namespace-specific cost estimation tool
- [ ] Add authentication for production deployment
- [ ] Create Unified Dashboard that discovers both services via A2A
