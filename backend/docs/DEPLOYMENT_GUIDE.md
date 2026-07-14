# Deployment Guide

This guide provides step-by-step instructions for building, deploying, and orchestrating the application.

## Prerequisites

- Docker installed and running.
- Access to a container registry (e.g., Docker Hub, AWS ECR, Google GCR) if deploying to a remote environment.
- `kubectl` installed if using Kubernetes for orchestration.
- `docker-compose` installed if using Docker Compose for local orchestration or simple deployments.

## 1. Building the Docker Image

The application is containerized using Docker. The `Dockerfile` in the root of the `corpus-te` directory defines the build process.

**Steps:**

1.  **Navigate to the `corpus-te` directory:**
    Open your terminal and change to the directory containing the `Dockerfile` and your application code.
    ```bash
    cd /path/to/your/corpus-te
    ```

2.  **Build the Docker image:**
    Use the `docker build` command. Replace `your-image-name:tag` with your desired image name and tag (e.g., `corpus-te-app:latest` or `your-registry/corpus-te-app:v1.0.0`).
    ```bash
    docker build -t your-image-name:tag .
    ```
    *   `-t your-image-name:tag`: Tags the image with a name and optionally a tag.
    *   `.`: Specifies that the build context (the `Dockerfile` and application files) is the current directory.

    This command will execute the steps defined in your `Dockerfile`, including installing dependencies and copying your application code into the image.

## 2. Deploying the Application

Once the Docker image is built, you can deploy the application in various ways.

### A. Running Locally with Docker

For testing or local development:

1.  **Run the Docker container:**
    ```bash
    docker run -d -p 8000:8000 --name my-corpus-te-container your-image-name:tag
    ```
    *   `-d`: Runs the container in detached mode (in the background).
    *   `-p 8000:8000`: Maps port 8000 of the host to port 8000 of the container (as exposed in the `Dockerfile`).
    *   `--name my-corpus-te-container`: Assigns a name to the running container for easier management.
    *   `your-image-name:tag`: The image you built in the previous step.

2.  **Access the application:**
    Open your web browser and go to `http://localhost:8000`.

3.  **View logs (optional):**
    ```bash
    docker logs my-corpus-te-container
    ```

4.  **Stop the container (optional):**
    ```bash
    docker stop my-corpus-te-container
    ```

5.  **Remove the container (optional):**
    ```bash
    docker rm my-corpus-te-container
    ```

### B. Deploying to a Container Registry

To deploy to a cloud provider or share your image, you typically push it to a container registry.

1.  **Log in to your container registry:**
    (Example for Docker Hub)
    ```bash
    docker login
    ```
    For other registries like AWS ECR or Google GCR, follow their specific login instructions.

2.  **Tag your image (if not already tagged with the registry path):**
    If your image name is `corpus-te-app:latest` and your Docker Hub username is `yourusername`, you would tag it as:
    ```bash
    docker tag corpus-te-app:latest yourusername/corpus-te-app:latest
    ```
    Replace `yourusername/corpus-te-app:latest` with `your-registry-url/your-image-name:tag`.

3.  **Push the image to the registry:**
    ```bash
    docker push yourusername/corpus-te-app:latest
    ```
    Replace `yourusername/corpus-te-app:latest` with the fully qualified image name.

### C. Deploying to a Server/Cloud Platform

The exact steps will vary depending on your hosting environment (e.g., a VM, AWS ECS, Google Cloud Run, Azure App Service). Generally, you would:

1.  Ensure Docker is installed on the server.
2.  Pull the image from your container registry:
    ```bash
    docker pull your-registry-url/your-image-name:tag
    ```
3.  Run the container as described in "Running Locally with Docker", adjusting port mappings and environment variables as needed.
    You might use a process manager like `systemd` to manage the Docker container as a service.

## 3. Orchestration

For managing deployments, scaling, and ensuring high availability in production environments, container orchestration tools are recommended.

### A. Docker Compose (Simpler Orchestration / Local Development)

Docker Compose is suitable for defining and running multi-container Docker applications. While your current `Dockerfile` defines a single service, Compose can be useful for managing it alongside other services (like a database or Redis, if they were external to this container).

1.  **Create a `docker-compose.yml` file:**
    In your `corpus-te` directory, create a `docker-compose.yml` file:
    ```yaml
    version: \'\'\'3.8\'\'\' # Or a newer version

    services:
      app:
        image: your-image-name:tag # Or your-registry-url/your-image-name:tag
        build:
          context: .
          dockerfile: Dockerfile # Optional if Dockerfile is in the context root
        ports:
          - "8000:8000"
        # environment:
        #   - DATABASE_URL=your_database_url
        #   - REDIS_URL=your_redis_url
        # volumes:
        #   - .:/app # For development, mounts current directory to /app in container
        restart: unless-stopped
    ```
    *   Replace `your-image-name:tag` with your actual image name.
    *   Uncomment and configure `environment` variables as needed for your application.
    *   The `build` section can be used to build the image if it doesn\'t exist, or you can point `image` to an image already in a registry.

