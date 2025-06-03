"""Tests for deployment skills."""

import tempfile
from pathlib import Path

import yaml

from nanobricks.protocol import NanobrickBase
from nanobricks.skills.deployment import (
    DockerConfig,
    KubernetesConfig,
    SkillDocker,
    SkillKubernetes,
)


class Nanobrick(NanobrickBase[str, str, None]):
    """Simple test nanobrick."""

    def __init__(self):
        self.name = "simple_brick"
        self.version = "1.0.0"

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return f"Processed: {input}"


class TestSkillDocker:
    """Test Docker deployment skill."""

    def test_basic_dockerfile_generation(self):
        """Test basic Dockerfile generation."""
        skill = SkillDocker()
        brick = Nanobrick()

        dockerfile = skill.generate_dockerfile(brick)

        assert "FROM python:3.13-slim" in dockerfile
        assert "WORKDIR /app" in dockerfile
        assert 'CMD ["python", "-m", "nanobricks", "run", "simple_brick"]' in dockerfile

    def test_dockerfile_with_config(self):
        """Test Dockerfile generation with custom config."""
        config = DockerConfig(
            base_image="python:3.12-alpine",
            working_dir="/application",
            expose_ports=[8080, 9090],
            environment={"API_KEY": "secret", "DEBUG": "true"},
            dependencies=["fastapi", "uvicorn"],
            system_packages=["curl", "git"],
            labels={"maintainer": "test@example.com", "version": "1.0"},
            healthcheck={
                "test": ["CMD", "wget", "--spider", "http://localhost:8080/health"],
                "interval": "60s",
                "timeout": "5s",
                "retries": 5,
            },
            user="appuser",
        )

        skill = SkillDocker(config)
        brick = Nanobrick()

        dockerfile = skill.generate_dockerfile(brick)

        assert "FROM python:3.12-alpine" in dockerfile
        assert "WORKDIR /application" in dockerfile
        assert "EXPOSE 8080" in dockerfile
        assert "EXPOSE 9090" in dockerfile
        assert "ENV API_KEY=secret" in dockerfile
        assert "ENV DEBUG=true" in dockerfile
        assert "RUN apt-get update && apt-get install -y" in dockerfile
        assert "curl" in dockerfile
        assert "git" in dockerfile
        assert 'LABEL maintainer="test@example.com"' in dockerfile
        assert "USER appuser" in dockerfile
        assert "HEALTHCHECK --interval=60s --timeout=5s --retries=5" in dockerfile
        assert "requirements.txt" in dockerfile

    def test_docker_compose_generation(self):
        """Test docker-compose.yml generation."""
        skill = SkillDocker(DockerConfig(expose_ports=[8080]))

        brick1 = Nanobrick()
        brick2 = Nanobrick()
        brick2.name = "another_brick"

        services = {"service1": brick1, "service2": brick2}

        compose_yaml = skill.generate_compose(
            services,
            networks=["app_network"],
            volumes={"service1": {"./data": "/data"}},
        )

        compose = yaml.safe_load(compose_yaml)

        assert compose["version"] == "3.8"
        assert "service1" in compose["services"]
        assert "service2" in compose["services"]

        service1 = compose["services"]["service1"]
        assert service1["build"] == "."
        assert service1["container_name"] == "service1_container"
        assert service1["restart"] == "unless-stopped"
        assert service1["ports"] == ["8080:8080"]
        assert service1["networks"] == ["app_network"]
        assert service1["volumes"] == ["./data:/data"]
        assert service1["command"] == [
            "python",
            "-m",
            "nanobricks",
            "run",
            "simple_brick",
        ]

        assert "app_network" in compose["networks"]

    def test_save_deployment_files(self):
        """Test saving deployment files."""
        config = DockerConfig(dependencies=["fastapi", "uvicorn"])
        skill = SkillDocker(config)
        brick = Nanobrick()

        # Generate files
        skill.generate_dockerfile(brick)
        skill.generate_compose({"app": brick})

        with tempfile.TemporaryDirectory() as tmpdir:
            skill.save_deployment_files(tmpdir)

            # Check files exist
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            compose_path = Path(tmpdir) / "docker-compose.yml"
            requirements_path = Path(tmpdir) / "requirements.txt"

            assert dockerfile_path.exists()
            assert compose_path.exists()
            assert requirements_path.exists()

            # Check requirements content
            requirements = requirements_path.read_text()
            assert "fastapi" in requirements
            assert "uvicorn" in requirements


