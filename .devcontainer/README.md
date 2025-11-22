# Dev Container Configuration

This directory contains the Dev Container configuration for the NTN Podcast Creator project.

## What is a Dev Container?

A development container (or dev container for short) allows you to use a container as a full-featured development environment. It can be used to run an application, to separate tools, libraries, or runtimes needed for working with a codebase, and to aid in continuous integration and testing.

## Features

This dev container includes:

- **Python 3.12**: Latest Python runtime
- **FFmpeg**: Pre-installed for audio processing
- **VS Code Extensions**: 
  - Python language support
  - Pylance (type checking and IntelliSense)
  - Black formatter
  - Ruff linter
- **Port Forwarding**: Automatically forwards port 7860 for the Gradio UI
- **Auto-install**: Dependencies from `requirements.txt` are automatically installed

## Using the Dev Container

### Prerequisites

- [Visual Studio Code](https://code.visualstudio.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code

### Getting Started

1. **Open in VS Code**
   ```bash
   code .
   ```

2. **Reopen in Container**
   - Press `F1` or `Ctrl+Shift+P` (Windows/Linux) / `Cmd+Shift+P` (Mac)
   - Type "Dev Containers: Reopen in Container"
   - Select the command and wait for the container to build

3. **Start the Application**
   Once the container is ready, open a terminal in VS Code and run:
   ```bash
   python app.py
   ```

4. **Access the UI**
   - VS Code will automatically forward port 7860
   - Click the notification or go to http://127.0.0.1:7860 in your browser

## What Gets Installed

The dev container automatically:

1. Installs FFmpeg (required for audio processing)
2. Installs all Python dependencies from `requirements.txt`
3. Sets up Python development tools and extensions
4. Configures code formatting and linting

## Customization

You can customize the dev container by editing `.devcontainer/devcontainer.json`:

- Add more VS Code extensions in the `extensions` array
- Change Python version by updating the `image` property
- Add additional tools in the `postCreateCommand`
- Configure additional ports in the `forwardPorts` array

## Troubleshooting

### Container won't start
- Ensure Docker is running
- Try rebuilding the container: `F1` → "Dev Containers: Rebuild Container"

### Port 7860 is not accessible
- Check that the port is forwarded in the Ports view (bottom panel in VS Code)
- Ensure no other application is using port 7860

### Dependencies not installed
- Rebuild the container to re-run `postCreateCommand`
- Or manually run: `pip install -r requirements.txt`

## Learn More

- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container Specification](https://containers.dev/)
