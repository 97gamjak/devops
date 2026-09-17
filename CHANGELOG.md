# Changelog

All notable changes to this project will be documented in this file.

## Next Release

### Features

#### CPP Rules

- Add first libclang AST-based check (`paramNameForType`) that enforces canonical parameter names for configured types; supports fully-qualified type names (e.g. `"molsys::SimulationBox"`), leading `::` stripping, and suffix matching for types that acquire an extra namespace prefix via libclang/GCC system-header quirks
- Allow multiple accepted parameter names per type in `paramNameForType` by setting the value to a list (e.g. `["simulationBox", "box"]`)
- Add `unseen_type_is_error` option to `paramNameForType`: when `true`, a configured type never seen as a parameter type across all checked files fails the run instead of just warning
- Add `ast_check_compile_commands_db` config option to read per-file compile flags from a `compile_commands.json` database; strip CMake precompiled-header flags (`-Xclang -include-pch`) that cause libclang parse failures when the `.gch` file is absent for a given cmake target
- Add per-check TOML configuration via `[cpp.ast_check_config.<check-id>]` sub-tables, allowing each AST check to declare its own settings
- Add `check_dirs` config option to restrict C++ checks to specific directories
- Add `exclude_dirs` config option to skip directories during recursive file scanning
- Add `(i/total)` file progress logging during C++ checks
- Add incremental check mode: set `incremental_state_file = "build/.cpp_check_state.json"` in `[cpp]` (or pass `--incremental` / `--state-file` on the CLI) to persist per-file pass/fail state and skip already-passing, unmodified files on subsequent runs; fail-fast behaviour is preserved by default
- Add `fail_fast` config option (default `true`) and `--no-fail-fast` CLI flag: when disabled, all files are checked even after a failure and their results are all recorded — particularly useful combined with incremental mode to get a full picture of the codebase in one pass

#### Documentation

- Fill in the user guide with an "Overview" page (feature areas and full CLI command reference) and a "Configuration File" page documenting every `devops.toml`/`.devops.toml` section and key, discovery rules, and the changelog insertion-marker format

### Bug Fixes

#### CPP Rules

- Fix `cpp_checks` CLI always scanning all directories regardless of `check_dirs` config

<!-- insertion marker -->
## [0.1.4](https://github.com/repo/owner/releases/tag/0.1.4) - 2026-09-13

### Bug Fixes

#### Documentation

- Explicitly dispatch the `Docs` workflow from `create-tag.yml` instead of relying on the tag push to trigger it, since pushes made with `GITHUB_TOKEN` don't trigger other workflows (GitHub's anti-recursion protection) - the release tag push was silently never deploying the docs
- Allow the `Docs` workflow to be redeployed manually via `workflow_dispatch` regardless of ref

## [0.1.3](https://github.com/repo/owner/releases/tag/0.1.3) - 2026-09-13

### Bug Fixes

#### Documentation

- Only deploy documentation to GitHub Pages on release tag pushes, so the published version reflects the clean release version (e.g. `0.1.2`) instead of a dev version (e.g. `0.1.2.dev0+g...`)
- Add `docs` status badge to the README

## [0.1.2](https://github.com/repo/owner/releases/tag/0.1.2) - 2026-09-13

### Features

#### Documentation

- Add Sphinx documentation site (`sphinx-rtd-theme`) with an automatically generated API reference from docstrings and an automatically displayed package version
- Add placeholder user guide section for future explanatory documentation pages

### Deployment

#### CI/CD

- Add GitHub Actions workflow to build the documentation and deploy it to GitHub Pages on merges to `main`

## [0.1.1](https://github.com/repo/owner/releases/tag/0.1.1) - 2026-02-20

### Features

#### CPP Rules

- make it possible to check header guards also for `.tpp` and `.impl.hpp` files

## [0.1.0](https://github.com/repo/owner/releases/tag/0.1.0) - 2026-01-18

#### Config

- Add `changelog_paths` to config toml approach
- Add `default_changelog_path` to config toml approach

#### API

- Add `changelog_path` input to `update_changelog`
- Add `update_changelogs` to update multiple changelogs at once

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











