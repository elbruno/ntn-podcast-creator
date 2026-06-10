# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the NTN Podcast Creator project.

## Workflows

### 1. Run Unit Tests (`run-tests.yml`)

**Purpose**: Automatically run all unit tests when code changes are detected.

**Triggers**:
- Push to `main` or `master` branches
- Pull requests to `main` or `master` branches
- Manual workflow dispatch

**What it does**:
1. Checks out the repository code
2. Sets up Python 3.12
3. Installs system dependencies (FFmpeg)
4. Installs Python dependencies from `requirements.txt`
5. Installs Playwright browsers (Chromium)
6. Runs all tests in `tests/` directory using pytest

**Test Types Included**:
- Unit tests (`test_units.py`) - Core functionality
- Playwright UI tests (`test_ui_playwright.py`) - Browser-based UI testing
- Structure verification tests (`test_playwright_structure.py`) - Quick validation
- Integration tests (various other test files)

**Usage**:
The workflow runs automatically on push/PR. You can also trigger it manually:
1. Go to the Actions tab in GitHub
2. Select "Run Unit Tests" workflow
3. Click "Run workflow"

**Requirements**:
- Tests must pass for the workflow to succeed
- FFmpeg must be available for audio processing tests
- Playwright browsers must be installed for UI tests

**Exit Codes**:
- `0`: All tests passed
- `1`: One or more tests failed

**Viewing Results**:
- Check the Actions tab in GitHub to see test results
- Failed tests will show detailed error messages
- Each test step is logged separately

### 2. Build and Publish Docker Image (`docker-publish.yml`)

**Purpose**: Build and publish Docker images to Docker Hub.

**Triggers**:
- Release published
- Manual workflow dispatch

**What it does**:
1. Builds multi-platform Docker images (amd64, arm64)
2. Pushes to Docker Hub
3. Updates Docker Hub description

See `docker-publish.yml` for details.

## Adding New Workflows

To add a new workflow:

1. Create a new `.yml` file in `.github/workflows/`
2. Define the workflow name, triggers, and jobs
3. Add necessary steps and actions
4. Commit and push to trigger the workflow

Example structure:
```yaml
name: My Workflow
on:
  push:
    branches: [ "main" ]
jobs:
  my-job:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Run my task
      run: echo "Hello World"
```

## Best Practices

1. **Fast Feedback**: Keep test runs under 10 minutes when possible
2. **Fail Fast**: Use `pytest -x` to stop on first failure
3. **Parallel Testing**: Use `pytest-xdist` for parallel test execution
4. **Caching**: Consider caching dependencies to speed up workflow
5. **Environment Variables**: Use secrets for sensitive data
6. **Matrix Testing**: Test across multiple Python versions if needed

## Troubleshooting

**Workflow fails to start**:
- Check YAML syntax with `yamllint` or online validator
- Verify branch names in trigger configuration

**Tests fail in CI but pass locally**:
- Check Python version matches (3.12 in workflow)
- Verify all dependencies are in `requirements.txt`
- Check for environment-specific issues (paths, permissions)

**Playwright tests timeout**:
- Increase timeout in test configuration
- Check if app starts successfully
- Verify browser installation step completes

**FFmpeg not found**:
- Ensure system dependencies step runs successfully
- Check if FFmpeg is in PATH

## Contributing

When adding new tests:
1. Ensure they work locally first
2. Add them to the appropriate test file
3. Update test documentation
4. Verify workflow runs successfully after push

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/python/)
