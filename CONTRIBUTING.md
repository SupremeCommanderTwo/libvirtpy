# Contributing to libvirtpy

Thanks for helping. The rules for code, models and tests are in the
[development guide](docs/development.md); read it first, it is short where it matters:

- Python 3.14 only; full type annotations; `mypy --strict`; `ruff`.
- Docstrings with `:param:` lines on every function in `src/` and `tools/`.
- Blank lines between logical steps; public code first, helpers last.
- Every bug fix comes with a test that fails without the fix.

## Setup

```sh
python3.14 -m venv .venv
.venv/bin/pip install -e . --group dev --group docs
```

## Before a pull request

```sh
.venv/bin/ruff format --check && .venv/bin/ruff check
.venv/bin/pytest --cov                            # default run: offline, ~10 s; coverage must stay >= 95%
                                                   # includes mypy --strict (tests/tools/test_types.py)
.venv/bin/python tools/fetch_samples.py            # once: libvirt's test corpus
.venv/bin/pytest -m corpus -q --tb=short           # models and generated files
.venv/bin/python -m sphinx -W -b html docs docs/_build/html
```

`client.py`, `aio.py` and `rpc/protocol/` are **generated**: change the operations or
the generator, then run `tools/gen_client.py`, `tools/gen_protocol.py`; never edit them.

Tests that need a libvirt daemon are opt-in: `pytest -m libvirt` (read-only) and
`pytest -m libvirt_write` (creates and removes `lvxtest-*` objects on
`qemu:///system`; never run it on a machine whose domains you care about).
`tools/setup_test_vps.sh` prepares a server for the remote transports.

## Using AI tools

Use whatever helps you, and stay the author of what you submit. Some suggestions:

- **Read and understand every line** you send. You answer for it in review, and the
  tool does not.
- **Run the checks yourself** (the commands above); do not trust "all tests pass" from
  a tool. A change that fixes a bug needs a test that fails without the fix.
- **Do not edit generated files** (`client/client.py`, `client/aio.py`,
  `rpc/protocol/`): change the operations or the generator and regenerate.
- **Do not paste code you cannot license.** The project is LGPL-2.1-or-later. libvirt's
  own sources, tests and documentation are not ours to copy in; models and tests are
  written from the schemas and the public protocol (`NOTICE` explains what is derived).
- **Keep tools away from real systems.** `pytest -m libvirt_write` creates and deletes
  objects on `qemu:///system`: never let a tool run it on a machine whose VMs, pools or
  networks you care about, and never give a tool credentials for a remote host.
- **Do not share private data** with a tool: host names, addresses, certificates, SASL
  passwords or the XML of your own VMs. Use the made-up values of the tests.
- **Prefer small, reviewable changes** over a large rewrite a tool produced in one go.
- **Do not commit tool files**: assistant instructions, rules and local state
  (`AGENTS.md`, `CLAUDE.md`, `.cursor/`, ...) are git-ignored on purpose. The shared
  project rules live in the documents above.

You do not have to say that a tool was used, but if it helps the reviewer (a big
generated test table, say), mention it in the pull request.

## Licence

By contributing you agree that your work is licensed under LGPL-2.1-or-later.
