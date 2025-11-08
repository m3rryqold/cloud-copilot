#!/bin/bash
# CloudCopilot - Local Development Script
# Run services locally for development

set -e

SERVICE="${1:-k8s-copilot}"

echo "🔧 Starting CloudCopilot service: $SERVICE"
echo "=========================================="
echo ""

case $SERVICE in
  k8s-copilot)
    cd services/k8s-copilot

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3 -m venv venv
    fi

    # Activate and install dependencies
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -q -r requirements.txt

    # Check for .env file
    if [ ! -f ".env" ]; then
      echo "⚠️  Warning: .env file not found"
      echo "Create .env with GOOGLE_API_KEY=your-key"
      echo ""
    fi

    # Start ADK web server
    echo "Starting K8s Copilot on http://localhost:8000"
    adk web src/agents --port 8000 --host 0.0.0.0
    ;;

  cost-optimizer)
    cd services/cost-copilot

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3 -m venv venv
    fi

    # Activate and install dependencies
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -q -r requirements.txt

    # Check for .env file
    if [ ! -f ".env" ]; then
      echo "⚠️  Warning: .env file not found"
      echo "Create .env with GOOGLE_API_KEY=your-key and GCP_PROJECT_ID=your-project"
      echo ""
    fi

    # Start ADK web server
    echo "Starting Cost Copilot on http://localhost:8001"
    adk web src/agents --port 8001 --host 0.0.0.0
    ;;

  unified-dashboard)
    echo "❌ Unified Dashboard service not yet implemented"
    exit 1
    ;;

  *)
    echo "❌ Unknown service: $SERVICE"
    echo ""
    echo "Usage: $0 [service-name]"
    echo ""
    echo "Available services:"
    echo "  k8s-copilot        - Kubernetes troubleshooting agent"
    echo "  cost-optimizer     - GCP cost optimization agent (Cost Copilot)"
    echo "  unified-dashboard  - Unified agents UI (coming soon)"
    exit 1
    ;;
esac
