"""Example demonstrating deployment skills for nanobricks.

Shows how to containerize nanobricks with Docker and deploy to Kubernetes.
"""

import asyncio
from pathlib import Path
import tempfile

from nanobricks.protocol import NanobrickBase
from nanobricks.skills.deployment import (
    SkillDocker, SkillKubernetes, DockerConfig, KubernetesConfig
)
from nanobricks.skills.api import SkillApi
from nanobricks.validators.schema_validator import SchemaValidator
from nanobricks.transformers.json_transformer import JSONSerializer


# Example nanobricks to deploy

class DataProcessor(NanobrickBase[dict[str, any], dict[str, any], None]):
    """Process incoming data and add metadata."""
    
    def __init__(self):
        self.name = "data_processor"
        self.version = "1.0.0"
    
    async def invoke(self, input: dict[str, any], *, deps: None = None) -> dict[str, any]:
        import time
        return {
            **input,
            "processed_at": time.time(),
            "processor_version": self.version,
            "status": "processed"
        }


class MetricsCollector(NanobrickBase[dict[str, any], dict[str, float], None]):
    """Collect metrics from processed data."""
    
    def __init__(self):
        self.name = "metrics_collector"
        self.version = "1.0.0"
    
    async def invoke(self, input: dict[str, any], *, deps: None = None) -> dict[str, float]:
        # Mock metrics calculation
        return {
            "processing_time": 0.123,
            "data_size": len(str(input)),
            "success_rate": 0.99,
            "throughput": 1000.0
        }


def example_basic_docker_deployment():
    """Example: Basic Docker deployment."""
    print("\n=== Basic Docker Deployment Example ===")
    
    # Create a nanobrick
    processor = DataProcessor()
    
    # Apply Docker skill
    docker_skill = SkillDocker()
    
    # Generate Dockerfile
    dockerfile = docker_skill.generate_dockerfile(processor)
    print("\nGenerated Dockerfile:")
    print("-" * 50)
    print(dockerfile)
    print("-" * 50)


def example_docker_with_api():
    """Example: Docker deployment with API endpoint."""
    print("\n=== Docker + API Deployment Example ===")
    
    # Create processor with API skill
    processor = DataProcessor()
    api_skill = SkillApi({
        "port": 8080,
        "docs": True
    })
    processor_with_api = api_skill.enhance(processor)
    
    # Configure Docker with API requirements
    docker_config = DockerConfig(
        base_image="python:3.13-slim",
        expose_ports=[8080],
        environment={
            "API_HOST": "0.0.0.0",
            "API_PORT": "8080",
            "LOG_LEVEL": "info"
        },
        dependencies=[
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "nanobricks>=1.0.0"
        ],
        healthcheck={
            "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
            "interval": "30s",
            "timeout": "10s",
            "retries": 3
        }
    )
    
    docker_skill = SkillDocker(docker_config)
    dockerfile = docker_skill.generate_dockerfile(processor_with_api)
    
    print("\nDockerfile with API configuration:")
    print("-" * 50)
    print(dockerfile[:500] + "..." if len(dockerfile) > 500 else dockerfile)
    print("-" * 50)


def example_docker_compose_multi_service():
    """Example: Multi-service deployment with docker-compose."""
    print("\n=== Docker Compose Multi-Service Example ===")
    
    # Create multiple nanobricks
    processor = DataProcessor()
    metrics = MetricsCollector()
    
    # Configure Docker
    docker_config = DockerConfig(
        expose_ports=[8080, 9090],
        environment={
            "SERVICE_NAME": "${SERVICE_NAME}",
            "LOG_LEVEL": "info"
        }
    )
    
    docker_skill = SkillDocker(docker_config)
    
    # Generate docker-compose.yml
    services = {
        "processor": processor,
        "metrics": metrics
    }
    
    compose_yaml = docker_skill.generate_compose(
        services,
        networks=["microservices"],
        volumes={
            "processor": {"./data": "/app/data", "processor_logs": "/app/logs"},
            "metrics": {"metrics_data": "/app/metrics"}
        }
    )
    
    print("\nGenerated docker-compose.yml:")
    print("-" * 50)
    print(compose_yaml)
    print("-" * 50)


