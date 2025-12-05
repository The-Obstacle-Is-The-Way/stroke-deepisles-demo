# Deployment

The demo is designed to be deployed on Hugging Face Spaces.

## Hugging Face Spaces

1.  **Create a Space**: Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a new Space.
    *   **SDK**: Docker (Recommended for custom dependencies) or Gradio
    *   **Hardware**: GPU is recommended for DeepISLES inference.

2.  **Configure Dockerfile (if using Docker SDK)**:
    Ensure the Dockerfile installs Python 3.11, uv, and pulls the DeepISLES image (or handles it appropriately, though Spaces might restrict running Docker-in-Docker).

    *Note*: Since DeepISLES runs as a Docker container, running it inside a HF Space (which is a container) requires Docker-in-Docker (DinD) or a compatible runtime. If DinD is not supported, you might need to adapt the inference to run directly in the python environment if possible (DeepISLES source code integration instead of Docker wrapper), but this project wraps the Docker image.

    **Standard Deployment (Gradio SDK)**:
    The project includes `app.py` at the root for standard Gradio deployment. However, checking `requirements.txt` or `pyproject.toml` is needed.

    For standard Gradio Spaces, you need to ensure `docker` command is available if you stick to the current architecture. Most HF Spaces do not support running `docker run`.

    **Alternative**: Use a VM (AWS/GCP/Azure) with Docker installed.

## Local Deployment

1.  **Build/Pull**:
    ```bash
    docker pull isleschallenge/deepisles
    ```

2.  **Run App**:
    ```bash
    uv run python -m stroke_deepisles_demo.ui.app
    ```

## Environment Variables

Configure the deployment using environment variables (Secrets in HF Spaces):
-   `STROKE_DEMO_HF_TOKEN`: Read-only token for accessing datasets if private.
-   `STROKE_DEMO_DEEPISLES_USE_GPU`: Set to `false` if deploying on CPU-only instance.
