# CI/CD Pipeline Documentation

This document describes the comprehensive CI/CD pipeline implemented for the landuse project using GitHub Actions.

## Overview

The CI/CD pipeline provides automated testing, security scanning, performance monitoring, documentation building, and release management. It ensures code quality, security, and reliability while enabling rapid development and deployment.

## Pipeline Components

### 1. Continuous Integration (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Matrix Testing:**
- Python 3.11 and 3.12
- Ubuntu Linux environment

**Steps:**
1. **Environment Setup**
   - Checkout code
   - Install Python and uv
   - Cache dependencies for faster builds
   - Install project dependencies

2. **Code Quality Checks**
   - **Linting**: `ruff check` for code style and potential issues
   - **Type Checking**: `mypy` for static type analysis
   - **Security Scan**: `bandit` for security vulnerabilities

3. **Testing**
   - Unit and integration tests with `pytest`
   - Code coverage analysis with minimum 50% threshold
   - Test result artifacts and coverage reports

4. **Artifacts**
   - Coverage reports (HTML and XML)
   - Security scan results
   - Test artifacts

### 2. Security Scanning (`security.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Daily scheduled scans at 2 AM UTC

**Security Checks:**

#### Dependency Scanning
- **Safety**: Check for known vulnerabilities in dependencies
- **pip-audit**: Additional vulnerability scanning
- Reports generated in JSON format

#### Code Analysis
- **Bandit**: Python security linter for common security issues
- **Semgrep**: Advanced static analysis with security rules
- SARIF output for GitHub Security tab integration

#### Secrets Detection
- **TruffleHog**: Scan for committed secrets and credentials
- Verified secrets detection only

#### License Compliance
- **pip-licenses**: Check dependency licenses
- Alert on GPL licenses that might conflict with MIT
- Generate license compatibility reports

### 3. Performance Testing (`performance.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Weekly scheduled runs on Sundays at 3 AM UTC

**Performance Tests:**

#### DuckDB Benchmarking
- Bulk loading performance tests
- Traditional INSERT vs COPY command comparison
- Performance regression detection
- Detailed timing and throughput metrics

#### Memory Profiling
- Memory usage analysis with `memory-profiler`
- Bulk loading memory consumption
- Connection pooling memory efficiency

#### Load Testing
- Concurrent query simulation
- Response time analysis
- Performance threshold monitoring
- Regression detection and alerting

### 4. Documentation (`documentation.yml`)

**Triggers:**
- Push to `main` branch (docs changes)
- Pull requests affecting documentation
- Changes to `docs/`, `mkdocs.yml`, `README.md`, or `CLAUDE.md`

**Documentation Workflow:**

#### Build and Deploy
- **MkDocs Build**: Generate static documentation site
- **Link Checking**: Validate internal and external links
- **GitHub Pages**: Automatic deployment to GitHub Pages

#### Quality Assessment
- **Readability Analysis**: Flesch reading ease scores
- **Writing Quality**: Grammar and style checking
- **Issue Detection**: Find TODO items and broken links
- **PR Comments**: Automated quality reports on pull requests

### 5. Release Management (`release.yml`)

**Triggers:**
- Git tags starting with `v` (e.g., `v1.0.0`)
- Manual workflow dispatch with version input

**Release Process:**

#### Pre-Release Testing
- Full test suite execution
- Minimum 70% code coverage requirement
- All quality checks must pass

#### Build Artifacts
- **Python Package**: Build wheel and source distribution
- **Documentation**: Generate complete documentation site
- **Artifacts**: Upload all build outputs

#### Release Creation
- **GitHub Release**: Automatic release creation
- **Changelog**: Extract relevant changelog sections
- **Assets**: Attach wheel and source distribution
- **Pre-release Detection**: Automatic detection of alpha/beta/rc versions

## Configuration Files

### 1. Dependabot (`dependabot.yml`)