2.  **Start the application using Docker Compose:**
    ```bash
    docker-compose up -d
    ```
    *   `-d`: Runs in detached mode.

3.  **Stop the application:**
    ```bash
    docker-compose down
    ```

### B. Kubernetes (Advanced Orchestration)

Kubernetes (K8s) is a powerful open-source system for automating deployment, scaling, and management of containerized applications.

**Key Concepts:**

*   **Pod:** The smallest deployable unit, can contain one or more containers (your app container).
*   **Deployment:** Manages stateless applications, ensuring a specified number of Pod replicas are running and handles updates.
*   **Service:** Provides a stable network endpoint (IP address and DNS name) to access your application Pods.
*   **Ingress:** Manages external access to the services in a cluster, typically HTTP.
*   **ConfigMap/Secrets:** For managing configuration data and sensitive information.

**General Steps (Simplified):**

1.  **Write Kubernetes Manifest Files (YAML):**
    You\'ll need to create YAML files for `Deployment`, `Service`, and potentially `Ingress`.

    *   **`deployment.yaml` (Example):**
        ```yaml
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: corpus-te-deployment
        spec:
          replicas: 2 # Number of desired instances
          selector:
            matchLabels:
              app: corpus-te
          template:
            metadata:
              labels:
                app: corpus-te
            spec:
              containers:
              - name: corpus-te-app
                image: your-registry-url/your-image-name:tag # Image from your registry
                ports:
                - containerPort: 8000
                # env:
                # - name: DATABASE_URL
                #   value: "your_database_url_from_secret_or_configmap"
        ```

    *   **`service.yaml` (Example - LoadBalancer type for external access):**
        ```yaml
        apiVersion: v1
        kind: Service
        metadata:
          name: corpus-te-service
        spec:
          selector:
            app: corpus-te
          ports:
            - protocol: TCP
              port: 80 # External port
              targetPort: 8000 # Container port
          type: LoadBalancer # Or ClusterIP for internal, NodePort for specific node port
        ```

2.  **Apply the manifests to your Kubernetes cluster:**
    Ensure `kubectl` is configured to point to your cluster.
    ```bash
    kubectl apply -f deployment.yaml
    kubectl apply -f service.yaml
    ```

3.  **Check deployment status:**
    ```bash
    kubectl get deployments
    kubectl get pods
    kubectl get services
    ```

4.  **Access your application:**
    If using `type: LoadBalancer` for the service, Kubernetes will provision an external IP. Find it with `kubectl get services`.

**Further Considerations for Kubernetes:**
*   **Helm:** A package manager for Kubernetes that simplifies deploying and managing applications.
*   **Persistent Storage:** If your application requires persistent storage (e.g., for databases or uploaded files not handled by an external service like Hetzner Storage), you\'ll need to configure PersistentVolumes (PVs) and PersistentVolumeClaims (PVCs).
*   **Monitoring and Logging:** Integrate solutions like Prometheus, Grafana, and an ELK stack (Elasticsearch, Logstash, Kibana) or EFK stack (Elasticsearch, Fluentd, Kibana).
*   **CI/CD:** Set up a CI/CD pipeline (e.g., using Jenkins, GitLab CI, GitHub Actions) to automate building, testing, and deploying your application to Kubernetes.

## 4. Environment Configuration

Your application likely requires configuration (e.g., database URLs, API keys, Redis connection strings).

*   **For Docker run:** Use the `-e` or `--env-file` option.
    ```bash
    docker run -d -p 8000:8000 \
      -e DATABASE_URL="your_db_connection_string" \
      -e REDIS_HOST="your_redis_host" \
      your-image-name:tag
    ```
*   **For Docker Compose:** Use the `environment` section in `docker-compose.yml` or an `.env` file.
*   **For Kubernetes:** Use `ConfigMaps` for non-sensitive data and `Secrets` for sensitive data. These can be mounted as environment variables or files into your Pods.

    Your `Dockerfile` already sets `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`. Ensure any other necessary environment variables are passed during runtime.

## 5. Database Migrations (Alembic)

Your project includes Alembic for database migrations (`alembic.ini`, `alembic/` directory). Migrations should typically be run as part of your deployment process, *before* the new application version starts serving traffic, or in a way that ensures compatibility.

**Strategies:**

1.  **Run migrations manually:** Connect to a container or use a one-off task to run `alembic upgrade head`.
2.  **Entrypoint script:** Modify your Docker image\'s entrypoint to run migrations before starting the Gunicorn server. This is common but can be problematic if multiple instances start simultaneously.
3.  **Kubernetes Init Container:** Use an Init Container in your Kubernetes Pod definition to run migrations before the main application container starts. This is a robust approach.
4.  **Dedicated migration job:** Run migrations as a separate job in your CI/CD pipeline or orchestration platform.

**Example command to run migrations (assuming your app is configured to find `alembic.ini`):**
```bash
alembic upgrade head
```
You might need to execute this within the context of your running application environment (e.g., inside the Docker container or a Kubernetes pod with the correct environment variables set for database connection).

---

This guide provides a general overview. Adapt these steps to your specific infrastructure and requirements.
