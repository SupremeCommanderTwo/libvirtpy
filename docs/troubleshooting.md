# Errors and troubleshooting

## Exceptions

Everything the library raises on purpose derives from
{class}`~libvirtpy.errors.LibvirtPyError`.

| Class | When |
|---|---|
| `LibvirtError` | the daemon reported a failure; it has `message`, `code` (`virErrorNumber`) and `domain` |
| `NoDomainError`, `NoNetworkError`, `NoStoragePoolError`, `NoStorageVolumeError`, `NoSecretError`, `NoSnapshotError`, ... | the object does not exist |
| `ExistsError` | it exists already |
| `OperationInvalidError` | the object's state does not allow it |
| `InvalidArgumentError`, `NotSupportedError`, `AuthFailedError` | what they say |
| `ProtocolError` (`libvirtpy.rpc.session`) | the daemon sent something that is not libvirt RPC |
| `ConnectionLostError` (`libvirtpy.rpc.session`) | the connection ended (also a `ConnectionError`) |

```python
from libvirtpy.client import LibvirtError
from libvirtpy.rpc.errors import NoDomainError, OperationInvalidError

try:
    client.start_domain("vm")
except OperationInvalidError:
    pass  # already running
except NoDomainError:
    raise
except LibvirtError as error:
    print(error.code, error.domain, error.message)
```

## Cannot connect

- **`qemu:///system` is refused or hangs.** The client looks for the modular daemon
  sockets (`/run/libvirt/virtqemud-sock`) first, then `libvirtd`'s. Make sure one of the
  services runs (`systemctl status virtqemud.socket`). Your user needs access to the
  socket: usually membership in the `libvirt` group, or a polkit rule.
- **Permission denied on a session URI.** `qemu:///session` uses a socket under
  `$XDG_RUNTIME_DIR/libvirt/`; it exists only after the user daemon starts.
- **SSH.** The helper command on the host is `virt-ssh-helper`, or `nc -U` as a fallback;
  one of them must exist there. Test the same login by hand with `ssh user@host`.
- **TLS.** The client certificate, key and CA are looked up like libvirt does: root uses
  `/etc/pki/CA/cacert.pem` and `/etc/pki/libvirt/`, other users `~/.pki/libvirt/`, and
  `?pkipath=/dir` in the URI names one directory with `cacert.pem`, `clientcert.pem` and
  `clientkey.pem`. The daemon must accept TLS (`virtproxyd-tls.socket`, or `libvirtd
  --listen`).
- **SASL on plain TCP** is refused on purpose: there is no SASL security layer, so the
  credentials would travel unprotected. Use TLS or SSH.

## SELinux

On a host with SELinux enforcing, qemu processes can only write sockets under
`/run/libvirt/qemu` and files with the right label. If a backup, a save file or a
console socket fails with "permission denied", look at the audit log
(`ausearch -m avc -ts recent`) before blaming the library.

## A hang

A call that never returns usually waits for a reply that the daemon will not send. To
see where, run the script under `faulthandler`:

```python
import faulthandler

faulthandler.dump_traceback_later(30, exit=True)
```

and wrap the work in `try/finally` so that a killed script still cleans up what it
created.
