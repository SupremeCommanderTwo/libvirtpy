# XML models

`libvirtpy.xml` has a model for every libvirt document: `Domain`, `Network`,
`NetworkPort`, `Pool`, `Volume`, `Snapshot`, `Backup`, `Checkpoint`, `Secret`,
`Filter`, `FilterBinding`, `Device` (a host device), `HostInterface`, `Sysinfo` and
the read-only `Capabilities`, `DomainCapabilities` and `StoragePoolCapabilities`.

```python
from libvirtpy.xml import Domain

domain = Domain.from_xml(open("vm.xml").read())
print(domain.name, domain.memory.value, domain.memory.unit)
domain.vcpu.value = 4
print(domain.to_xml())
```

## What the models promise

- **Round trips do not lose data.** The models parse all 10,728 files of libvirt's own
  test corpus and write them back equal (compared as normalised XML trees).
- **They generate valid XML.** Output is validated against libvirt's RelaxNG schemas.
- **Nothing is invented.** A missing element or attribute stays `None`; libvirt's
  defaults are not filled in, so writing the model back does not change the document.
- **Order is kept** between siblings of the same tag (device order matters to libvirt).
- **Unknown elements are ignored** when parsing, so XML from a newer libvirt still loads.

## Conventions

- Names follow the libvirt docs: `<memballoon>` is `Memballoon`, in the module of its
  section of `formatdomain`.
- Variants such as `<disk type='file'>` and `<disk type='network'>` are one model each,
  joined in a union (`FileDisk | NetworkDisk | ...`); an unknown `type` is an error.
- Units stay as written: `Memory(value=4, unit="GiB")`; `memory.to_bytes()` converts.
- `yes`/`no` and `on`/`off` become `bool`; `PresenceFlag` stands for `<acpi/>`.
- Models are mutable and validate on assignment.

See {doc}`reference/xml` for every model.
