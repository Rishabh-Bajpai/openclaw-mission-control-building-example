# Contributing Guide

Thank you for your interest in contributing to OpenClaw Mission Control! This guide will help you get started.

## Quick Links

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting Changes](#submitting-changes)
- [Extension Development](#extension-development)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code:

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints and experiences

## Getting Started

### Ways to Contribute

1. **Report Bugs**: Open an issue with bug details
2. **Suggest Features**: Open an issue with feature request
3. **Write Documentation**: Improve docs and tutorials
4. **Fix Issues**: Pick up issues labeled "good first issue"
5. **Add Extensions**: Build new features (see [Extensions Guide](EXTENSIONS_GUIDE.md))
6. **Review PRs**: Help review pull requests

### Before You Start

- Check existing issues to avoid duplicates
- Comment on issues you're working on
- Ask questions in discussions

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- PostgreSQL (optional, SQLite works for dev)

### Fork and Clone

```bash
# Fork on GitHub first, then clone your fork
git clone https://github.com/YOUR_USERNAME/openclaw-mission-control-building-example.git
cd openclaw-mission-control-building-example

# Add upstream remote
git remote add upstream https://github.com/Rishabh-Bajpai/openclaw-mission-control-building-example.git
```

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio httpx black isort mypy

# Setup pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run tests
pytest tests/ -v

# Run with auto-reload
uvicorn app.main:app --reload --port 8002
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Install dev dependencies
npm install --save-dev @types/node eslint prettier

# Copy and configure environment
cp .env.example .env.local

# Run development server
npm run dev

# Run linter
npm run lint

# Run type checker
npm run type-check
```

## Coding Standards

### Python (Backend)

We follow PEP 8 with some modifications:

**Style**:
- Use Black for formatting: `black .`
- Use isort for imports: `isort .`
- Line length: 100 characters
- Use type hints everywhere

**Documentation**:
- All functions need docstrings
- Use Google style docstrings
- Include examples in complex functions

```python
"""
Brief description.

Detailed description with examples:
    >>> example_function(1, 2)
    3

Args:
    param1: Description
    param2: Description

Returns:
    Description of return value
"""
```

**Testing**:
- Write tests for all new features
- Use pytest fixtures
- Aim for >80% coverage

**Code Example**:

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

async def create_agent(
    db: AsyncSession,
    name: str,
    role: str,
    team_id: Optional[int] = None
) -> Agent:
    """
    Create a new agent.
    
    Args:
        db: Database session
        name: Unique agent name
        role: Job title
        team_id: Optional team assignment
    
    Returns:
        Created agent object
    
    Raises:
        ValueError: If name is empty or already exists
    
    Example:
        >>> agent = await create_agent(db, "Dev", "Developer")
        >>> print(agent.name)
        'Dev'
    """
    if not name:
        raise ValueError("Name is required")
    
    # Check for duplicates
    existing = await db.execute(
        select(Agent).where(Agent.name == name)
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Agent {name} already exists")
    
    # Create agent
    agent = Agent(name=name, role=role, team_id=team_id)
    db.add(agent)
    await db.commit()
    
    return agent
```

### TypeScript/JavaScript (Frontend)

**Style**:
- Use ESLint and Prettier
- 2 spaces indentation
- Semicolons required
- Single quotes for strings

**TypeScript**:
- Use strict mode
- Define interfaces for all data structures
- Avoid `any` type
- Use type guards for runtime checks

**Documentation**:
- JSDoc for functions and classes
- Inline comments for complex logic

**Code Example**:

```typescript
/**
 * Create a new agent via API.
 * 
 * @param data - Agent creation data
 * @returns Created agent object
 * @throws {Error} If validation fails
 * 
 * @example
 * const agent = await createAgent({
 *   name: 'Developer',
 *   role: 'Senior Developer'
 * });
 */
async function createAgent(data: AgentCreate): Promise<Agent> {
  // Validate required fields
  if (!data.name || !data.role) {
    throw new Error('Name and role are required');
  }
  
  const response = await fetch('/api/agents/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    throw new Error(`Failed to create agent: ${response.statusText}`);
  }
  
  return response.json();
}
```

## Submitting Changes

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code change
- `test`: Tests
- `chore`: Maintenance

**Examples**:

```
feat(agents): add agent performance metrics

Add tasks_completed, failure_count fields to Agent model.
Update scheduler to track metrics on task completion.

Closes #123
```

```
fix(api): resolve rate limit retry logic

Fixed issue where rate limit retry wasn't working correctly.
Now properly extracts retry_seconds from error response.

Fixes #456
```

### Pull Request Process

1. **Create Branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make Changes**:
   - Write code
   - Add tests
   - Update docs
   - Run linters

3. **Commit**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

4. **Push**:
   ```bash
   git push origin feature/my-feature
   ```

5. **Create PR**:
   - Fill out PR template
   - Link related issues
   - Add screenshots if UI changes
   - Request review

6. **Address Feedback**:
   - Make requested changes
   - Push updates
   - Resolve conversations

7. **Merge**:
   - Squash commits if requested
   - Delete branch after merge

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console errors
- [ ] Works in production build

## Screenshots (if UI changes)
[Add screenshots]

## Related Issues
Fixes #123
```

## Extension Development

Want to add a new feature? See [EXTENSIONS_GUIDE.md](EXTENSIONS_GUIDE.md) for detailed tutorials.

### Quick Checklist for Extensions

- [ ] Database model changes (if needed)
- [ ] Pydantic schemas
- [ ] API endpoints
- [ ] Service layer
- [ ] Frontend components
- [ ] Tests
- [ ] Documentation
- [ ] Example in README

### Extension PR Template

```markdown
## Extension: [Name]

### What It Does
Brief description of the extension

### Files Changed
- backend/app/models/models.py
- backend/app/api/new_feature.py
- backend/app/services/new_service.py
- frontend/src/app/new-page/page.tsx

### Testing
- [ ] Unit tests added
- [ ] Integration tests pass
- [ ] Example code provided

### Documentation
- [ ] Code comments added
- [ ] README updated
- [ ] EXTENSIONS_GUIDE.md entry added

### Breaking Changes
None / List any

### Migration Required
None / Describe migration steps
```

## Testing Guidelines

### Backend Tests

```python
# tests/test_agents.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient):
    """Test agent creation"""
    response = await client.post(
        "/agents/",
        json={"name": "TestAgent", "role": "Tester"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "TestAgent"
    assert data["role"] == "Tester"
```

### Frontend Tests

```typescript
// __tests__/agents.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import AgentsPage from '@/app/agents/page';

describe('AgentsPage', () => {
  it('creates agent on form submit', async () => {
    render(<AgentsPage />);
    
    const nameInput = screen.getByLabelText('Name');
    fireEvent.change(nameInput, { target: { value: 'TestAgent' } });
    
    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);
    
    // Assert agent was created
    expect(await screen.findByText('TestAgent')).toBeInTheDocument();
  });
});
```

## Code Review Process

### Reviewer Responsibilities

1. **Understand the Change**
   - Read PR description
   - Check linked issues
   - Understand context

2. **Code Quality**
   - Follows style guidelines
   - Properly documented
   - No obvious bugs
   - Efficient implementation

3. **Testing**
   - Tests cover new code
   - Edge cases handled
   - No breaking changes (or documented)

4. **Documentation**
   - README updated if needed
   - Code comments clear
   - Examples provided

### Review Comments

**Be Constructive**:

```
❌ "This is wrong"
✅ "Consider using X here because Y"

❌ "Fix this"
✅ "Could you add error handling for case Z?"
```

**Request Changes**:
- Be specific about what needs changing
- Explain why
- Suggest alternatives

**Approve**:
- LGTM (Looks Good To Me)
- Note any minor suggestions
- Ready to merge

## Release Process

1. **Version Bump**:
   - Update version in `backend/app/main.py`
   - Update version in `frontend/package.json`

2. **Update Changelog**:
   - Add release notes
   - List all changes
   - Credit contributors

3. **Create Tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

4. **Create Release**:
   - Draft release on GitHub
   - Add release notes
   - Attach binaries if needed

## Getting Help

- **Discord**: [Join our Discord](https://discord.gg/...)
- **GitHub Discussions**: Use for questions
- **Issues**: Report bugs here
- **Email**: maintainers@openclaw.org

## Recognition

Contributors will be:
- Listed in README.md
- Mentioned in release notes
- Added to CONTRIBUTORS.md

Thank you for contributing! 🚀
