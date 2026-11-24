# Connections

`LibvirtClient.open(uri)` connects in pure Python.

| URI | How |
|---|---|
| `qemu:///system`, `qemu:///session` | the UNIX sockets of this machine (modular daemons first, then `libvirtd`) |
| `qemu+ssh://user@host/system` | through `ssh`, running `virt-ssh-helper` or `nc -U` on the host |
| `qemu+tls://host/system` | TLS with a client certificate |
| `qemu+tcp://host/system` | plain TCP (use only with SASL on a trusted network) |

SASL logins use `sasl=SaslCredentials(user, password)`. SCRAM-SHA-256/1, DIGEST-MD5 and
PLAIN are implemented with the standard library; GSSAPI is not supported. There is no
SASL security layer, so SASL is refused on plain TCP and used on UNIX sockets, TLS and
SSH.

```python
from libvirtpy.client import LibvirtClient, SaslCredentials

client = LibvirtClient.open(
    "qemu+tls://host/system", sasl=SaslCredentials("admin", "secret")
)
```

```{note}
SSH, TLS and TLS with a SASL login are verified against a real remote libvirt 12
daemon (Ubuntu 26.04), as well as against a fake RPC server in the test suite. Plain
TCP, and the DIGEST-MD5 and PLAIN mechanisms against a real daemon, are covered by the
fake server only.
```

## Setting up a host to test against

`tools/setup_test_vps.sh` prepares a fresh Debian, Ubuntu or Fedora-family server for
remote tests: libvirt and qemu, a test user for SSH, a CA with server and client
certificates for TLS, optional SASL, and firewall rules for your address. Run it with
`--dry-run` first to see what it does. Then run the scripts in `examples/real/` with the
URIs it prints.
