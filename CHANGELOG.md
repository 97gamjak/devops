# Changelog

All notable changes to this project will be documented in this file.

## Next Release

### API

- Add cli command `get_latest_tag`
- Add cli command `increase_latest_tag`
- Add new license checking rule to `cpp_checks`

### Features

#### Git

- Add function to retrieve latest tag from git
- Add 

#### Config

- Adding possibility to have a `devops.toml` or `.devops.toml` config file
- Adding logging levels to toml file config: `global_level`, `utils_level`, `config_level`, `cpp_level`
    ```toml
    [logging]
    global_level = "INFO"
    cpp_level = "DEBUG"
    ```

#### CPP Rules

- Add license check rule for cpp header and source files

### Deployment

#### CI/CD

- Add checking if `CHANGELOG.md` was updated
- Add ruff check and ruff format CI
- Add pytest CI with python versions 3.12 and 3.13
- Add automatic release CI for PRs to main (either via title or via hotfix/ branch)
- Add overnight CI runs for pytest and ruff CIs
- Add test coverage to pytest CI

<!-- insertion marker -->

