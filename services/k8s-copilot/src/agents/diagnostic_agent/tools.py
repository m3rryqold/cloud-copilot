from kubernetes import config, client
from google.cloud import monitoring_v3
from google.protobuf import duration_pb2
import time
import os
from typing import Optional

def get_cluster_info() -> str:
    """Gets information about the current Kubernetes cluster.

    Returns:
        A string containing cluster name, version, and endpoint information.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    try:
        v1 = client.CoreV1Api()
        version_api = client.VersionApi()

        # Get cluster version
        version_info = version_api.get_code()

        # Get current context info
        contexts, active_context = config.list_kube_config_contexts(config_file=os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config')))
        cluster_name = active_context['context']['cluster'] if active_context else "Unknown"

        # Get node count
        nodes = v1.list_node()
        node_count = len(nodes.items)

        info = [
            f"Cluster Name: {cluster_name}",
            f"Kubernetes Version: {version_info.git_version}",
            f"Nodes: {node_count}",
            f"Platform: {version_info.platform}"
        ]

        return "\n".join(info)
    except Exception as e:
        return f"Error retrieving cluster info: {str(e)}"


def list_namespaces() -> str:
    """Lists all namespaces in the cluster.

    Returns:
        A string containing all namespaces and their status.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()

    namespace_list = []
    for ns in namespaces.items:
        status = ns.status.phase
        age = ns.metadata.creation_timestamp
        namespace_list.append(f"- {ns.metadata.name} (Status: {status}, Created: {age})")

    return "\n".join(namespace_list) if namespace_list else "No namespaces found"


def list_all_pods(namespace: Optional[str] = None) -> str:
    """Lists all pods in the cluster or a specific namespace.

    Args:
        namespace: Optional namespace to filter pods. If None, lists all pods cluster-wide.

    Returns:
        A string containing pod information including name, namespace, status, and node.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    if namespace:
        pod_list = v1.list_namespaced_pod(namespace)
    else:
        pod_list = v1.list_pod_for_all_namespaces()

    pods = []
    for pod in pod_list.items:
        ns = pod.metadata.namespace
        name = pod.metadata.name
        phase = pod.status.phase
        node = pod.spec.node_name or "Unassigned"
        restarts = sum(cs.restart_count for cs in pod.status.container_statuses) if pod.status.container_statuses else 0

        pods.append(f"{ns}/{name} - Status: {phase}, Node: {node}, Restarts: {restarts}")

    if not pods:
        return f"No pods found{f' in namespace {namespace}' if namespace else ' in cluster'}"

    return "\n".join(pods)


def get_unhealthy_pods(namespace: Optional[str] = None) -> str:
    """Gets all pods that are not in a 'Running' or 'Succeeded' state.

    Args:
        namespace: Optional namespace to check. If None, checks all namespaces.

    Returns:
        A string containing a list of unhealthy pods and their status.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    if namespace:
        pod_list = v1.list_namespaced_pod(namespace)
    else:
        pod_list = v1.list_pod_for_all_namespaces()

    unhealthy_pods = []
    for pod in pod_list.items:
        if pod.status.phase not in ["Running", "Succeeded"]:
            container_statuses = []
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.state.waiting:
                        container_statuses.append(f"Waiting: {cs.state.waiting.reason}")
                    elif cs.state.terminated:
                        container_statuses.append(f"Terminated: {cs.state.terminated.reason}")

            status_detail = ", ".join(container_statuses) if container_statuses else pod.status.phase
            ns = pod.metadata.namespace
            restarts = sum(cs.restart_count for cs in pod.status.container_statuses) if pod.status.container_statuses else 0
            unhealthy_pods.append(f"{ns}/{pod.metadata.name} - Status: {status_detail}, Restarts: {restarts}")

    if not unhealthy_pods:
        return f"No unhealthy pods found{f' in namespace {namespace}' if namespace else ' in cluster'}."

    return "\n".join(unhealthy_pods)


