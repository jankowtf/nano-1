"""Deployment skills for nanobricks.

Provides Docker and Kubernetes deployment capabilities.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from nanobricks.protocol import NanobrickProtocol, T_deps, T_in, T_out
from nanobricks.skill import NanobrickEnhanced, Skill


@dataclass
class DockerConfig:
    """Docker deployment configuration."""

    base_image: str = "python:3.13-slim"
    working_dir: str = "/app"
    expose_ports: list[int] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    system_packages: list[str] = field(default_factory=list)
    entrypoint: list[str] | None = None
    cmd: list[str] | None = None
    labels: dict[str, str] = field(default_factory=dict)
    healthcheck: dict[str, Any] | None = None
    user: str | None = None


@dataclass
class KubernetesConfig:
    """Kubernetes deployment configuration."""

    namespace: str = "default"
    replicas: int = 1
    service_type: str = "ClusterIP"
    service_port: int = 8080
    container_port: int = 8080
    resources: dict[str, dict[str, str]] = field(
        default_factory=lambda: {
            "limits": {"cpu": "1", "memory": "512Mi"},
            "requests": {"cpu": "100m", "memory": "128Mi"},
        }
    )
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    env_from_configmap: str | None = None
    env_from_secret: str | None = None
    liveness_probe: dict[str, Any] | None = None
    readiness_probe: dict[str, Any] | None = None
    autoscaling: dict[str, Any] | None = None


class SkillDocker(Skill):
    """Docker deployment skill for nanobricks."""

    def __init__(self, config: DockerConfig | None = None):
        """Initialize Docker skill.

        Args:
            config: Docker configuration
        """
        super().__init__()
        self.docker_config = config or DockerConfig()
        self._dockerfile_content: str | None = None
        self._compose_content: str | None = None

    def _create_enhanced_brick(
        self, brick: NanobrickProtocol[T_in, T_out, T_deps]
    ) -> NanobrickEnhanced[T_in, T_out, T_deps]:
        """Create enhanced brick with Docker capabilities."""

        class DockerEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
                # Just pass through to the wrapped brick
                return await self._wrapped.invoke(input, deps=deps)

            def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
                return self._wrapped.invoke_sync(input, deps=deps)

        return DockerEnhanced(brick, self)

    def generate_dockerfile(self, brick: NanobrickProtocol) -> str:
        """Generate Dockerfile for a nanobrick.

        Args:
            brick: Nanobrick to containerize

        Returns:
            Dockerfile content
        """
        lines = []

        # Base image
        lines.append(f"FROM {self.docker_config.base_image}")
        lines.append("")

        # Labels
        if self.docker_config.labels:
            for key, value in self.docker_config.labels.items():
                lines.append(f'LABEL {key}="{value}"')
            lines.append("")

        # System packages
        if self.docker_config.system_packages:
            lines.append("RUN apt-get update && apt-get install -y \\")
            for pkg in self.docker_config.system_packages[:-1]:
                lines.append(f"    {pkg} \\")
            lines.append(f"    {self.docker_config.system_packages[-1]} \\")
            lines.append("    && rm -rf /var/lib/apt/lists/*")
            lines.append("")

        # Working directory
        lines.append(f"WORKDIR {self.docker_config.working_dir}")
        lines.append("")

        # Python dependencies
        if self.docker_config.dependencies:
            lines.append("# Install Python dependencies")
            lines.append("COPY requirements.txt .")
            lines.append("RUN pip install --no-cache-dir -r requirements.txt")
            lines.append("")

        # Copy application code
        lines.append("# Copy application code")
        lines.append("COPY . .")
        lines.append("")

        # Environment variables
        if self.docker_config.environment:
            lines.append("# Environment variables")
            for key, value in self.docker_config.environment.items():
                lines.append(f"ENV {key}={value}")
            lines.append("")

        # User
        if self.docker_config.user:
            lines.append(f"USER {self.docker_config.user}")
            lines.append("")

        # Expose ports
        if self.docker_config.expose_ports:
            for port in self.docker_config.expose_ports:
                lines.append(f"EXPOSE {port}")
            lines.append("")

        # Health check
        if self.docker_config.healthcheck:
            hc = self.docker_config.healthcheck
            cmd = " ".join(
                hc.get("test", ["CMD", "curl", "-f", "http://localhost:8080/health"])
            )
            interval = hc.get("interval", "30s")
            timeout = hc.get("timeout", "10s")
            retries = hc.get("retries", 3)
            lines.append(
                f"HEALTHCHECK --interval={interval} --timeout={timeout} --retries={retries} \\"
            )
            lines.append(f"    {cmd}")
            lines.append("")

        # Entrypoint and CMD
        if self.docker_config.entrypoint:
            lines.append(f"ENTRYPOINT {json.dumps(self.docker_config.entrypoint)}")

        if self.docker_config.cmd:
            lines.append(f"CMD {json.dumps(self.docker_config.cmd)}")
        elif not self.docker_config.entrypoint:
            # Default command
            lines.append(f'CMD ["python", "-m", "nanobricks", "run", "{brick.name}"]')

        self._dockerfile_content = "\n".join(lines)
        return self._dockerfile_content

    def generate_compose(
        self,
        services: dict[str, NanobrickProtocol],
        networks: list[str] | None = None,
        volumes: dict[str, dict[str, str]] | None = None,
    ) -> str:
        """Generate docker-compose.yml for multiple nanobricks.

        Args:
            services: Map of service names to nanobricks
            networks: List of network names
            volumes: Volume configurations

        Returns:
            docker-compose.yml content
        """
        compose = {"version": "3.8", "services": {}}

        # Generate service definitions
        for service_name, brick in services.items():
            service = {
                "build": ".",
                "container_name": f"{service_name}_container",
                "restart": "unless-stopped",
            }

            # Ports
            if self.docker_config.expose_ports:
                service["ports"] = [
                    f"{port}:{port}" for port in self.docker_config.expose_ports
                ]

            # Environment
            if self.docker_config.environment:
                service["environment"] = self.docker_config.environment.copy()

            # Networks
            if networks:
                service["networks"] = networks

            # Volumes
            if volumes and service_name in volumes:
                service["volumes"] = []
                for host_path, container_path in volumes[service_name].items():
                    service["volumes"].append(f"{host_path}:{container_path}")

            # Command override for specific brick
            service["command"] = ["python", "-m", "nanobricks", "run", brick.name]

            compose["services"][service_name] = service

        # Add networks
        if networks:
            compose["networks"] = {net: {"driver": "bridge"} for net in networks}

        # Add named volumes
        if volumes:
            compose["volumes"] = {}
            for service_volumes in volumes.values():
                for volume_name in service_volumes.keys():
                    if not volume_name.startswith("/") and not volume_name.startswith(
                        "."
                    ):
                        compose["volumes"][volume_name] = {}

        import yaml

        self._compose_content = yaml.dump(compose, default_flow_style=False)
        return self._compose_content

    def save_deployment_files(self, output_dir: str | Path = ".") -> None:
        """Save deployment files to directory.

        Args:
            output_dir: Directory to save files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if self._dockerfile_content:
            dockerfile_path = output_path / "Dockerfile"
            dockerfile_path.write_text(self._dockerfile_content)
            print(f"Saved Dockerfile to {dockerfile_path}")

        if self._compose_content:
            compose_path = output_path / "docker-compose.yml"
            compose_path.write_text(self._compose_content)
            print(f"Saved docker-compose.yml to {compose_path}")

        # Save requirements.txt if dependencies specified
        if self.docker_config.dependencies:
            requirements_path = output_path / "requirements.txt"
            requirements_path.write_text("\n".join(self.docker_config.dependencies))
            print(f"Saved requirements.txt to {requirements_path}")


