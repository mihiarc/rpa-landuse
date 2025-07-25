# Pull Request

## Description

Brief description of the changes in this PR.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring (no functional changes)
- [ ] Test coverage improvement
- [ ] CI/CD improvement

## Related Issues

- Fixes #(issue number)
- Relates to #(issue number)

## Changes Made

### Core Changes
- [ ] List of main changes
- [ ] Key functionality added/modified
- [ ] Breaking changes (if any)

### Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] Performance testing completed (if applicable)

### Documentation
- [ ] Code comments updated
- [ ] README updated (if applicable)
- [ ] CLAUDE.md updated (if applicable)
- [ ] API documentation updated (if applicable)
- [ ] User guide updated (if applicable)

## Testing

### Automated Tests
```bash
# Commands used to test the changes
uv run python -m pytest tests/
uv run python -m pytest tests/integration/
```

### Manual Testing
- [ ] Streamlit dashboard functionality
- [ ] Natural language agent queries
- [ ] Database operations
- [ ] Bulk loading operations
- [ ] Error handling scenarios

### Test Results
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Test coverage maintained/improved
- [ ] Performance tests pass (if applicable)

## Performance Impact

- [ ] No performance impact
- [ ] Performance improvement (provide metrics)
- [ ] Minor performance regression (justified)
- [ ] Performance testing completed

### Performance Metrics (if applicable)
```
Before: X operations/second
After:  Y operations/second
Improvement: Z%
```

## Security Considerations

- [ ] No security implications
- [ ] Security review completed
- [ ] No sensitive data exposed
- [ ] Input validation added/updated
- [ ] Authentication/authorization considered

## Deployment Notes

- [ ] No special deployment considerations
- [ ] Database migrations required
- [ ] Configuration changes required
- [ ] Environment variable changes required
- [ ] Dependencies updated

### Migration Steps (if applicable)
1. Step 1
2. Step 2
3. Step 3

## Screenshots (if applicable)

<!-- Add screenshots to help explain your changes -->

## Checklist

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Code is self-documenting or well-commented
- [ ] No debugging code left in
- [ ] Error handling is appropriate

### Dependencies
- [ ] No new dependencies added
- [ ] New dependencies are justified and documented
- [ ] Dependency versions are pinned appropriately
- [ ] License compatibility checked

### Backwards Compatibility
- [ ] No breaking changes
- [ ] Breaking changes are documented and justified
- [ ] Migration guide provided (if applicable)
- [ ] Deprecation warnings added (if applicable)

### Review Readiness
- [ ] PR title is descriptive
- [ ] PR description is complete
- [ ] Commits are atomic and well-described
- [ ] No merge conflicts
- [ ] CI/CD checks pass

## Additional Notes

<!-- Any additional information that reviewers should know -->

## Reviewer Guidance

### Focus Areas
- [ ] Core functionality correctness
- [ ] Performance impact
- [ ] Security implications
- [ ] Code maintainability
- [ ] Test coverage
- [ ] Documentation quality

### Testing Instructions
1. Checkout this branch
2. Run `uv sync` to install dependencies
3. Run specific test commands (listed above)
4. Test specific scenarios:
   - [ ] Scenario 1
   - [ ] Scenario 2
   - [ ] Scenario 3

---

**Definition of Done:**
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] Security considerations addressed
- [ ] Ready for deployment