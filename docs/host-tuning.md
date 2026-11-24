# Host information, statistics and tuning

## The host

```python
info = client.get_host_info()
print(info.cpus, info.mhz, info.memory)  # memory in KiB

print(client.get_hostname(), client.get_version())  # the version is one integer
print(client.get_host_cpu_stats())  # {"kernel": ..., "user": ..., ...}
print(client.get_host_memory_stats())
print(client.get_host_cells_free_memory())  # per NUMA cell
```

`get_capabilities()` returns a {class}`~libvirtpy.xml.Capabilities` model (host CPU,
topology, guest types); `get_domain_capabilities(...)` and
`get_storage_pool_capabilities()` return the matching models. `get_sysinfo()`
returns the host's SMBIOS data as a `Sysinfo`.

## Statistics

Per-domain numbers come back as plain data:

```python
client.get_domain_cpu_stats("vm")  # list of dicts, one per CPU
client.get_domain_memory_stats("vm")
client.get_domain_block_stats("vm", "vda")
client.get_domain_interface_stats("vm", "vnet0")  # rx/tx bytes, packets, errors
client.get_domain_block_info("vm", "vda")  # capacity, allocation, physical
client.get_all_domain_stats()  # every domain in one call
```

## Typed parameters

libvirt's tuning calls (scheduler, memory, block I/O, NUMA, migration, ...) exchange
*typed parameters*. Here they are plain `dict`s; getters return one, setters take one:

```python
LIVE = 1
client.set_domain_scheduler_parameters("vm", {"cpu_shares": 512}, flags=LIVE)
print(client.get_domain_scheduler_parameters("vm")["cpu_shares"])

client.set_domain_memory_parameters("vm", {"soft_limit": 1048576}, flags=LIVE)
```

The integer width of each documented name (`cpu_shares` is an unsigned long long, and
so on) comes from libvirt's headers, so you pass ordinary Python numbers. Names the
library does not know are typed from the value you give: `bool`, `int`, `float` or `str`.

## CPU pinning

```python
client.pin_domain_vcpu("vm", 0, [0, 1], flags=LIVE)  # vCPU 0 on host CPUs 0 and 1
print(client.get_domain_vcpu_pins("vm", flags=LIVE))  # [[0, 1]]
```

`get_host_cpu_map()` tells which host CPUs are online (it returns the reply struct
`NodeGetCpuMapRet`).
