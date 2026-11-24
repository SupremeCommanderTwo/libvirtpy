"""The life of a domain: define, start, inspect, shut down, undefine."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient

with LibvirtClient(FakeLibvirt()) as client:
    print("hypervisor version:", client.get_version())

    # define_domain() stores the configuration and returns it as the daemon
    # keeps it: libvirt has filled in the UUID.
    domain = client.define_domain(make_domain("web1"))
    print(f"defined {domain.name}, uuid {domain.uuid}, running id: {domain.id}")

    # start_domain() takes any reference; the returned model is the live one.
    running = client.start_domain(domain)
    print(f"started: id {running.id}, state {client.get_domain_state(domain).name}")

    info = client.get_domain_info("web1")
    print(f"info: {info.vcpus} vCPUs, {info.memory_kib // 1024} MiB")

    client.shutdown_domain("web1")
    print("after shutdown:", client.get_domain_state("web1").name)

    client.undefine_domain("web1")
    print("domains left:", [d.name for d in client.list_domains()])
