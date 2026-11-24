# FAQ

## How is this different from `libvirt-python`?

`libvirt-python` wraps the libvirt C library: you need `libvirt-dev` to build it and the
library at run time, and objects are thin handles that return XML strings. libvirtpy
speaks the wire protocol itself, in pure Python, and returns typed models.

| | `libvirt-python` | libvirtpy |
|---|---|---|
| Needs libvirt C library | yes | no |
| Install | build against `libvirt-dev` | `pip install` |
| Replies | XML strings, tuples | models, `dict`s, dataclasses |
| asyncio | no (event loop integration only) | native `AsyncLibvirtClient` |
| In-memory fake for tests | no | `FakeLibvirt` |
| Python | 3.x | 3.14+ |

## Can it talk to remote hosts?

Yes: `qemu+ssh://`, `qemu+tls://` and `qemu+tcp://`, with SASL. SSH, TLS and TLS with
a SASL login are verified against a real remote daemon; plain TCP is covered by tests
with a fake server only ({doc}`remote`).

## What is not supported?

- Passing file descriptors (`open_graphics`, the `*_with_files` calls).
- *Starting* a migration; the daemon calls that make it up are available, but the client
  does not coordinate two daemons.
- SASL security layers and GSSAPI.
- Flags are plain integers, not typed `IntFlag` enums yet.

## Which libvirt versions work?

The protocol is generated from libvirt 12.9.0; older daemons accept the procedures they
know and reply with `NotSupportedError` to the rest. Tested against libvirt 11.6.

## Why Python 3.14 only?

The code uses `type` aliases, PEP 695 generics and lazy annotations without
compatibility shims.

## Can I use it in closed-source software?

Yes. The license is LGPL-2.1-or-later: your program keeps its own license; changes to
libvirtpy's own files must be shared ({doc}`licensing`).