def example_kubernetes_basic():
    """Example: Basic Kubernetes deployment."""
    print("\n=== Basic Kubernetes Deployment Example ===")
    
    # Create nanobrick
    processor = DataProcessor()
    
    # Configure Kubernetes
    k8s_config = KubernetesConfig(
        namespace="default",
        replicas=3,
        service_port=80,
        container_port=8080,
        resources={
            "limits": {"cpu": "500m", "memory": "256Mi"},
            "requests": {"cpu": "100m", "memory": "128Mi"}
        }
    )
    
    k8s_skill = SkillKubernetes(k8s_config)
    
    # Generate deployment
    deployment = k8s_skill.generate_deployment(processor, "data-processor:v1.0.0")
    
    print("\nKubernetes Deployment:")
    print("-" * 50)
    import yaml
    print(yaml.dump(deployment, default_flow_style=False))
    
    # Generate service
    service = k8s_skill.generate_service(processor)
    
    print("\nKubernetes Service:")
    print("-" * 50)
    print(yaml.dump(service, default_flow_style=False))


def example_kubernetes_production():
    """Example: Production-ready Kubernetes deployment."""
    print("\n=== Production Kubernetes Deployment Example ===")
    
    # Create nanobrick with API
    processor = DataProcessor()
    api_skill = SkillApi({"port": 8080, "docs": True})
    processor_with_api = api_skill.enhance(processor)
    
    # Production Kubernetes config
    k8s_config = KubernetesConfig(
        namespace="production",
        replicas=5,
        service_type="LoadBalancer",
        service_port=443,
        container_port=8080,
        resources={
            "limits": {"cpu": "1", "memory": "512Mi"},
            "requests": {"cpu": "200m", "memory": "256Mi"}
        },
        labels={
            "app": "data-processor",
            "environment": "production",
            "team": "backend"
        },
        annotations={
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "8080",
            "prometheus.io/path": "/metrics"
        },
        env_from_configmap="app-config",
        env_from_secret="app-secrets",
        liveness_probe={
            "httpGet": {
                "path": "/health",
                "port": 8080
            },
            "initialDelaySeconds": 30,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "failureThreshold": 3
        },
        readiness_probe={
            "httpGet": {
                "path": "/health",
                "port": 8080
            },
            "initialDelaySeconds": 5,
            "periodSeconds": 5,
            "timeoutSeconds": 3,
            "successThreshold": 1
        },
        autoscaling={
            "min_replicas": 3,
            "max_replicas": 20,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": 70
                        }
                    }
                },
                {
                    "type": "Resource",
                    "resource": {
                        "name": "memory",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": 80
                        }
                    }
                }
            ]
        }
    )
    
    k8s_skill = SkillKubernetes(k8s_config)
    
    # Generate all manifests
    manifests = k8s_skill.generate_manifests(processor_with_api, "data-processor:v1.0.0")
    
    print("\nGenerated Kubernetes manifests:")
    for filename, content in manifests.items():
        print(f"\n--- {filename} ---")
        print(content[:300] + "..." if len(content) > 300 else content)


def example_helm_chart():
    """Example: Generate Helm chart for nanobrick."""
    print("\n=== Helm Chart Generation Example ===")
    
    # Create nanobrick
    processor = DataProcessor()
    
    # Configure Kubernetes with Helm-friendly defaults
    k8s_config = KubernetesConfig(
        replicas=2,
        autoscaling={
            "min_replicas": 2,
            "max_replicas": 10
        }
    )
    
    k8s_skill = SkillKubernetes(k8s_config)
    
    # Generate Helm chart
    helm_files = k8s_skill.generate_helm_chart(
        processor,
        chart_name="data-processor",
        chart_version="1.0.0"
    )
    
    print("\nGenerated Helm chart files:")
    for filepath, content in helm_files.items():
        print(f"\n--- {filepath} ---")
        if filepath.endswith(".yaml"):
            # Show first 20 lines for YAML files
            lines = content.split('\n')
            preview = '\n'.join(lines[:20])
            if len(lines) > 20:
                preview += f"\n... ({len(lines) - 20} more lines)"
            print(preview)
        else:
            print(content[:300] + "..." if len(content) > 300 else content)


