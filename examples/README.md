# Client examples (prototype)

These scripts run against `FakeLibvirt`, an in-memory daemon, so they need no
libvirt. Run any of them from the repository root:

```sh
.venv/bin/python examples/01_define_start_stop.py
```

| Script | Shows |
|---|---|
| `01_define_start_stop.py` | the life of a domain: define, start, inspect, shut down, undefine |
| `02_lookup_and_edit_xml.py` | find a domain by id, name, UUID or model; edit the model; redefine |
| `03_set_vcpus_memory.py` | change vCPUs and memory, autostart, hot-plug a device |
| `04_networks_pools_volumes.py` | a network, a storage pool and its volumes |
| `05_snapshots.py` | snapshots of a domain: create, list, revert, delete |
| `06_errors.py` | the errors a daemon reports, as exceptions |
| `07_async_concurrent.py` | the async client: many requests at once |
| `08_proxy_style.py` | `client.domain("vm").start()` instead of `client.start_domain("vm")` |
| `09_host_and_other_resources.py` | host capabilities, devices, secrets, filters, host interfaces |

`common.py` builds the sample models they share. When the protocol layer
exists, only the first lines change: `LibvirtClient.open("qemu:///system")`
instead of `LibvirtClient(FakeLibvirt())`.

`real/` has the same kind of scripts against a **real** libvirt: local system and
session, SSH, TLS, TLS with a SASL login, and the async client over many hosts.
See `real/README.md`.