**Automated Dependency Management:**
- **Python Dependencies**: Weekly updates on Mondays
- **GitHub Actions**: Weekly updates on Mondays
- **PR Limits**: 10 for Python, 5 for Actions
- **Automatic Labels**: Dependencies and language tags
- **Team Assignment**: Auto-assign to landuse-team

### 2. Issue Templates

#### Bug Report (`bug_report.yml`)
- Structured bug reporting form
- Environment and reproduction details
- Component and severity classification
- Contact information and additional context

#### Feature Request (`feature_request.yml`)
- Feature suggestion template
- Problem description and proposed solution
- Use case documentation
- Implementation ideas and contribution offers

### 3. Pull Request Template (`pull_request_template.md`)

**Comprehensive PR Checklist:**
- Change type classification
- Related issues linking
- Testing requirements
- Documentation updates
- Performance and security considerations
- Review guidance and focus areas

## Environment Configuration

### Required Environment Variables

**Basic Configuration:**
```bash
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=1000
```

**CI-Specific Variables:**
```bash
# Test environment
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50
```

### Secrets Management

**Required GitHub Secrets:**
- `GITHUB_TOKEN`: Automatic token for releases and actions
- `CODECOV_TOKEN`: For coverage report uploads (optional)

**API Keys (for integration tests):**
- API keys should be stored as GitHub secrets
- Use minimal permissions and test-specific keys
- Rotate keys regularly

## Quality Gates

### Code Quality Standards

**Linting Requirements:**
- **Ruff**: No linting errors allowed
- **Style**: Consistent code formatting
- **Complexity**: Maximum cyclomatic complexity limits

**Type Checking:**
- **MyPy**: Type hints validation (advisory)
- **Coverage**: Gradual improvement of type coverage

### Testing Requirements

**Coverage Thresholds:**
- **Minimum**: 50% for CI (allowing incremental improvement)
- **Target**: 70% for releases
- **Trend**: Must not decrease significantly

**Test Types:**
- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: End-to-end functionality tests
- **Performance Tests**: Regression detection tests

### Security Standards

**Vulnerability Management:**
- **Critical/High**: Must be addressed before merge
- **Medium**: Should be addressed in next release
- **Low**: Can be tracked as technical debt

**Secret Management:**
- **No Secrets**: Never commit secrets to repository
- **Detection**: Automated scanning with TruffleHog
- **Rotation**: Regular API key rotation

## Performance Monitoring

### Benchmark Tracking

**DuckDB Operations:**
- Bulk loading performance metrics
- Query response times
- Memory usage patterns

**Regression Detection:**
- **Thresholds**: 20% performance degradation triggers alert
- **Trending**: Track performance over time
- **Reporting**: Automated performance reports

### Load Testing

**Concurrent Operations:**
- Database connection pooling
- Query execution under load
- Memory usage under stress

**Thresholds:**
- Average response time: < 5 seconds
- Maximum response time: < 10 seconds
- Memory usage: Within system limits

## Deployment Strategy

### Branching Strategy

**Main Branches:**
- `main`: Production-ready code
- `develop`: Integration branch for features

**Feature Branches:**
- `feature/*`: New features and enhancements
- `bugfix/*`: Bug fixes
- `hotfix/*`: Critical production fixes

### Release Process

**Versioning:**
- **Semantic Versioning**: MAJOR.MINOR.PATCH
- **Pre-releases**: alpha, beta, rc suffixes
- **Tags**: Git tags trigger automated releases

**Release Notes:**
- **Automated**: Extract from CHANGELOG.md
- **Manual**: Override with workflow dispatch
- **Assets**: Include built packages and documentation

## Monitoring and Alerting

### GitHub Integration

**Status Checks:**
- All CI workflows must pass for merge
- Security scans must not have critical issues
- Documentation must build successfully

**Notifications:**
- Failed workflows notify team
- Security alerts escalated immediately
- Performance regressions flagged for review

