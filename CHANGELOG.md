# Changelog

All notable changes to this project will be documented in this file.

## Next Release

<!-- insertion marker -->
## [0.0.4](https://github.com/repo/owner/releases/tag/0.0.4) - 2025-12-20

### Features

#### CPP Rules

- Add CPP rule to check that in a header file there is always a header guard present
- Adding option to enforce header guard format via file path

## [0.0.3](https://github.com/repo/owner/releases/tag/0.0.3) - 2025-12-20

### Bug Fixes

#### API

- Now `cpp_checks` returns exit(1) if any test fails

## [0.0.2](https://github.com/repo/owner/releases/tag/0.0.2) - 2025-12-20

### API

- Add `dirs` argument to `cpp_checks` cli

### Bug Fixes

#### Config

- generated default .toml file contains now key `license_header`

## [0.0.1](https://github.com/repo/owner/releases/tag/0.0.1) - 2025-12-20

### API

- Add cli command `get_latest_tag`
- Add cli command `increase_latest_tag`
- Add new license checking rule to `cpp_checks`
- Add cli command `generate_toml_template` to get a template default toml file
- Add cli commands `add_license_header` and `add_license_headers`
- Add cli command `filter_buggy_cpp_files`

### Features

#### Git

- Add function to retrieve latest tag from git

#### Config

- Adding possibility to have a `devops.toml` or `.devops.toml` config file
- Adding logging levels to toml file config: `global_level`, `utils_level`, `config_level`, `cpp_level`
    ```toml
    [logging]
    global_level = "INFO"
    cpp_level = "DEBUG"
    ```
- Adding `file.encoding` config for toml configuration

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






