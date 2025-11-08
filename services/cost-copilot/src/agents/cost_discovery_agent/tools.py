"""
Cost Discovery Agent Tools
Scans GCP resources to identify idle and underutilized resources
"""

import os
from typing import Optional
from google.cloud import asset_v1, compute_v1, monitoring_v3, resourcemanager_v3
from google.cloud.monitoring_v3 import query
import datetime


def get_current_project() -> str:
    """Gets the current GCP project ID from environment or Application Default Credentials."""
    project_id = os.getenv('GCP_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        import google.auth
        _, project_id = google.auth.default()
    return project_id or "unknown"


def list_accessible_projects() -> str:
    """
    Lists all GCP projects accessible to the service account.
    Returns project IDs, names, and current status.
    """
    try:
        client = resourcemanager_v3.ProjectsClient()
        request = resourcemanager_v3.ListProjectsRequest()

        projects_info = []
        for project in client.list_projects(request=request):
            projects_info.append({
                "project_id": project.project_id,
                "name": project.display_name,
                "state": project.state.name,
                "create_time": str(project.create_time)
            })

        if not projects_info:
            return "No accessible projects found. Ensure the service account has resourcemanager.projects.list permission."

        result = f"Found {len(projects_info)} accessible project(s):\n\n"
        for proj in projects_info:
            result += f"- **{proj['project_id']}** ({proj['name']})\n"
            result += f"  Status: {proj['state']}\n"
            result += f"  Created: {proj['create_time']}\n\n"

        return result

    except Exception as e:
        return f"Error listing projects: {str(e)}\nEnsure service account has roles/resourcemanager.projectViewer role."


def scan_compute_resources(project_id: Optional[str] = None) -> str:
    """
    Scans compute resources (VMs, disks, static IPs) in the specified project.
    Shows resource counts and basic statistics.
    """
    if not project_id:
        project_id = get_current_project()

    try:
        result = f"## Compute Resources in Project: {project_id}\n\n"

        # Count VMs
        instances_client = compute_v1.InstancesClient()
        total_instances = 0
        instance_zones = {}

        for zone in _list_zones(project_id):
            instances = instances_client.list(project=project_id, zone=zone)
            zone_count = 0
            for instance in instances:
                zone_count += 1
                total_instances += 1
            if zone_count > 0:
                instance_zones[zone] = zone_count

        result += f"**Compute Instances (VMs):** {total_instances}\n"
        if instance_zones:
            for zone, count in instance_zones.items():
                result += f"  - {zone}: {count} instance(s)\n"

        # Count Disks
        disks_client = compute_v1.DisksClient()
        total_disks = 0
        total_disk_size_gb = 0

        for zone in _list_zones(project_id):
            disks = disks_client.list(project=project_id, zone=zone)
            for disk in disks:
                total_disks += 1
                total_disk_size_gb += disk.size_gb if hasattr(disk, 'size_gb') else 0

        result += f"\n**Persistent Disks:** {total_disks} ({total_disk_size_gb} GB total)\n"

        # Count Static IPs
        addresses_client = compute_v1.AddressesClient()
        total_addresses = 0

        for region in _list_regions(project_id):
            addresses = addresses_client.list(project=project_id, region=region)
            for _ in addresses:
                total_addresses += 1

        result += f"\n**Static IP Addresses:** {total_addresses}\n"

        return result

    except Exception as e:
        return f"Error scanning compute resources: {str(e)}\nEnsure service account has roles/compute.viewer role."


def find_idle_resources(project_id: Optional[str] = None, days: int = 7) -> str:
    """
    Identifies potentially idle compute resources based on CPU utilization.
    A resource is considered idle if average CPU < 5% over the specified period.
    """
    if not project_id:
        project_id = get_current_project()

    try:
        result = f"## Idle Resources (< 5% CPU over last {days} days)\n\n"
        result += f"Project: {project_id}\n\n"

        instances_client = compute_v1.InstancesClient()
        monitoring_client = monitoring_v3.MetricServiceClient()

        idle_instances = []
        checked_instances = 0

        # Get all running instances
        for zone in _list_zones(project_id):
            instances = instances_client.list(project=project_id, zone=zone)

            for instance in instances:
                if instance.status != "RUNNING":
                    continue

                checked_instances += 1

                # Query CPU utilization from Cloud Monitoring
                interval = monitoring_v3.TimeInterval()
                now = datetime.datetime.utcnow()
                interval.end_time = now
                interval.start_time = now - datetime.timedelta(days=days)

                try:
                    request = monitoring_v3.ListTimeSeriesRequest(
                        name=f"projects/{project_id}",
                        filter=f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.labels.instance_id="{instance.id}"',
                        interval=interval,
                        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                    )

                    results = monitoring_client.list_time_series(request=request)

                    # Calculate average CPU
                    total_cpu = 0
                    point_count = 0
                    for series in results:
                        for point in series.points:
                            total_cpu += point.value.double_value
                            point_count += 1

                    if point_count > 0:
                        avg_cpu = (total_cpu / point_count) * 100
                        if avg_cpu < 5.0:
                            idle_instances.append({
                                "name": instance.name,
                                "zone": zone,
                                "machine_type": instance.machine_type.split("/")[-1],
                                "avg_cpu": f"{avg_cpu:.2f}%"
                            })
                except Exception:
                    # Skip instances without metrics
                    pass

        if not idle_instances:
            result += f"No idle instances found. Checked {checked_instances} running instance(s).\n"
        else:
            result += f"Found {len(idle_instances)} idle instance(s):\n\n"
            for inst in idle_instances:
                result += f"- **{inst['name']}** ({inst['machine_type']})\n"
                result += f"  Zone: {inst['zone']}\n"
                result += f"  Avg CPU: {inst['avg_cpu']}\n"
                result += f"  💡 Consider stopping or downsizing\n\n"

        return result

    except Exception as e:
        return f"Error finding idle resources: {str(e)}\nEnsure service account has roles/monitoring.viewer role."


def list_unattached_disks(project_id: Optional[str] = None) -> str:
    """
    Lists persistent disks not attached to any VM instance.
    These disks incur costs but provide no value.
    """
    if not project_id:
        project_id = get_current_project()

    try:
        disks_client = compute_v1.DisksClient()
        unattached_disks = []
        total_wasted_gb = 0

        for zone in _list_zones(project_id):
            disks = disks_client.list(project=project_id, zone=zone)

            for disk in disks:
                # Check if disk has any users (attached VMs)
                if not disk.users or len(disk.users) == 0:
                    size_gb = disk.size_gb if hasattr(disk, 'size_gb') else 0
                    unattached_disks.append({
                        "name": disk.name,
                        "zone": zone,
                        "size_gb": size_gb,
                        "type": disk.type.split("/")[-1] if hasattr(disk, 'type') else "unknown"
                    })
                    total_wasted_gb += size_gb

        if not unattached_disks:
            return f"No unattached disks found in project {project_id}. Good job! 🎉"

        result = f"## Unattached Persistent Disks\n\n"
        result += f"Project: {project_id}\n\n"
        result += f"Found {len(unattached_disks)} unattached disk(s) ({total_wasted_gb} GB total):\n\n"

        for disk in unattached_disks:
            result += f"- **{disk['name']}**\n"
            result += f"  Zone: {disk['zone']}\n"
            result += f"  Size: {disk['size_gb']} GB\n"
            result += f"  Type: {disk['type']}\n"
            result += f"  💰 Costing money with no attached VM\n\n"

        # Rough cost estimate (PD-Standard: $0.04/GB/month, PD-SSD: $0.17/GB/month)
        estimated_cost_min = total_wasted_gb * 0.04
        estimated_cost_max = total_wasted_gb * 0.17
        result += f"**Estimated monthly waste:** ${estimated_cost_min:.2f} - ${estimated_cost_max:.2f}\n"
        result += f"💡 Consider deleting these disks or creating snapshots first.\n"

        return result

    except Exception as e:
        return f"Error listing unattached disks: {str(e)}"


def list_idle_static_ips(project_id: Optional[str] = None) -> str:
    """
    Lists static IP addresses not attached to any resource.
    Unattached IPs cost money (~$3-4/month each).
    """
    if not project_id:
        project_id = get_current_project()

    try:
        addresses_client = compute_v1.AddressesClient()
        idle_ips = []

        for region in _list_regions(project_id):
            addresses = addresses_client.list(project=project_id, region=region)

            for address in addresses:
                # Check if address is not in use
                if address.status == "RESERVED" and not address.users:
                    idle_ips.append({
                        "name": address.name,
                        "region": region,
                        "ip": address.address if hasattr(address, 'address') else "N/A"
                    })

        if not idle_ips:
            return f"No idle static IPs found in project {project_id}. All IPs are in use! 👍"

        result = f"## Idle Static IP Addresses\n\n"
        result += f"Project: {project_id}\n\n"
        result += f"Found {len(idle_ips)} idle static IP(s):\n\n"

        for ip in idle_ips:
            result += f"- **{ip['name']}**\n"
            result += f"  Region: {ip['region']}\n"
            result += f"  Address: {ip['ip']}\n"
            result += f"  💰 ~$3-4/month per IP\n\n"

        estimated_monthly_cost = len(idle_ips) * 3.5
        result += f"**Estimated monthly waste:** ~${estimated_monthly_cost:.2f}\n"
        result += f"💡 Consider releasing these IPs if not needed.\n"

        return result

    except Exception as e:
        return f"Error listing idle static IPs: {str(e)}"


# Helper functions

def _list_zones(project_id: str, max_zones: int = 10) -> list:
    """Returns a list of GCP zones (limited for performance)."""
    try:
        zones_client = compute_v1.ZonesClient()
        zones = zones_client.list(project=project_id)
        return [zone.name for zone in list(zones)[:max_zones]]
    except Exception:
        # Fallback to common zones
        return ["us-central1-a", "us-central1-b", "us-east1-b", "europe-west1-b"]


def _list_regions(project_id: str, max_regions: int = 5) -> list:
    """Returns a list of GCP regions (limited for performance)."""
    try:
        regions_client = compute_v1.RegionsClient()
        regions = regions_client.list(project=project_id)
        return [region.name for region in list(regions)[:max_regions]]
    except Exception:
        # Fallback to common regions
        return ["us-central1", "us-east1", "europe-west1"]
