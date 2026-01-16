# GitHub Actions CI/CD Pipeline Configuration

This directory contains the GitHub Actions workflow for automated testing, validation, and deployment.

## Workflow Files

- `ci-cd.yml`: Main CI/CD pipeline that runs on PRs and pushes

## Workflow Jobs

### 1. Linting and Formatting
- Runs ruff check for linting
- Runs ruff format for formatting verification
- Checks for print statements in source code
- Caches dependencies for performance

### 2. Type Checking
- Runs mypy for static type checking
- Ensures all type annotations are correct

### 3. Test Suite
- Runs pytest on multiple Python versions (3.11, 3.12, 3.13)
- Generates coverage reports
- Uploads coverage to Codecov
- Caches dependencies per Python version

### 4. Security Scan
- Runs bandit for security vulnerability scanning
- Runs safety to check for known vulnerable dependencies
- Uploads security reports as artifacts

### 5. Build Package
- Builds the package using `uv build`
- Validates package with `twine check`
- Uploads build artifacts

### 6. Documentation
- Builds documentation
- Uploads documentation artifacts

### 7. Auto-merge
- **Only runs on PRs**
- Checks conditions:
  - PR is from trusted user (olekslitus)
  - PR has at least 1 approval
  - PR is from same repository (not fork)
- If conditions met: Auto-merges with squash
- If from trusted user but no approval: Requests review

### 8. Deploy
- **Only runs on main branch pushes**
- Deploys to PyPI if tagged
- Creates GitHub releases for tags
- Deploys documentation

### 9. Notify
- Comments on PRs with CI/CD status
- Provides summary of all job results
- Updates existing comments or creates new ones

## Triggers

- **Push to main/develop**: Runs full pipeline
- **Pull Request**: Runs all jobs except deploy
- **Manual**: Can be triggered manually

## Required Secrets

For full functionality, these GitHub repository secrets are needed:

- `PYPI_TOKEN`: For publishing to PyPI
- (Optional) Other deployment tokens

## Auto-merge Policy

The auto-merge job follows a safe approach:
1. Only merges from trusted users
2. Requires at least one approval
3. Only works for same-repo PRs (no forks)
4. Uses squash merge to keep history clean

This ensures code quality while maintaining security.