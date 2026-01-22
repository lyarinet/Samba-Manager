# Contributing to Samba Manager 🚀

Thank you for your interest in contributing to **Samba Manager**! We welcome contributions from everyone. 

To maintain code quality and a smooth workflow, please follow these guidelines.

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. **Check Existing Issues**: Before creating a new issue, please check if it already exists.
2. **Use the Bug Report Template**: When creating an issue, provide:
   - A clear and descriptive title
   - Steps to reproduce the bug
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Your environment (OS, browser, etc.)

### Suggesting Enhancements

1. **Check Existing Suggestions**: Ensure your suggestion hasn't already been proposed.
2. **Provide Details**: Clearly describe the enhancement, including:
   - Why it would be useful
   - How it should work
   - Any alternatives you've considered

### Pull Requests

1. **Fork the Repository**: Create your own fork of the project.
2. **Create a Branch**: Make your changes in a new branch.
3. **Follow Code Style**: Maintain the existing code style.
4. **Write Tests**: Add tests for new features or bug fixes.
5. **Update Documentation**: Update relevant documentation.
6. **Submit a Pull Request**: Include a clear description of the changes and any related issues.

## 🛠 Set Up Development Environment

Follow these steps to set up the project on your local machine:

1. **Fork** the repository and **Clone** it to your system.

2. Create and activate a virtual environment:
   ```bash
   git clone https://github.com/lyarinet/samba-manager.git
   cd samba-manager
   ```

3. **Set Up Development Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run in Development Mode**:
   ```bash
   python run.py --dev
   ```

## Code Style

- Follow PEP 8 for Python code
- Use consistent indentation (4 spaces)
- Keep lines under 100 characters when possible
- Write clear, descriptive comments

## Testing

- Add tests for new features or bug fixes
- Ensure all tests pass before submitting a pull request
- Run tests with: `python -m unittest discover`

## Documentation

- Update the README.md file with new features or changes
- Document code using docstrings
- Update any relevant documentation in the project

## Review Process

1. A maintainer will review your pull request
2. Changes may be requested before merging
3. Once approved, your pull request will be merged

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

Thank you for contributing to Samba Manager! 
