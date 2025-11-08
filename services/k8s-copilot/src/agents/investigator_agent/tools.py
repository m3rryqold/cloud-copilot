
from kubernetes import config, client
import yaml
import os
from typing import Optional

def get_pod_logs(namespace: str, pod_name: str, tail_lines: int = 100) -> str:
    """Gets the logs of a given pod in a given namespace.

    Args:
        namespace: The namespace of the pod.
        pod_name: The name of the pod.
        tail_lines: Number of lines to retrieve from the end of the logs.

    Returns:
        The logs of the pod.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines
        )
        return logs if logs else "No logs available"
    except Exception as e:
        return f"Error retrieving logs: {str(e)}"


def get_pod_description(namespace: str, pod_name: str) -> str:
    """Gets detailed description of a pod including configuration and status.

    Args:
        namespace: The namespace of the pod.
        pod_name: The name of the pod.

    Returns:
        Detailed pod information in YAML format.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    v1 = client.CoreV1Api()

    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        # Extract key information
        info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": {
                "phase": pod.status.phase,
                "conditions": [{"type": c.type, "status": c.status, "reason": c.reason, "message": c.message}
                              for c in (pod.status.conditions or [])],
                "container_statuses": []
            },
            "spec": {
                "node_name": pod.spec.node_name,
                "restart_policy": pod.spec.restart_policy,
                "containers": []
            }
        }

        # Container statuses
        if pod.status.container_statuses:
            for cs in pod.status.container_statuses:
                status_info = {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "image": cs.image
                }
                if cs.state.waiting:
                    status_info["state"] = {"waiting": {"reason": cs.state.waiting.reason, "message": cs.state.waiting.message}}
                elif cs.state.terminated:
                    status_info["state"] = {"terminated": {"reason": cs.state.terminated.reason, "exit_code": cs.state.terminated.exit_code}}
                elif cs.state.running:
                    status_info["state"] = {"running": {"started_at": str(cs.state.running.started_at)}}
                info["status"]["container_statuses"].append(status_info)

        # Container specs
        for container in pod.spec.containers:
            container_info = {
                "name": container.name,
                "image": container.image,
                "resources": {}
            }
            if container.resources:
                if container.resources.requests:
                    container_info["resources"]["requests"] = dict(container.resources.requests)
                if container.resources.limits:
                    container_info["resources"]["limits"] = dict(container.resources.limits)
            info["spec"]["containers"].append(container_info)

        return yaml.dump(info, default_flow_style=False)
    except Exception as e:
        return f"Error retrieving pod description: {str(e)}"


def analyze_deployment_history(namespace: str, deployment_name: Optional[str] = None) -> str:
    """Analyzes deployment history and recent changes.

    Args:
        namespace: The namespace to check.
        deployment_name: Optional specific deployment name.

    Returns:
        Deployment history and rollout information.
    """
    try:
        config.load_incluster_config()
    except config.ConfigException:
        kubeconfig_path = os.getenv('KUBECONFIG', os.path.expanduser('~/.kube/config'))
        config.load_kube_config(config_file=kubeconfig_path)

    apps_v1 = client.AppsV1Api()

    try:
        if deployment_name:
            deployments = [apps_v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)]
        else:
            deployments = apps_v1.list_namespaced_deployment(namespace=namespace).items

        if not deployments:
            return "No deployments found"

        results = []
        for deployment in deployments:
            info = [f"\nDeployment: {deployment.metadata.name}"]
            info.append(f"Replicas: {deployment.status.replicas}/{deployment.spec.replicas}")
            info.append(f"Ready: {deployment.status.ready_replicas or 0}")
            info.append(f"Available: {deployment.status.available_replicas or 0}")
            info.append(f"Unavailable: {deployment.status.unavailable_replicas or 0}")

            # Get conditions
            if deployment.status.conditions:
                info.append("Conditions:")
                for condition in deployment.status.conditions:
                    info.append(f"  - {condition.type}: {condition.status} - {condition.message}")

            # Get ReplicaSets for this deployment
            selector = deployment.spec.selector.match_labels
            label_selector = ",".join([f"{k}={v}" for k, v in selector.items()])

            replica_sets = apps_v1.list_namespaced_replica_set(
                namespace=namespace,
                label_selector=label_selector
            )

            if replica_sets.items:
                info.append("\nReplicaSet History:")
                for rs in sorted(replica_sets.items, key=lambda x: x.metadata.creation_timestamp, reverse=True)[:5]:
                    info.append(f"  - {rs.metadata.name}: {rs.status.replicas} replicas (created: {rs.metadata.creation_timestamp})")

            results.append("\n".join(info))

        return "\n".join(results)
    except Exception as e:
        return f"Error analyzing deployment history: {str(e)}"
