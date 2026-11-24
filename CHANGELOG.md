# Changelog

All notable changes to libvirtpy are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `libvirtpy.xml`: typed pydantic models for every libvirt XML document (domain,
  network, network port, storage pool and volume, snapshot, checkpoint, backup,
  secret, network filter and binding, host device, host interface, sysinfo, and the
  capabilities documents). They round-trip all 10,728 files of libvirt 12.9.0's test
  corpus and validate against its RelaxNG schemas.
- `libvirtpy.rpc`: the libvirt wire protocol in pure Python (XDR codec, sans-I/O
  session, synchronous and `asyncio` connections), over UNIX sockets, SSH, TLS and TCP,
  with SASL (SCRAM-SHA-256/1, DIGEST-MD5, PLAIN), events and data streams.
- `libvirtpy.client`: about 280 operations as `LibvirtClient` and `AsyncLibvirtClient`
  (one implementation, two generated clients), references by id, name, UUID or model,
  per-object proxies, and the in-memory `FakeLibvirt` daemon for tests.
- Documentation (Sphinx, Read the Docs), runnable examples against a fake daemon and
  against a real libvirt, and `tools/setup_test_vps.sh` to prepare a remote test host.

### Robustness

- Client keepalive (`keepalive_interval`, `keepalive_count`) detects a dead daemon, an
  optional per-call `timeout` raises `CallTimeoutError` and leaves the connection
  usable, and event subscriptions keep at most `max_events` events (the oldest are
  dropped and counted in `dropped`).
- Fuzz tests of the XDR decoder, the session, SASL and URI parsing; hostile SCRAM
  and DIGEST-MD5 messages are rejected with `AuthFailedError`.

- Optional automatic reconnect (`open(..., reconnect=True)`): a lost connection is
  opened again with backoff; event subscriptions are registered again and
  `subscription.reconnects` counts it.

### Quality

- Stricter lint (`RUF`, `PERF`, `ARG`, `PIE`), a coverage gate (95%, currently 98%), tests
  that run every generated client method and proxy against the real protocol
  structures, and the fake daemon split into one module per area.

### Fixed

- `qemu+ssh://`: the remote command is quoted, so the remote shell runs the whole
  `virt-ssh-helper` / `nc -U` script.
- SASL: the daemon's comma-separated mechanism list is parsed.
- TLS: a `pkipath` without `cacert.pem` is an error instead of falling back to the
  system CAs; `~` and `$VARIABLES` in `pkipath` are expanded.

### Verified

- Against a real `qemu:///system`: read-only and write tests (throwaway objects only).
- Against a real remote libvirt 12 server: SSH, TLS and TLS with a SASL login.

### Licence

- LGPL-2.1-or-later. The generated protocol code in `libvirtpy.rpc.protocol` is derived
  from libvirt's `.x` files (see `NOTICE`).
