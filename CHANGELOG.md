# Changelog

All notable changes to this project will be documented in this file.

## Next Release

<!-- insertion marker -->
## [0.12.0](https://github.com/repo/owner/releases/tag/0.12.0) - 2026-10-04

### Features

#### CPP Rules

- Add `noFinalKeyword` AST check flagging use of the `final` specifier on classes, structs, and virtual methods (Fixes #158)

## [0.11.0](https://github.com/repo/owner/releases/tag/0.11.0) - 2026-10-03

### Features

#### CPP Rules

- Add `noClangFormatToggle` AST check flagging `// clang-format off` / `// clang-format on` comments (both line- and block-comment spellings) anywhere in code (Fixes #153)

#### CPP Checks

- Add `parallel_jobs` option (`[cpp]` TOML section, also `--jobs`/`-j` on the `cpp_checks` CLI) to speed up slow AST checks by parsing files concurrently across a process pool. Defaults to `1` (serial, identical to prior behavior); values `> 0` use that many worker processes, values `<= 0` use `os.cpu_count()`. Only the libclang AST parse — the CPU-bound part — is parallelized; other rule types keep running serially since they're cheap. With `fail_fast` enabled, a parallel run stops soon after a failure rather than at the exact first failing file in listing order

### Fixes

#### CPP Checks

- Stop reading each checked file from disk twice per run (once for file-based rules, once for line-based rules); the content is now read once and shared between both

## [0.10.0](https://github.com/repo/owner/releases/tag/0.10.0) - 2026-10-02

### Features

#### CPP Rules

- Add `includeIwyuPragmaOnly` AST check flagging a `#include` line whose trailing comment is not a valid `// IWYU pragma: ...` comment (Fixes #150). An `#include` with no trailing comment is always allowed. Takes an optional `allowed_pragmas` list restricting which IWYU pragma keywords (e.g. `export`, `keep`) are accepted; when unset, every pragma keyword is allowed

## [0.9.0](https://github.com/repo/owner/releases/tag/0.9.0) - 2026-09-30

### Features

#### CPP Rules

- Add `noNewInGtestSetup` AST check flagging `new` expressions anywhere inside a member function named `SetUp`, `SetUpTestSuite`, or `SetUpTestCase` — the fixture-setup hooks GTest calls by name. A raw pointer allocated there needs a matching manual release whose timing depends on a separate teardown hook firing correctly later; prefer an RAII/smart-pointer owner instead. Only a literal `new` lexically inside the setup function's own body is flagged, not calls into other functions. Takes no configuration
- Add `noDeleteInGtestTeardown` AST check flagging `delete`/`delete[]` expressions anywhere inside a member function named `TearDown`, `TearDownTestSuite`, or `TearDownTestCase` — the fixture-teardown hooks GTest calls by name. Manually deleting a raw pointer there is fragile (a `SetUp()` that throws or returns early skips the matching `delete`, and a test body that already freed the pointer causes a double-free); prefer an RAII/smart-pointer owner instead. Only a literal `delete`/`delete[]` lexically inside the teardown function's own body is flagged, not calls into other functions. Takes no configuration

## [0.8.0](https://github.com/repo/owner/releases/tag/0.8.0) - 2026-09-30

### Features

#### CPP Rules

- Add `noPublicLeadingUnderscore` AST check flagging public member variables and member functions (including static and template ones) whose name starts with `_`, e.g. `int _count;` or `void _compute();` under `public:` (or under a `struct`'s default access) should drop the leading underscore. Private/protected members are never checked here, since that's the concern of `memberLeadingUnderscore`/`memberFunctionLeadingUnderscore`. Constructors/destructors, operator overloads/conversions, and methods overriding a base-class virtual method are always exempt, and members synthesized entirely by a macro invoked on the same source line are excluded too. Takes no configuration
- Add `classMemberOrder` AST check enforcing a fixed section order within each class/struct/union body: public, protected, then private member variables, followed by public, protected, then private member functions. Only in-class declarations count — out-of-line member-function definitions don't affect ordering — and declarations outside that list (nested types, `using` declarations, enums, friend declarations, ...) are ignored rather than resetting the sequence. Takes an optional `excluded_macros` list (e.g. `["Q_OBJECT"]`) so members/access-specifier changes synthesized by a named macro invocation are excluded from ordering entirely

## [0.7.0](https://github.com/repo/owner/releases/tag/0.7.0) - 2026-09-28

### Python Requirement

- remove 3.12 dependeny
- add support for 3.14

### Features

#### CPP Rules

- Add `memberFunctionLeadingUnderscore` AST check flagging private and protected member functions (including static and template ones) whose name doesn't start with `_`, e.g. `void compute();` under `private:`/`protected:` should be `void _compute();`. Public methods are never checked, and constructors/destructors, operator overloads/conversions, and methods overriding a base-class virtual method are always exempt, since their names aren't the author's to change. As with `memberLeadingUnderscore`, methods synthesized entirely by a macro invoked on the same source line are excluded too. Takes no configuration

### Fixes

#### Documentation

- Fix `sphinx-build` failing under `-W` when the optional `ast` extra (`libclang`) isn't installed — as in the docs CI job, which only installs the `docs` extra. `memberFunctionLeadingUnderscore` bound a libclang ctypes function signature (`ctypes.POINTER(clang.Cursor)`) at module import time, which raised `TypeError: must be a ctypes type` against Sphinx's mocked `clang` module and broke autosummary for `devops.cpp` and everything that imports it (`add_license_header`, `cpp_checks`, `cpp_files`). The binding is now deferred to first use, when a real `clang.Cursor` is guaranteed to be available

## [0.6.0](https://github.com/repo/owner/releases/tag/0.6.0) - 2026-09-27

### Features

#### CPP Rules

- Add `memberLeadingUnderscore` AST check flagging private and protected member variables (including static ones) whose name doesn't start with `_`, e.g. `int count;` under `private:`/`protected:` should be `int _count;`. Public members are never checked. Members synthesized entirely by a macro invoked on the same source line (e.g. gtest's `TEST_F(...)` expanding to a fixture class with its own private `test_info_` member) are excluded, since there is no user-typed name to rename. Takes no configuration

### Documentation

- Add a dedicated "AST-Based C++ Checks" section to the Sphinx docs with an overview table of every AST check and its own sidebar-linked page per check (`paramNameForType`, `macroReplacement`, `noGlobalUsing`, `noGlobalUsingEnum`, `noThrowParen`), each with flagged-code examples and its full configuration reference. The scattered/partial AST-check descriptions previously duplicated across the overview and configuration pages now point to these pages instead

## [0.5.0](https://github.com/repo/owner/releases/tag/0.5.0) - 2026-09-27

### Features

#### CPP Rules

- Add `macroReplacement` AST check flagging invocations of a banned macro and suggesting its replacement, e.g. disallowing gtest's `EXPECT_THROW`/`ASSERT_THROW` in favor of custom `EXPECT_THROW_MSG`/`ASSERT_THROW_MSG` macros that also require a failure message. Ships with that mapping as a built-in default (no configuration required) and is fully configurable/extensible via `[cpp.ast_check_config.macroReplacement].macro_to_replacement`. Detection matches the macro name exactly and works whether the macro is defined in the same file or an included header

### Fixes

#### CPP Rules

- Fix a libclang crash (`astParseError` with no useful diagnostic) when parsing a file whose compile args force-include a PCH header via the `-include <file>` compiler flag (as kept by the earlier `-include`-handling fix). Pip's libclang build has been observed to hard-crash on some real PCH headers when force-included this way — even though the exact same header content parses cleanly as an ordinary `#include`, and even though the project's own real compiler accepts the identical flag without issue. `-include <file>` is now stripped from the compiler args and instead turned into a real `#include` line ahead of the checked file in a synthetic wrapper (the same technique already used for header checks), which avoids the crash while preserving the checked file's own path and line numbers exactly

## [0.4.2](https://github.com/repo/owner/releases/tag/0.4.2) - 2026-09-26

### Fixes

#### CPP Rules

- Refine the `-include`/`-include-pch` handling in `compile_commands.json` arg filtering (following up on the 0.4.1 fix): `-include-pch` (the compiled PCH binary) is still always dropped, since it's serialized by whichever real compiler produced it and is generally incompatible with pip's bundled libclang regardless of whether the file exists. A plain `-include <file>` (the textual PCH header CMake also generates alongside the binary one) is now kept — normalized to a bare pair regardless of how it was originally wrapped — whenever that file exists on disk, since real project headers often rely on it being force-included first for standard-library symbols (`<optional>`, `<format>`, ...) they don't include themselves; unconditionally dropping it (the previous fix) produced a cascade of unrelated "no member"/"too many errors" failures when such a header was checked standalone. It's still dropped when missing, to avoid the original "file not found" fatal error

## [0.4.1](https://github.com/repo/owner/releases/tag/0.4.1) - 2026-09-26

### Fixes

#### CPP Rules

- Fix a bug in `compile_commands.json` arg filtering where a bare `-include <file>` (as GCC/CMake's `target_precompile_headers` emits, unlike Clang's `-Xclang -include -Xclang <file>`) had its file argument silently dropped by the positional-source-file heuristic, leaving a dangling `-include` that swallowed the next unrelated flag as its filename and caused a fatal parse error. `-include` (bare or `-Xclang`-wrapped, including `-include-pch`) is now always dropped together with its file argument, since a force-included PCH header may not exist for every cmake target

## [0.4.0](https://github.com/repo/owner/releases/tag/0.4.0) - 2026-09-26

### Features

#### CPP Rules

- Add `noThrowParen` AST check flagging `throw(...)` where the parentheses wrap the entire thrown expression (e.g. `throw(x);`, `throw(SomeException(1));`); write these as `throw x;` / `throw SomeException(1);` instead. Parentheses that are only part of the thrown expression itself (`throw SomeException(1);`) and a bare rethrow (`throw;`) are not affected

### Fixes

#### CPP Rules

- AST checks now parse full function bodies (previously skipped for performance), so statement-level checks like `noThrowParen` can see inside them
- Auto-detect and pass `-resource-dir` to libclang when parsing, using the project's own compiler from `compile_commands.json` (or `clang++`/`clang` on PATH as a fallback). Pip's `libclang` wheel ships no builtin headers, so without this, parsing real files could silently hit a fatal error partway through and stop analyzing the rest of the file
- Surface a fatal libclang parse error (e.g. an unresolvable `#include`) as a visible `astParseError` diagnostic instead of silently reporting no issues for the unparsed remainder of the file

## [0.3.0](https://github.com/repo/owner/releases/tag/0.3.0) - 2026-09-22

### Features

#### CPP Rules

- Add `noGlobalUsing` AST check flagging `using namespace X;` and `using X::Y;` at global or namespace scope (the same constructs inside function, lambda or class bodies are allowed); the full qualified name is reported (e.g. `a::b`)
- Add `noGlobalUsingEnum` AST check flagging `using enum X;` at global or namespace scope
- Add `enabled_names` / `disabled_names` options for `noGlobalUsing` and `noGlobalUsingEnum` (`[cpp.ast_check_config.<check-id>]`) to report only, or exempt, specific namespaces/declarations, matched by qualified name (e.g. `"std::literals"`)

#### CPP Rules

- Invalidate the incremental state file whenever the TOML config file changes (a hash of its contents is stored in the state file), so all files are re-checked with the new configuration

## [0.3.0](https://github.com/repo/owner/releases/tag/0.3.0) - 2026-09-20

### Features

#### CPP Rules

- add cli arg `--base-ref` to only check git changed files

## [0.2.1](https://github.com/repo/owner/releases/tag/0.2.1) - 2026-09-20

### Bug Fixes

#### CPP Rules

- Add `.tpp` files to header file extensions

## [0.2.0](https://github.com/repo/owner/releases/tag/0.2.0) - 2026-09-20

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
- Fix AST parse failures being silently ignored: files that libclang cannot parse now produce a real check error (`[astParseError]`) and fail the run instead of being treated as passing

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


