def example_complete_deployment_pipeline():
    """Example: Complete deployment pipeline from code to Kubernetes."""
    print("\n=== Complete Deployment Pipeline Example ===")
    
    # Step 1: Create a data processing pipeline
    validator = SchemaValidator({"data": dict, "type": str}, required_fields=["data"])
    processor = DataProcessor()
    serializer = JSONSerializer(indent=2)
    
    # Compose pipeline
    pipeline = validator | processor | serializer
    pipeline.name = "data_pipeline"
    pipeline.version = "1.0.0"
    
    # Step 2: Add API capability
    api_skill = SkillApi({
        "port": 8080,
        "docs": True
    })
    pipeline_with_api = api_skill.enhance(pipeline)
    
    # Step 3: Create Docker deployment
    docker_config = DockerConfig(
        base_image="python:3.13-slim",
        expose_ports=[8080],
        environment={
            "API_HOST": "0.0.0.0",
            "API_PORT": "8080",
            "WORKERS": "4"
        },
        dependencies=[
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
            "prometheus-client>=0.19.0",
            "nanobricks>=1.0.0"
        ],
        system_packages=["curl"],
        healthcheck={
            "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
            "interval": "30s"
        }
    )
    
    docker_skill = SkillDocker(docker_config)
    
    # Step 4: Create Kubernetes deployment
    k8s_config = KubernetesConfig(
        namespace="production",
        replicas=3,
        service_type="LoadBalancer",
        autoscaling={
            "min_replicas": 2,
            "max_replicas": 10
        }
    )
    
    k8s_skill = SkillKubernetes(k8s_config)
    
    print("\n1. Pipeline created with composition:")
    print(f"   {validator.name} | {processor.name} | {serializer.name}")
    
    print("\n2. API endpoint added at port 8080")
    
    print("\n3. Docker configuration:")
    print(f"   - Base image: {docker_config.base_image}")
    print(f"   - Exposed ports: {docker_config.expose_ports}")
    print(f"   - Health check enabled")
    
    print("\n4. Kubernetes configuration:")
    print(f"   - Namespace: {k8s_config.namespace}")
    print(f"   - Initial replicas: {k8s_config.replicas}")
    print(f"   - Autoscaling: {k8s_config.autoscaling['min_replicas']}-{k8s_config.autoscaling['max_replicas']}")
    
    # Generate deployment artifacts
    print("\n5. Generating deployment artifacts...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        deploy_dir = Path(tmpdir) / "deploy"
        deploy_dir.mkdir()
        
        # Docker files
        docker_dir = deploy_dir / "docker"
        docker_skill.generate_dockerfile(pipeline_with_api)
        docker_skill.save_deployment_files(docker_dir)
        
        # Kubernetes files
        k8s_dir = deploy_dir / "kubernetes"
        k8s_skill.generate_manifests(pipeline_with_api, "data-pipeline:v1.0.0")
        k8s_skill.save_manifests(k8s_dir)
        
        # Helm chart
        helm_dir = deploy_dir / "helm"
        helm_files = k8s_skill.generate_helm_chart(pipeline_with_api)
        helm_dir.mkdir()
        for filepath, content in helm_files.items():
            file_path = helm_dir / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
        
        print(f"\n   Deployment artifacts saved to: {deploy_dir}")
        print("\n   Directory structure:")
        for path in sorted(deploy_dir.rglob("*")):
            if path.is_file():
                indent = "   " * (len(path.relative_to(deploy_dir).parts))
                print(f"   {indent}{path.name}")
    
    print("\n6. Deployment commands:")
    print("   # Build Docker image")
    print("   docker build -t data-pipeline:v1.0.0 ./deploy/docker")
    print("\n   # Run with Docker Compose")
    print("   docker-compose -f ./deploy/docker/docker-compose.yml up")
    print("\n   # Deploy to Kubernetes") 
    print("   kubectl apply -f ./deploy/kubernetes/")
    print("\n   # Deploy with Helm")
    print("   helm install data-pipeline ./deploy/helm/")


def main():
    """Run all deployment examples."""
    example_basic_docker_deployment()
    example_docker_with_api()
    example_docker_compose_multi_service()
    example_kubernetes_basic()
    example_kubernetes_production()
    example_helm_chart()
    example_complete_deployment_pipeline()


if __name__ == "__main__":
    main()