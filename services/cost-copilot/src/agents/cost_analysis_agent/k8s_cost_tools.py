"""
Kubernetes Cost Estimation Tools
Estimates costs for K8s namespaces and workloads based on resource allocation
"""

from typing import Optional


# GKE Pricing (approximate, region-dependent)
# Based on us-central1 pricing as of 2024
GKE_PRICING = {
    "cpu_per_core_hour": 0.031611,  # Standard tier
    "memory_per_gb_hour": 0.004237,  # Standard tier
    "autopilot_cpu_per_core_hour": 0.042588,
    "autopilot_memory_per_gb_hour": 0.005722,
    "storage_per_gb_month": 0.04,  # PD-Standard
    "storage_ssd_per_gb_month": 0.17,  # PD-SSD
}


def estimate_namespace_cost(
    namespace: str,
    cpu_cores: float,
    memory_gb: float,
    storage_gb: float = 0.0,
    pod_count: int = 0,
    is_autopilot: bool = True,
    days: int = 30
) -> str:
    """
    Estimates the cost of a Kubernetes namespace based on resource allocation.

    Args:
        namespace: Name of the namespace
        cpu_cores: Total CPU cores allocated (sum of all pod requests)
        memory_gb: Total memory in GB allocated (sum of all pod requests)
        storage_gb: Total persistent storage in GB
        pod_count: Number of pods in the namespace
        is_autopilot: Whether cluster is GKE Autopilot (vs Standard)
        days: Number of days to estimate (default 30 for monthly)

    Returns:
        Cost estimation breakdown
    """
    hours = days * 24

    # Choose pricing based on cluster type
    if is_autopilot:
        cpu_price = GKE_PRICING["autopilot_cpu_per_core_hour"]
        memory_price = GKE_PRICING["autopilot_memory_per_gb_hour"]
        cluster_type = "GKE Autopilot"
    else:
        cpu_price = GKE_PRICING["cpu_per_core_hour"]
        memory_price = GKE_PRICING["memory_per_gb_hour"]
        cluster_type = "GKE Standard"

    # Calculate compute costs
    cpu_cost = cpu_cores * cpu_price * hours
    memory_cost = memory_gb * memory_price * hours
    storage_cost = storage_gb * GKE_PRICING["storage_per_gb_month"] * (days / 30)

    total_cost = cpu_cost + memory_cost + storage_cost

    result = f"""## Cost Estimation for Namespace: {namespace}

**Cluster Type**: {cluster_type}
**Period**: {days} days (~{days/30:.1f} months)
**Pod Count**: {pod_count}

### Resource Allocation:
- **CPU**: {cpu_cores:.2f} cores
- **Memory**: {memory_gb:.2f} GB
- **Storage**: {storage_gb:.2f} GB

### Cost Breakdown:
- **Compute (CPU)**: ${cpu_cost:.2f}
  - {cpu_cores:.2f} cores × ${cpu_price:.6f}/core/hour × {hours} hours
- **Memory**: ${memory_cost:.2f}
  - {memory_gb:.2f} GB × ${memory_price:.6f}/GB/hour × {hours} hours
- **Storage**: ${storage_cost:.2f}
  - {storage_gb:.2f} GB × ${GKE_PRICING['storage_per_gb_month']:.4f}/GB/month

### **Total Estimated Cost**: ${total_cost:.2f}

### Cost Breakdown by Resource Type:
- Compute (CPU): {(cpu_cost/total_cost*100) if total_cost > 0 else 0:.1f}%
- Memory: {(memory_cost/total_cost*100) if total_cost > 0 else 0:.1f}%
- Storage: {(storage_cost/total_cost*100) if total_cost > 0 else 0:.1f}%

### Monthly Projection:
**Estimated Monthly Cost**: ${total_cost * (30/days):.2f}
**Estimated Annual Cost**: ${total_cost * (365/days):.2f}

### 💡 Cost Optimization Tips:
1. **Right-size resources**: Review if CPU/memory requests match actual usage
2. **Use Horizontal Pod Autoscaler (HPA)**: Scale pods based on demand
3. **Review storage**: Consider if all persistent volumes are necessary
4. **Spot/Preemptible nodes**: Save up to 80% for fault-tolerant workloads (Standard GKE)

**Note**: This is an estimate based on resource requests/limits. Actual costs may vary based on:
- Actual cluster configuration and region
- Network egress costs
- Load balancer costs
- Additional GCP services used
- Committed use discounts or sustained use discounts
"""

    return result