class TestSkillKubernetes:
    """Test Kubernetes deployment skill."""

    def test_basic_deployment_generation(self):
        """Test basic Kubernetes deployment generation."""
        skill = SkillKubernetes()
        brick = Nanobrick()

        deployment = skill.generate_deployment(brick, "myapp:latest")

        assert deployment["apiVersion"] == "apps/v1"
        assert deployment["kind"] == "Deployment"
        assert deployment["metadata"]["name"] == "simple_brick-deployment"
        assert deployment["spec"]["replicas"] == 1

        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert container["name"] == "simple_brick"
        assert container["image"] == "myapp:latest"
        assert container["ports"][0]["containerPort"] == 8080

    def test_deployment_with_config(self):
        """Test deployment with custom config."""
        config = KubernetesConfig(
            namespace="production",
            replicas=3,
            container_port=3000,
            resources={
                "limits": {"cpu": "2", "memory": "1Gi"},
                "requests": {"cpu": "500m", "memory": "256Mi"},
            },
            labels={"team": "backend", "env": "prod"},
            annotations={"prometheus.io/scrape": "true"},
            env_from_configmap="app-config",
            env_from_secret="app-secrets",
            liveness_probe={
                "httpGet": {"path": "/health", "port": 3000},
                "initialDelaySeconds": 30,
                "periodSeconds": 10,
            },
            readiness_probe={
                "httpGet": {"path": "/ready", "port": 3000},
                "initialDelaySeconds": 5,
                "periodSeconds": 5,
            },
        )

        skill = SkillKubernetes(config)
        brick = Nanobrick()

        deployment = skill.generate_deployment(brick, "myapp:v2")

        assert deployment["metadata"]["namespace"] == "production"
        assert deployment["spec"]["replicas"] == 3
        assert deployment["metadata"]["labels"]["team"] == "backend"
        assert deployment["metadata"]["annotations"]["prometheus.io/scrape"] == "true"

        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert container["ports"][0]["containerPort"] == 3000
        assert container["resources"]["limits"]["cpu"] == "2"
        assert container["livenessProbe"]["httpGet"]["path"] == "/health"
        assert container["readinessProbe"]["httpGet"]["path"] == "/ready"

        # Check env references
        env_from = container["envFrom"]
        assert len(env_from) == 2
        assert env_from[0]["configMapRef"]["name"] == "app-config"
        assert env_from[1]["secretRef"]["name"] == "app-secrets"

    def test_service_generation(self):
        """Test Kubernetes service generation."""
        config = KubernetesConfig(
            service_type="LoadBalancer", service_port=80, container_port=8080
        )
        skill = SkillKubernetes(config)
        brick = Nanobrick()

        service = skill.generate_service(brick)

        assert service["apiVersion"] == "v1"
        assert service["kind"] == "Service"
        assert service["metadata"]["name"] == "simple_brick-service"
        assert service["spec"]["type"] == "LoadBalancer"
        assert service["spec"]["ports"][0]["port"] == 80
        assert service["spec"]["ports"][0]["targetPort"] == 8080

    def test_hpa_generation(self):
        """Test HPA generation."""
        config = KubernetesConfig(
            autoscaling={
                "min_replicas": 2,
                "max_replicas": 20,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {"type": "Utilization", "averageUtilization": 70},
                        },
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {"type": "Utilization", "averageUtilization": 80},
                        },
                    },
                ],
            }
        )
        skill = SkillKubernetes(config)
        brick = Nanobrick()

        hpa = skill.generate_hpa(brick)

        assert hpa is not None
        assert hpa["apiVersion"] == "autoscaling/v2"
        assert hpa["kind"] == "HorizontalPodAutoscaler"
        assert hpa["spec"]["minReplicas"] == 2
        assert hpa["spec"]["maxReplicas"] == 20
        assert len(hpa["spec"]["metrics"]) == 2

    def test_no_hpa_without_config(self):
        """Test no HPA generated without autoscaling config."""
        skill = SkillKubernetes()
        brick = Nanobrick()

        hpa = skill.generate_hpa(brick)
        assert hpa is None

    def test_generate_all_manifests(self):
        """Test generating all manifests."""
        config = KubernetesConfig(autoscaling={"min_replicas": 1, "max_replicas": 5})
        skill = SkillKubernetes(config)
        brick = Nanobrick()

        manifests = skill.generate_manifests(brick, "myapp:latest")

        assert "deployment.yaml" in manifests
        assert "service.yaml" in manifests
        assert "hpa.yaml" in manifests

        # Verify YAML is valid
        deployment = yaml.safe_load(manifests["deployment.yaml"])
        assert deployment["kind"] == "Deployment"

        service = yaml.safe_load(manifests["service.yaml"])
        assert service["kind"] == "Service"

        hpa = yaml.safe_load(manifests["hpa.yaml"])
        assert hpa["kind"] == "HorizontalPodAutoscaler"

    def test_helm_chart_generation(self):
        """Test Helm chart generation."""
        skill = SkillKubernetes()
        brick = Nanobrick()

        files = skill.generate_helm_chart(brick, "my-chart", "1.0.0")

        assert "Chart.yaml" in files
        assert "values.yaml" in files
        assert "templates/deployment.yaml" in files
        assert "templates/service.yaml" in files

        # Verify Chart.yaml
        chart = yaml.safe_load(files["Chart.yaml"])
        assert chart["name"] == "my-chart"
        assert chart["version"] == "1.0.0"
        assert chart["appVersion"] == "1.0.0"

        # Verify values.yaml
        values = yaml.safe_load(files["values.yaml"])
        assert values["replicaCount"] == 1
        assert values["image"]["repository"] == "simple_brick"
        assert values["service"]["type"] == "ClusterIP"

    def test_save_manifests(self):
        """Test saving Kubernetes manifests."""
        skill = SkillKubernetes()
        brick = Nanobrick()

        skill.generate_manifests(brick, "myapp:latest")

        with tempfile.TemporaryDirectory() as tmpdir:
            skill.save_manifests(tmpdir)

            # Check files exist
            deployment_path = Path(tmpdir) / "deployment.yaml"
            service_path = Path(tmpdir) / "service.yaml"

            assert deployment_path.exists()
            assert service_path.exists()

            # Verify content
            deployment = yaml.safe_load(deployment_path.read_text())
            assert deployment["kind"] == "Deployment"