class SkillKubernetes(Skill):
    """Kubernetes deployment skill for nanobricks."""

    def __init__(self, config: KubernetesConfig | None = None):
        """Initialize Kubernetes skill.

        Args:
            config: Kubernetes configuration
        """
        super().__init__()
        self.k8s_config = config or KubernetesConfig()
        self._manifests: dict[str, str] = {}

    def _create_enhanced_brick(
        self, brick: NanobrickProtocol[T_in, T_out, T_deps]
    ) -> NanobrickEnhanced[T_in, T_out, T_deps]:
        """Create enhanced brick with Kubernetes capabilities."""

        class KubernetesEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
                # Just pass through to the wrapped brick
                return await self._wrapped.invoke(input, deps=deps)

            def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out:
                return self._wrapped.invoke_sync(input, deps=deps)

        return KubernetesEnhanced(brick, self)

    def generate_deployment(
        self, brick: NanobrickProtocol, image: str
    ) -> dict[str, Any]:
        """Generate Kubernetes deployment manifest.

        Args:
            brick: Nanobrick to deploy
            image: Docker image name

        Returns:
            Deployment manifest
        """
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{brick.name}-deployment",
                "namespace": self.k8s_config.namespace,
                "labels": {"app": brick.name, **self.k8s_config.labels},
                "annotations": self.k8s_config.annotations,
            },
            "spec": {
                "replicas": self.k8s_config.replicas,
                "selector": {"matchLabels": {"app": brick.name}},
                "template": {
                    "metadata": {
                        "labels": {"app": brick.name, **self.k8s_config.labels}
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": brick.name,
                                "image": image,
                                "ports": [
                                    {"containerPort": self.k8s_config.container_port}
                                ],
                                "resources": self.k8s_config.resources,
                                "env": [],
                            }
                        ]
                    },
                },
            },
        }

        # Add environment variables
        container = deployment["spec"]["template"]["spec"]["containers"][0]

        if self.k8s_config.env_from_configmap:
            container["envFrom"] = container.get("envFrom", [])
            container["envFrom"].append(
                {"configMapRef": {"name": self.k8s_config.env_from_configmap}}
            )

        if self.k8s_config.env_from_secret:
            container["envFrom"] = container.get("envFrom", [])
            container["envFrom"].append(
                {"secretRef": {"name": self.k8s_config.env_from_secret}}
            )

        # Add probes
        if self.k8s_config.liveness_probe:
            container["livenessProbe"] = self.k8s_config.liveness_probe

        if self.k8s_config.readiness_probe:
            container["readinessProbe"] = self.k8s_config.readiness_probe

        return deployment

    def generate_service(self, brick: NanobrickProtocol) -> dict[str, Any]:
        """Generate Kubernetes service manifest.

        Args:
            brick: Nanobrick to expose

        Returns:
            Service manifest
        """
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{brick.name}-service",
                "namespace": self.k8s_config.namespace,
                "labels": {"app": brick.name, **self.k8s_config.labels},
            },
            "spec": {
                "type": self.k8s_config.service_type,
                "selector": {"app": brick.name},
                "ports": [
                    {
                        "port": self.k8s_config.service_port,
                        "targetPort": self.k8s_config.container_port,
                        "protocol": "TCP",
                    }
                ],
            },
        }

    def generate_hpa(self, brick: NanobrickProtocol) -> dict[str, Any] | None:
        """Generate Horizontal Pod Autoscaler manifest.

        Args:
            brick: Nanobrick to autoscale

        Returns:
            HPA manifest if autoscaling configured
        """
        if not self.k8s_config.autoscaling:
            return None

        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{brick.name}-hpa",
                "namespace": self.k8s_config.namespace,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": f"{brick.name}-deployment",
                },
                "minReplicas": self.k8s_config.autoscaling.get("min_replicas", 1),
                "maxReplicas": self.k8s_config.autoscaling.get("max_replicas", 10),
                "metrics": self.k8s_config.autoscaling.get(
                    "metrics",
                    [
                        {
                            "type": "Resource",
                            "resource": {
                                "name": "cpu",
                                "target": {
                                    "type": "Utilization",
                                    "averageUtilization": 80,
                                },
                            },
                        }
                    ],
                ),
            },
        }

    def generate_manifests(
        self, brick: NanobrickProtocol, image: str
    ) -> dict[str, str]:
        """Generate all Kubernetes manifests for a nanobrick.

        Args:
            brick: Nanobrick to deploy
            image: Docker image name

        Returns:
            Map of filename to YAML content
        """
        import yaml

        manifests = {}

        # Deployment
        deployment = self.generate_deployment(brick, image)
        manifests["deployment.yaml"] = yaml.dump(deployment, default_flow_style=False)

        # Service
        service = self.generate_service(brick)
        manifests["service.yaml"] = yaml.dump(service, default_flow_style=False)

        # HPA (if configured)
        hpa = self.generate_hpa(brick)
        if hpa:
            manifests["hpa.yaml"] = yaml.dump(hpa, default_flow_style=False)

        self._manifests = manifests
        return manifests

    def generate_helm_chart(
        self,
        brick: NanobrickProtocol,
        chart_name: str | None = None,
        chart_version: str = "0.1.0",
    ) -> dict[str, str]:
        """Generate Helm chart for a nanobrick.

        Args:
            brick: Nanobrick to package
            chart_name: Helm chart name (defaults to brick name)
            chart_version: Chart version

        Returns:
            Map of file paths to content
        """
        chart_name = chart_name or brick.name
        files = {}

        # Chart.yaml
        files["Chart.yaml"] = yaml.dump(
            {
                "apiVersion": "v2",
                "name": chart_name,
                "description": f"A Helm chart for {brick.name} nanobrick",
                "type": "application",
                "version": chart_version,
                "appVersion": brick.version,
            },
            default_flow_style=False,
        )

        # values.yaml
        files["values.yaml"] = yaml.dump(
            {
                "replicaCount": self.k8s_config.replicas,
                "image": {
                    "repository": f"{brick.name}",
                    "pullPolicy": "IfNotPresent",
                    "tag": brick.version,
                },
                "service": {
                    "type": self.k8s_config.service_type,
                    "port": self.k8s_config.service_port,
                },
                "resources": self.k8s_config.resources,
                "autoscaling": {
                    "enabled": bool(self.k8s_config.autoscaling),
                    "minReplicas": (
                        self.k8s_config.autoscaling.get("min_replicas", 1)
                        if self.k8s_config.autoscaling
                        else 1
                    ),
                    "maxReplicas": (
                        self.k8s_config.autoscaling.get("max_replicas", 10)
                        if self.k8s_config.autoscaling
                        else 10
                    ),
                    "targetCPUUtilizationPercentage": 80,
                },
            },
            default_flow_style=False,
        )

        # Templates
        deployment_template = """
{{- define "nanobrick.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "nanobrick.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "nanobrick.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "nanobrick.fullname" . }}
  labels:
    app.kubernetes.io/name: {{ include "nanobrick.name" . }}
    helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "nanobrick.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include "nanobrick.name" . }}
        app.kubernetes.io/instance: {{ .Release.Name }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.service.port }}
              protocol: TCP
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
"""
        files["templates/deployment.yaml"] = deployment_template.strip()

        service_template = """
apiVersion: v1
kind: Service
metadata:
  name: {{ include "nanobrick.fullname" . }}
  labels:
    app.kubernetes.io/name: {{ include "nanobrick.name" . }}
    helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    app.kubernetes.io/name: {{ include "nanobrick.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
"""
        files["templates/service.yaml"] = service_template.strip()

        if self.k8s_config.autoscaling:
            hpa_template = """
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "nanobrick.fullname" . }}
  labels:
    app.kubernetes.io/name: {{ include "nanobrick.name" . }}
    helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
    app.kubernetes.io/instance: {{ .Release.Name }}
    app.kubernetes.io/managed-by: {{ .Release.Service }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "nanobrick.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
"""
            files["templates/hpa.yaml"] = hpa_template.strip()

        return files

    def save_manifests(self, output_dir: str | Path = ".") -> None:
        """Save Kubernetes manifests to directory.

        Args:
            output_dir: Directory to save files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for filename, content in self._manifests.items():
            file_path = output_path / filename
            file_path.write_text(content)
            print(f"Saved {filename} to {file_path}")
