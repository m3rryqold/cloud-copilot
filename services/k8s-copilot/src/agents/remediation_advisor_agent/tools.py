import yaml
import json

REMEDIATION_KNOWLEDGE_BASE = {
    "OOMKilled": {
        "description": "Container was terminated due to Out Of Memory",
        "causes": [
            "Memory limit is too low for the workload",
            "Memory leak in the application",
            "Unexpected spike in memory usage"
        ],
        "solutions": [
            "Increase memory limits in the pod spec",
            "Analyze the application for memory leaks",
            "Add resource requests to ensure proper scheduling",
            "Consider horizontal pod autoscaling"
        ]
    },
    "CrashLoopBackOff": {
        "description": "Pod is repeatedly crashing and restarting",
        "causes": [
            "Application error causing immediate exit",
            "Missing dependencies or configuration",
            "Failed health checks",
            "Incorrect container command or entrypoint"
        ],
        "solutions": [
            "Check pod logs for application errors",
            "Verify all ConfigMaps and Secrets are mounted correctly",
            "Review liveness and readiness probe configuration",
            "Ensure the container image is correct"
        ]
    },
    "ImagePullBackOff": {
        "description": "Cannot pull the container image",
        "causes": [
            "Image doesn't exist or wrong tag",
            "No authentication for private registry",
            "Network connectivity issues",
            "Rate limiting from registry"
        ],
        "solutions": [
            "Verify image name and tag are correct",
            "Create imagePullSecrets for private registries",
            "Check network policies and firewall rules",
            "Use a local or cached image"
        ]
    },
    "Pending": {
        "description": "Pod cannot be scheduled",
        "causes": [
            "Insufficient cluster resources",
            "No nodes match pod's nodeSelector/affinity",
            "PersistentVolumeClaim not bound",
            "Taints on nodes preventing scheduling"
        ],
        "solutions": [
            "Scale up the cluster or add more nodes",
            "Adjust resource requests to match available capacity",
            "Review nodeSelector and affinity rules",
            "Check PVC status and storage provisioning"
        ]
    },
    "ErrImagePull": {
        "description": "Failed to pull container image",
        "causes": [
            "Registry authentication failure",
            "Image doesn't exist",
            "Network issues"
        ],
        "solutions": [
            "Verify registry credentials and imagePullSecrets",
            "Confirm image exists in the registry",
            "Check DNS resolution and network connectivity"
        ]
    }
}


def suggest_fix(error_message: str) -> str:
    """Suggests comprehensive fixes for common Kubernetes errors.

    Args:
        error_message: The error message to suggest a fix for.

    Returns:
        A detailed suggested fix with causes and solutions.
    """
    suggestions = []

    for error_type, details in REMEDIATION_KNOWLEDGE_BASE.items():
        if error_type in error_message:
            suggestions.append(f"\n**{error_type}**")
            suggestions.append(f"Description: {details['description']}")
            suggestions.append("\nPossible Causes:")
            for cause in details['causes']:
                suggestions.append(f"  - {cause}")
            suggestions.append("\nRecommended Solutions:")
            for i, solution in enumerate(details['solutions'], 1):
                suggestions.append(f"  {i}. {solution}")

    if not suggestions:
        return """No specific remediation found for this error. General troubleshooting steps:
1. Check pod logs: kubectl logs <pod-name> -n <namespace>
2. Describe the pod: kubectl describe pod <pod-name> -n <namespace>
3. Check events: kubectl get events -n <namespace> --sort-by='.lastTimestamp'
4. Review pod configuration and resource limits
5. Verify all dependencies (ConfigMaps, Secrets, PVCs) exist"""

    return "\n".join(suggestions)


