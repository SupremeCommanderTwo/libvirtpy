"""What goes wrong, and how it looks in Python."""

from common import make_domain

from libvirtpy.client import FakeLibvirt, LibvirtClient, LibvirtError
from libvirtpy.rpc.errors import (
    ExistsError,
    NoDomainError,
    OperationInvalidError,
)

client = LibvirtClient(FakeLibvirt())

# A missing object has its own exception class.
try:
    client.lookup_domain("nope")
except NoDomainError as error:
    print("no such domain:", error.message)

# So does a state error: the domain exists but cannot do that now.
client.define_domain(make_domain("svc1"))
try:
    client.shutdown_domain("svc1")
except OperationInvalidError as error:
    print("cannot shut down a stopped domain:", error.message)

# Every class is a LibvirtError, which keeps the daemon's numbers.
try:
    client.destroy_domain("svc1")
except LibvirtError as error:
    print(f"code {error.code}, error class {type(error).__name__}")


# Handle one case, let the others through.
def start_if_needed(name: str) -> None:
    try:
        client.start_domain(name)
    except OperationInvalidError:
        print(f"{name} was already running")


start_if_needed("svc1")
start_if_needed("svc1")

# A name that exists twice cannot be created twice.
try:
    client.create_domain(make_domain("svc1"))
except ExistsError as error:
    print("exists:", error.message)