def estimate_cluster_cost(
    total_cpu_cores: float,
    total_memory_gb: float,
    total_storage_gb: float = 0.0,
    total_pods: int = 0,
    node_count: int = 0,
    is_autopilot: bool = True,
    days: int = 30
) -> str:
    """
    Estimates the total cost of a GKE cluster based on total resource allocation.

    Args:
        total_cpu_cores: Total CPU cores across all nodes
        total_memory_gb: Total memory in GB across all nodes
        total_storage_gb: Total persistent storage in GB
        total_pods: Total number of pods
        node_count: Number of nodes
        is_autopilot: Whether cluster is GKE Autopilot
        days: Number of days to estimate

    Returns:
        Cluster cost estimation
    """
    hours = days * 24

    if is_autopilot:
        cpu_price = GKE_PRICING["autopilot_cpu_per_core_hour"]
        memory_price = GKE_PRICING["autopilot_memory_per_gb_hour"]
        cluster_type = "GKE Autopilot"
        node_info = "Autopilot (managed by Google)"
    else:
        cpu_price = GKE_PRICING["cpu_per_core_hour"]
        memory_price = GKE_PRICING["memory_per_gb_hour"]
        cluster_type = "GKE Standard"
        node_info = f"{node_count} nodes"

    # Calculate costs
    cpu_cost = total_cpu_cores * cpu_price * hours
    memory_cost = total_memory_gb * memory_price * hours
    storage_cost = total_storage_gb * GKE_PRICING["storage_per_gb_month"] * (days / 30)

    # GKE cluster management fee (Standard only, ~$0.10/hour per cluster)
    management_fee = 0 if is_autopilot else (0.10 * hours)

    total_cost = cpu_cost + memory_cost + storage_cost + management_fee

    result = f"""## GKE Cluster Cost Estimation

**Cluster Type**: {cluster_type}
**Period**: {days} days (~{days/30:.1f} months)
**Infrastructure**: {node_info}
**Total Pods**: {total_pods}

### Resource Allocation:
- **Total CPU**: {total_cpu_cores:.2f} cores
- **Total Memory**: {total_memory_gb:.2f} GB
- **Total Storage**: {total_storage_gb:.2f} GB

### Cost Breakdown:
- **Compute (CPU)**: ${cpu_cost:.2f}
- **Memory**: ${memory_cost:.2f}
- **Storage**: ${storage_cost:.2f}
"""

    if management_fee > 0:
        result += f"- **Cluster Management Fee**: ${management_fee:.2f}\n"

    result += f"""
### **Total Estimated Cost**: ${total_cost:.2f}

### Monthly & Annual Projections:
- **Monthly**: ${total_cost * (30/days):.2f}
- **Annual**: ${total_cost * (365/days):.2f}

### Average Cost Per Pod:
- **Per Pod/Month**: ${(total_cost * (30/days) / total_pods) if total_pods > 0 else 0:.2f}

### 💡 Cluster-Wide Optimization Opportunities:
1. **Enable Cluster Autoscaler**: Automatically scale nodes based on workload
2. **Use Node Auto-Provisioning**: Right-size node pools automatically
3. **Implement Pod Disruption Budgets**: Safely scale down during low usage
4. **Review Namespace Resource Quotas**: Prevent over-allocation
5. **Consider Committed Use Discounts**: Save 25-55% for predictable workloads

**Savings Potential**: 20-40% through proper autoscaling and rightsizing

**Note**: This estimate is based on resource requests. Use GCP Billing Reports for actual costs.
"""

    return result


def compare_namespace_costs(namespaces_data: str) -> str:
    """
    Compares costs across multiple namespaces.

    Args:
        namespaces_data: Formatted string with namespace resource data
        Expected format: "namespace1:cpu,memory,storage|namespace2:cpu,memory,storage|..."
        Example: "production:10,32,100|staging:2,8,20|dev:1,4,10"

    Returns:
        Cost comparison breakdown
    """
    try:
        namespaces = []
        for ns_data in namespaces_data.split("|"):
            parts = ns_data.split(":")
            if len(parts) != 2:
                continue
            name = parts[0]
            resources = parts[1].split(",")
            if len(resources) < 2:
                continue

            cpu = float(resources[0])
            memory = float(resources[1])
            storage = float(resources[2]) if len(resources) > 2 else 0

            # Calculate monthly cost (Autopilot pricing)
            hours = 30 * 24
            cost = (
                cpu * GKE_PRICING["autopilot_cpu_per_core_hour"] * hours +
                memory * GKE_PRICING["autopilot_memory_per_gb_hour"] * hours +
                storage * GKE_PRICING["storage_per_gb_month"]
            )

            namespaces.append({
                "name": name,
                "cpu": cpu,
                "memory": memory,
                "storage": storage,
                "cost": cost
            })

        # Sort by cost
        namespaces.sort(key=lambda x: x["cost"], reverse=True)
        total_cost = sum(ns["cost"] for ns in namespaces)

        result = "## Namespace Cost Comparison\n\n"
        result += f"**Total Cluster Cost**: ${total_cost:.2f}/month\n\n"
        result += "### Cost Ranking (Highest to Lowest):\n\n"

        for i, ns in enumerate(namespaces, 1):
            pct = (ns["cost"] / total_cost * 100) if total_cost > 0 else 0
            result += f"{i}. **{ns['name']}**: ${ns['cost']:.2f}/month ({pct:.1f}%)\n"
            result += f"   - CPU: {ns['cpu']:.1f} cores | Memory: {ns['memory']:.1f} GB | Storage: {ns['storage']:.1f} GB\n\n"

        result += "\n### 💡 Optimization Recommendations:\n"
        if namespaces:
            top_namespace = namespaces[0]
            result += f"- Review **{top_namespace['name']}** namespace (highest cost: ${top_namespace['cost']:.2f}/month)\n"
            result += "- Check if all resources are actively used\n"
            result += "- Consider implementing resource quotas for cost control\n"

        return result

    except Exception as e:
        return f"Error parsing namespace data: {str(e)}\nExpected format: 'namespace:cpu,memory,storage|...'"