def generate_kubectl_commands(namespace: str, pod_name: str, error_type: str) -> str:
    """Generates specific kubectl commands for troubleshooting and remediation.

    Args:
        namespace: The namespace of the pod.
        pod_name: The name of the pod.
        error_type: The type of error detected.

    Returns:
        A list of kubectl commands to run.
    """
    commands = {
        "diagnostic": [
            f"# Get pod details",
            f"kubectl describe pod {pod_name} -n {namespace}",
            f"",
            f"# Check pod logs",
            f"kubectl logs {pod_name} -n {namespace} --tail=100",
            f"",
            f"# Check events",
            f"kubectl get events -n {namespace} --field-selector involvedObject.name={pod_name}",
        ],
        "OOMKilled": [
            f"# Check current resource limits",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].resources}}'",
            f"",
            f"# Get deployment name (if applicable)",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.metadata.labels}}'",
            f"",
            f"# Edit deployment to increase memory (replace DEPLOYMENT_NAME)",
            f"kubectl edit deployment <DEPLOYMENT_NAME> -n {namespace}",
            f"# Then increase memory limits, e.g., memory: '512Mi' -> memory: '1Gi'",
        ],
        "ImagePullBackOff": [
            f"# Check image name",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].image}}'",
            f"",
            f"# List image pull secrets",
            f"kubectl get secrets -n {namespace}",
            f"",
            f"# Create docker registry secret (if needed)",
            f"kubectl create secret docker-registry regcred \\",
            f"  --docker-server=<registry-url> \\",
            f"  --docker-username=<username> \\",
            f"  --docker-password=<password> \\",
            f"  -n {namespace}",
        ],
        "CrashLoopBackOff": [
            f"# Get previous container logs (from crashed container)",
            f"kubectl logs {pod_name} -n {namespace} --previous",
            f"",
            f"# Check liveness/readiness probes",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].livenessProbe}}'",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].readinessProbe}}'",
        ],
        "Pending": [
            f"# Check node resources",
            f"kubectl top nodes",
            f"",
            f"# Check pod resource requests",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.containers[*].resources.requests}}'",
            f"",
            f"# Check node affinity/selector",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.nodeSelector}}'",
            f"kubectl get pod {pod_name} -n {namespace} -o jsonpath='{{.spec.affinity}}'",
        ]
    }

    result = ["# Diagnostic Commands\n"]
    result.extend(commands["diagnostic"])

    if error_type in commands:
        result.append(f"\n\n# {error_type} Specific Commands\n")
        result.extend(commands[error_type])

    return "\n".join(result)


def generate_yaml_patch(namespace: str, resource_type: str, resource_name: str, error_type: str) -> str:
    """Generates YAML patches for common fixes.

    Args:
        namespace: The namespace of the resource.
        resource_type: Type of resource (deployment, pod, etc.).
        resource_name: Name of the resource.
        error_type: The type of error to fix.

    Returns:
        A YAML patch that can be applied.
    """
    patches = {
        "OOMKilled": {
            "description": "Increase memory limits for OOMKilled pods",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "<container-name>",
                                "resources": {
                                    "requests": {
                                        "memory": "256Mi",
                                        "cpu": "100m"
                                    },
                                    "limits": {
                                        "memory": "1Gi",
                                        "cpu": "500m"
                                    }
                                }
                            }]
                        }
                    }
                }
            },
            "apply_command": f"kubectl patch {resource_type} {resource_name} -n {namespace} --patch-file patch.yaml"
        },
        "ImagePullBackOff": {
            "description": "Add imagePullSecrets to deployment",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "imagePullSecrets": [
                                {"name": "regcred"}
                            ]
                        }
                    }
                }
            },
            "apply_command": f"kubectl patch {resource_type} {resource_name} -n {namespace} --patch-file patch.yaml"
        },
        "CrashLoopBackOff": {
            "description": "Adjust liveness probe settings to allow more time for startup",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "<container-name>",
                                "livenessProbe": {
                                    "initialDelaySeconds": 30,
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 5,
                                    "failureThreshold": 3
                                }
                            }]
                        }
                    }
                }
            },
            "apply_command": f"kubectl patch {resource_type} {resource_name} -n {namespace} --patch-file patch.yaml"
        }
    }

    if error_type not in patches:
        return f"No YAML patch template available for error type: {error_type}"

    patch_info = patches[error_type]
    result = [
        f"# {patch_info['description']}",
        f"# Save this to patch.yaml and apply with:",
        f"# {patch_info['apply_command']}",
        "",
        yaml.dump(patch_info['patch'], default_flow_style=False),
        f"\n# Or use kubectl patch directly:",
        f"kubectl patch {resource_type} {resource_name} -n {namespace} --type=strategic --patch '{json.dumps(patch_info['patch'])}'"
    ]

    return "\n".join(result)
