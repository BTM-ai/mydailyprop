# Contributing to My daily propaganda

Thank you for considering contributing to My daily propaganda! We welcome contributions from the community and are excited to see what you can bring to the project.

## How to Contribute

### Reporting Issues

If you encounter any bugs or have suggestions for improvements, please create an issue on the [GitHub Issues](https://github.com/BTM-ai/mydailymyprop/issues) page. Provide as much detail as possible to help us understand and address the issue.

### Forking the Project

1. Fork the project.
2. Create an issue, set the project, and assign yourself if you want to work on the issue.
3. Create a branch from `main` with a descriptive name.
4. Checkout locally to your new branch.

### Making Changes

1. Make your changes in your local branch.
2. Commit your changes with a descriptive commit message:
    ```bash
    git commit -m 'description of this commit'
    ```
3. Try to make unitary commits to keep the commit history clean.

### Pushing Changes

1. Push your changes to your forked repository:
    ```bash
    git push
    ```

### Creating a Pull Request

0. Before creating a PR, verify if the definition of done defined on the issue is complete.
1. Open a Pull Request (PR) from your forked repository to the main repository.
2. If you already have a draft PR, mark it as ready for review.
3. Request a review from the maintainers.

### Review Process

1. Apply any requested changes and comment on the Pull Request.
3. Re-request a review and repeat the process until you have an approved review.

### Merging Changes

1. Rebase your branch before merging to keep the commit history clean.
2. Once approved, squash and merge your commits.
3. Delete your branch after merging.

## Development Setup

For developers wishing to contribute or work on advanced features, follow these additional steps:

1. Install the dependencies with the development tools:
    ```bash
    poetry install --with dev
    ```

2. Configure the pre-commit hooks:
    ```bash
    poetry shell
    ```

3. Set up the hooks in your repository:
    ```bash
    pre-commit install
    ```

4. It is recommended to use **Visual Studio Code (VSCode)** as the IDE. Install the **Run and Debug** extension to run the project directly from the editor.

Hooks will run automatically on each commit. To run them manually on all files, use:
```bash
    pre-commit run --all-files
```
