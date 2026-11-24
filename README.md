# libvirtpy

[![CI](https://github.com/SupremeCommanderTwo/libvirtpy/actions/workflows/ci.yml/badge.svg)](https://github.com/SupremeCommanderTwo/libvirtpy/actions/workflows/ci.yml)
[![Documentation](https://readthedocs.org/projects/libvirtpy/badge/?version=latest)](https://libvirtpy.readthedocs.io)
[![License: LGPL v2.1+](https://img.shields.io/badge/license-LGPL--2.1%2B-blue.svg)](LICENSE)

**Pure-Python libvirt**: typed XML models, the wire protocol and a sync/async client.
No libvirt C library, no `libvirt-dev`, no compiler.

- **`libvirtpy.xml`**: pydantic models that parse and generate every libvirt XML
  document (domain, network, storage, snapshot, backup, secret, nwfilter, host devices,
  capabilities, ...). They round-trip all 10,728 files of libvirt's own test corpus.
- **`libvirtpy.rpc`**: the libvirt wire protocol over UNIX sockets, SSH, TLS and TCP,
  with SASL, events and data streams. Standard library only.
- **`libvirtpy.client`**: about 280 operations as a blocking `LibvirtClient` and an
  `asyncio` `AsyncLibvirtClient`, speaking in the models. Keepalive, call timeouts and
  optional automatic reconnect included.

## Install

Requires **Python 3.14 or newer**.

```sh
pip install libvirtpy
```

## Quick start

```python
from libvirtpy.client import LibvirtClient

with LibvirtClient.open("qemu:///system") as client:
    domain = client.lookup_domain("vm")  # a Domain model, not an XML string
    print(domain.name, domain.vcpu.value)

    domain.vcpu.value = 4
    client.define_domain(domain)  # write the edited model back

    client.domain("vm").start()  # or client.start_domain("vm")
```

The same with `asyncio`:

```python
async with await AsyncLibvirtClient.open("qemu+ssh://root@host/system") as client:
    names = [d.name for d in await client.list_domains()]
```

No daemon at hand? `LibvirtClient(FakeLibvirt())` is an in-memory daemon for tests and
examples. Remote hosts work over `qemu+ssh://`, `qemu+tls://` and `qemu+tcp://`, with
SASL logins.

## Documentation

Guide and API reference: **https://libvirtpy.readthedocs.io** (source in `docs/`).
Runnable examples are in [`examples/`](examples/) (against the fake daemon) and
[`examples/real/`](examples/real/) (against a real libvirt).

## Status

Alpha. Verified against real libvirt 11 and 12 daemons, locally and over SSH, TLS and
TLS with SASL. Not supported yet: starting migrations, file-descriptor passing, SASL
security layers and GSSAPI. See the [changelog](CHANGELOG.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) and the
[development guide](docs/development.md). Security issues: see
[`SECURITY.md`](SECURITY.md).

```sh
python3.14 -m venv .venv
.venv/bin/pip install -e . --group dev
.venv/bin/pytest          # offline; includes the mypy --strict check
```

## License

LGPL-2.1-or-later (see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE)). Programs that use
libvirtpy may keep their own license, closed source included. Copyright (C) 2026
SupremeCommanderTwo.