def get_cluster_metrics(project_id: Optional[str] = None) -> str:
    """Gets cluster-level metrics from Cloud Monitoring.

    Args:
        project_id: GCP project ID. If None, uses default project.

    Returns:
        A string containing cluster CPU and memory metrics.
    """
    try:
        client = monitoring_v3.MetricServiceClient()

        if not project_id:
            import google.auth
            _, project_id = google.auth.default()

        project_name = f"projects/{project_id}"

        # Get the last 5 minutes of data
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10 ** 9)
        interval = monitoring_v3.TimeInterval({
            "end_time": {"seconds": seconds, "nanos": nanos},
            "start_time": {"seconds": (seconds - 300), "nanos": nanos},
        })

        results = []

        # CPU usage metric
        cpu_filter = 'metric.type="kubernetes.io/container/cpu/core_usage_time" AND resource.type="k8s_container"'
        cpu_results = client.list_time_series(
            request={
                "name": project_name,
                "filter": cpu_filter,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        cpu_values = []
        for result in cpu_results:
            if result.points:
                cpu_values.append(result.points[0].value.double_value)

        if cpu_values:
            results.append(f"Average CPU usage: {sum(cpu_values) / len(cpu_values):.2f} cores")

        # Memory usage metric
        mem_filter = 'metric.type="kubernetes.io/container/memory/used_bytes" AND resource.type="k8s_container"'
        mem_results = client.list_time_series(
            request={
                "name": project_name,
                "filter": mem_filter,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        mem_values = []
        for result in mem_results:
            if result.points:
                mem_values.append(result.points[0].value.int64_value)

        if mem_values:
            avg_mem_gb = sum(mem_values) / len(mem_values) / (1024**3)
            results.append(f"Average Memory usage: {avg_mem_gb:.2f} GB")

        return "\n".join(results) if results else "No metrics data available"

    except Exception as e:
        return f"Error retrieving cluster metrics: {str(e)}"


def get_node_resources() -> str:
    """Gets resource usage information for all nodes in the cluster.

    Returns:
        A string containing node resource information including CPU and memory capacity/usage.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    try:
        nodes = v1.list_node()

        node_info = []
        for node in nodes.items:
            name = node.metadata.name
            status = "Ready" if any(c.type == "Ready" and c.status == "True" for c in node.status.conditions) else "NotReady"

            # Get capacity
            capacity = node.status.capacity
            cpu_capacity = capacity.get('cpu', 'Unknown')
            memory_capacity_bytes = capacity.get('memory', '0')
            memory_capacity_gb = int(memory_capacity_bytes.replace('Ki', '')) / (1024 * 1024) if 'Ki' in memory_capacity_bytes else 0

            # Get allocatable
            allocatable = node.status.allocatable
            cpu_allocatable = allocatable.get('cpu', 'Unknown')
            memory_allocatable_bytes = allocatable.get('memory', '0')
            memory_allocatable_gb = int(memory_allocatable_bytes.replace('Ki', '')) / (1024 * 1024) if 'Ki' in memory_allocatable_bytes else 0

            # Get pod count
            field_selector = f"spec.nodeName={name}"
            pods_on_node = v1.list_pod_for_all_namespaces(field_selector=field_selector)
            pod_count = len(pods_on_node.items)

            node_info.append(
                f"Node: {name}\n"
                f"  Status: {status}\n"
                f"  CPU: {cpu_allocatable}/{cpu_capacity} allocatable\n"
                f"  Memory: {memory_allocatable_gb:.1f}GB/{memory_capacity_gb:.1f}GB allocatable\n"
                f"  Pods: {pod_count}"
            )

        return "\n\n".join(node_info) if node_info else "No nodes found"
    except Exception as e:
        return f"Error retrieving node resources: {str(e)}"


def get_pod_events(namespace: str, pod_name: str) -> str:
    """Gets Kubernetes events for a specific pod.

    Args:
        namespace: The namespace of the pod.
        pod_name: The name of the pod.

    Returns:
        A string containing recent events for the pod.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    field_selector = f"involvedObject.name={pod_name}"
    events = v1.list_namespaced_event(namespace, field_selector=field_selector)

    if not events.items:
        return f"No events found for pod '{pod_name}' in namespace '{namespace}'."

    event_lines = []
    for event in sorted(events.items, key=lambda x: x.last_timestamp or x.event_time, reverse=True)[:10]:
        timestamp = event.last_timestamp or event.event_time
        event_lines.append(f"{timestamp} - {event.type}: {event.reason} - {event.message}")

    return "\n".join(event_lines)


def get_namespace_resources(namespace: str) -> str:
    """Gets total resource allocation (requests) for a namespace.

    Calculates the sum of CPU and memory requests across all pods in the namespace.
    This is useful for cost estimation and capacity planning.

    Args:
        namespace: The namespace to analyze

    Returns:
        Resource allocation summary including total CPU cores, memory GB, storage GB, and pod count
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    try:
        # Get all pods in namespace
        pods = v1.list_namespaced_pod(namespace)

        total_cpu_millicores = 0
        total_memory_bytes = 0
        total_storage_bytes = 0
        pod_count = len(pods.items)

        # Sum up CPU and memory requests from all containers in all pods
        for pod in pods.items:
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        # Parse CPU (can be in cores like "1" or millicores like "100m")
                        cpu_request = container.resources.requests.get('cpu', '0')
                        if cpu_request:
                            if isinstance(cpu_request, str):
                                if cpu_request.endswith('m'):
                                    total_cpu_millicores += int(cpu_request[:-1])
                                else:
                                    total_cpu_millicores += int(float(cpu_request) * 1000)

                        # Parse memory (can be in various units: Mi, Gi, M, G, Ki, K)
                        memory_request = container.resources.requests.get('memory', '0')
                        if memory_request:
                            if isinstance(memory_request, str):
                                memory_str = memory_request.upper()
                                if memory_str.endswith('KI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024
                                elif memory_str.endswith('K'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000
                                elif memory_str.endswith('MI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024 * 1024
                                elif memory_str.endswith('M'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000 * 1000
                                elif memory_str.endswith('GI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024 * 1024 * 1024
                                elif memory_str.endswith('G'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000 * 1000 * 1000
                                else:
                                    total_memory_bytes += int(memory_str)

        # Get persistent volumes in namespace
        pvcs = v1.list_namespaced_persistent_volume_claim(namespace)
        for pvc in pvcs.items:
            if pvc.spec.resources and pvc.spec.resources.requests:
                storage_request = pvc.spec.resources.requests.get('storage', '0')
                if storage_request:
                    if isinstance(storage_request, str):
                        storage_str = storage_request.upper()
                        if storage_str.endswith('GI'):
                            total_storage_bytes += int(storage_str[:-2]) * 1024 * 1024 * 1024
                        elif storage_str.endswith('G'):
                            total_storage_bytes += int(storage_str[:-1]) * 1000 * 1000 * 1000
                        elif storage_str.endswith('MI'):
                            total_storage_bytes += int(storage_str[:-2]) * 1024 * 1024
                        elif storage_str.endswith('M'):
                            total_storage_bytes += int(storage_str[:-1]) * 1000 * 1000

        # Convert to human-readable units
        total_cpu_cores = total_cpu_millicores / 1000
        total_memory_gb = total_memory_bytes / (1024 ** 3)
        total_storage_gb = total_storage_bytes / (1024 ** 3)

        # Get cluster info to determine if it's Autopilot
        try:
            # Try to detect Autopilot by checking for Autopilot-specific annotations or node labels
            nodes = v1.list_node()
            is_autopilot = False
            if nodes.items:
                first_node = nodes.items[0]
                if first_node.metadata.labels:
                    is_autopilot = 'cloud.google.com/gke-nodepool' in first_node.metadata.labels and \
                                 'autopilot' in str(first_node.metadata.labels).lower()
            cluster_type = "GKE Autopilot" if is_autopilot else "GKE Standard"
        except:
            cluster_type = "Unknown"
            is_autopilot = True  # Default to Autopilot for cost estimation

        result = f"""## Resource Allocation for Namespace: {namespace}

**Cluster Type**: {cluster_type}
**Pod Count**: {pod_count}

### Resource Requests Summary:
- **CPU**: {total_cpu_cores:.2f} cores ({total_cpu_millicores} millicores)
- **Memory**: {total_memory_gb:.2f} GB ({total_memory_bytes / (1024**2):.2f} MiB)
- **Storage (PVCs)**: {total_storage_gb:.2f} GB

### For Cost Estimation:
Use these values with Cost Copilot:
- namespace: {namespace}
- cpu_cores: {total_cpu_cores:.2f}
- memory_gb: {total_memory_gb:.2f}
- storage_gb: {total_storage_gb:.2f}
- pod_count: {pod_count}
- is_autopilot: {is_autopilot}

**Note**: These are resource *requests*, not actual usage. Actual usage may be lower.
"""
        return result

    except Exception as e:
        return f"Error getting namespace resources: {str(e)}"


def get_cluster_resources() -> str:
    """Gets total resource allocation (requests) for the entire cluster.

    Calculates the sum of CPU and memory requests across all namespaces and pods.
    This is useful for cluster-wide cost estimation and capacity planning.

    Returns:
        Cluster-wide resource allocation summary including total CPU, memory, storage, pods, and nodes
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    try:
        # Get all pods in cluster
        pods = v1.list_pod_for_all_namespaces()

        total_cpu_millicores = 0
        total_memory_bytes = 0
        total_storage_bytes = 0
        pod_count = len(pods.items)

        # Sum up CPU and memory requests from all containers in all pods
        for pod in pods.items:
            if pod.spec.containers:
                for container in pod.spec.containers:
                    if container.resources and container.resources.requests:
                        # Parse CPU
                        cpu_request = container.resources.requests.get('cpu', '0')
                        if cpu_request:
                            if isinstance(cpu_request, str):
                                if cpu_request.endswith('m'):
                                    total_cpu_millicores += int(cpu_request[:-1])
                                else:
                                    total_cpu_millicores += int(float(cpu_request) * 1000)

                        # Parse memory
                        memory_request = container.resources.requests.get('memory', '0')
                        if memory_request:
                            if isinstance(memory_request, str):
                                memory_str = memory_request.upper()
                                if memory_str.endswith('KI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024
                                elif memory_str.endswith('K'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000
                                elif memory_str.endswith('MI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024 * 1024
                                elif memory_str.endswith('M'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000 * 1000
                                elif memory_str.endswith('GI'):
                                    total_memory_bytes += int(memory_str[:-2]) * 1024 * 1024 * 1024
                                elif memory_str.endswith('G'):
                                    total_memory_bytes += int(memory_str[:-1]) * 1000 * 1000 * 1000
                                else:
                                    total_memory_bytes += int(memory_str)

        # Get all persistent volumes across all namespaces
        try:
            all_pvcs = v1.list_persistent_volume_claim_for_all_namespaces()
            for pvc in all_pvcs.items:
                if pvc.spec.resources and pvc.spec.resources.requests:
                    storage_request = pvc.spec.resources.requests.get('storage', '0')
                    if storage_request:
                        if isinstance(storage_request, str):
                            storage_str = storage_request.upper()
                            if storage_str.endswith('GI'):
                                total_storage_bytes += int(storage_str[:-2]) * 1024 * 1024 * 1024
                            elif storage_str.endswith('G'):
                                total_storage_bytes += int(storage_str[:-1]) * 1000 * 1000 * 1000
                            elif storage_str.endswith('MI'):
                                total_storage_bytes += int(storage_str[:-2]) * 1024 * 1024
                            elif storage_str.endswith('M'):
                                total_storage_bytes += int(storage_str[:-1]) * 1000 * 1000
        except Exception as e:
            print(f"Warning: Could not get PVCs: {e}")

        # Get node count
        nodes = v1.list_node()
        node_count = len(nodes.items)

        # Detect cluster type
        is_autopilot = False
        if nodes.items:
            first_node = nodes.items[0]
            if first_node.metadata.labels:
                is_autopilot = 'cloud.google.com/gke-nodepool' in first_node.metadata.labels and \
                             'autopilot' in str(first_node.metadata.labels).lower()
        cluster_type = "GKE Autopilot" if is_autopilot else "GKE Standard"

        # Convert to human-readable units
        total_cpu_cores = total_cpu_millicores / 1000
        total_memory_gb = total_memory_bytes / (1024 ** 3)
        total_storage_gb = total_storage_bytes / (1024 ** 3)

        result = f"""## Cluster-Wide Resource Allocation

**Cluster Type**: {cluster_type}
**Node Count**: {node_count}
**Total Pods**: {pod_count}

### Total Resource Requests Across All Namespaces:
- **CPU**: {total_cpu_cores:.2f} cores ({total_cpu_millicores} millicores)
- **Memory**: {total_memory_gb:.2f} GB ({total_memory_bytes / (1024**2):.2f} MiB)
- **Storage (PVCs)**: {total_storage_gb:.2f} GB

### Average Per Pod:
- **CPU per pod**: {(total_cpu_cores / pod_count) if pod_count > 0 else 0:.3f} cores
- **Memory per pod**: {(total_memory_gb / pod_count) if pod_count > 0 else 0:.3f} GB

### For Cost Estimation:
Use these values with Cost Copilot:
- total_cpu_cores: {total_cpu_cores:.2f}
- total_memory_gb: {total_memory_gb:.2f}
- total_storage_gb: {total_storage_gb:.2f}
- total_pods: {pod_count}
- node_count: {node_count}
- is_autopilot: {is_autopilot}

**Note**: These are resource *requests*, not actual usage. Actual usage may be lower.
"""
        return result

    except Exception as e:
        return f"Error getting cluster resources: {str(e)}"