### Artifact Management

**Storage:**
- Test results and coverage reports
- Security scan outputs
- Performance benchmarks
- Documentation builds

**Retention:**
- Artifacts retained for 30 days
- Release assets permanent
- Security reports archived

## Local Development

### Pre-commit Setup

**Install Pre-commit Hooks:**
```bash
# Install pre-commit
uv add --dev pre-commit

# Install hooks
uv run pre-commit install

# Run hooks manually
uv run pre-commit run --all-files
```

**Hook Configuration (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### Testing Locally

**Run Full Test Suite:**
```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests with coverage
uv run python -m pytest tests/ \
  --cov=src \
  --cov-report=html \
  --cov-report=term-missing

# Run specific test categories
uv run python -m pytest tests/unit/
uv run python -m pytest tests/integration/
```

**Performance Testing:**
```bash
# Run DuckDB benchmarks
uv run python -m landuse.converters.performance_benchmark

# Memory profiling
uv run python -m memory_profiler your_script.py
```

**Security Scanning:**
```bash
# Check for vulnerabilities
uv run safety check

# Security linting
uv run bandit -r src/

# License checking
uv run pip-licenses
```

## Troubleshooting

### Common CI Issues

**Test Failures:**
1. Check test logs in GitHub Actions
2. Reproduce locally with same Python version
3. Check for environment-specific issues
4. Verify test data and configuration

**Coverage Drops:**
1. Add tests for new code
2. Remove dead code
3. Check test configuration
4. Review coverage reports

**Security Alerts:**
1. Review Bandit and Safety reports
2. Update vulnerable dependencies
3. Fix code security issues
4. Document risk acceptance if needed

### Performance Issues

**Benchmark Failures:**
1. Check system resources during tests
2. Compare with baseline metrics
3. Profile memory and CPU usage
4. Review algorithm changes

**Memory Leaks:**
1. Use memory profiler for analysis
2. Check connection cleanup
3. Review data structure usage
4. Monitor garbage collection

## Best Practices

### CI/CD Optimization

**Build Speed:**
- Use dependency caching
- Parallel job execution
- Minimal test data sets
- Efficient Docker layers

**Resource Usage:**
- Monitor GitHub Actions minutes
- Optimize workflow triggers
- Use appropriate runner sizes
- Cache dependencies effectively

### Quality Assurance

**Test Strategy:**
- Fast unit tests for rapid feedback
- Comprehensive integration tests
- Performance regression tests
- Security validation tests

**Code Reviews:**
- Automated checks before human review
- Clear PR templates and guidelines
- Focus areas for reviewers
- Definition of done criteria

### Security Practices

**Secret Management:**
- Never commit secrets
- Use GitHub secrets for sensitive data
- Rotate keys regularly
- Principle of least privilege

**Vulnerability Response:**
- Monitor security alerts
- Patch critical issues immediately
- Track and remediate medium/low issues
- Document security decisions

## Future Enhancements

### Planned Improvements

**Advanced Testing:**
- Contract testing for APIs
- Visual regression testing
- End-to-end user journey tests
- Chaos engineering experiments

**Enhanced Security:**
- Container vulnerability scanning
- Infrastructure as Code security
- Runtime security monitoring
- Compliance reporting

**Performance Optimization:**
- Automated performance optimization
- Machine learning for anomaly detection
- Resource usage optimization
- Scalability testing

### Tool Integration

**Potential Additions:**
- SonarQube for code quality
- Snyk for vulnerability scanning
- Lighthouse for web performance
- Terraform for infrastructure

**Monitoring:**
- Application Performance Monitoring (APM)
- Error tracking and alerting
- User analytics and feedback
- Infrastructure monitoring

## Related Documentation

- [Architecture Overview](./architecture.md)
- [Contributing Guide](./contributing.md)
- [Testing Guide](./testing.md)
- [Branding Strategy](./BRANDING_STRATEGY.md)