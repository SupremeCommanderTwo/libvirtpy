# libvirtpy

Pure-Python libvirt: typed XML models, the wire protocol and a sync/async client.
No libvirt C library is needed, and nothing is built from source.

```{toctree}
:maxdepth: 2
:caption: Guide

quickstart
xml
client
domains
storage-networks
snapshots-backups
host-tuning
async
remote
events-streams
robustness
testing
troubleshooting
architecture
faq
licensing
development
```

```{toctree}
:maxdepth: 2
:caption: Reference

reference/xml
reference/client
reference/rpc
```

## Three layers in one package

| Package | What it does | Needs |
|---|---|---|
| `libvirtpy.xml` | pydantic models that parse and generate every libvirt XML document | pydantic |
| `libvirtpy.rpc` | the libvirt wire protocol: unix, ssh, tls and tcp, SASL, events, streams | standard library |
| `libvirtpy.client` | about 280 operations, blocking and `asyncio`, speaking in the models | both |

`libvirtpy.client` imports the two others; they never import each other.
