# Examples with a real libvirt connection

Unlike `examples/01`..`09` (an in-memory fake daemon), these talk to a real
libvirt daemon. They only **read**: connections are opened read-only and nothing
is created, changed or removed.

Run from the repository root; every script takes the URI as its argument or in
`$LIBVIRT_URI` and has `--help`.

| Script | URI | Shows |
|---|---|---|
| `01_local_system.py` | `qemu:///system` | this machine's daemons (modular or `libvirtd`), polkit |
| `02_local_session.py` | `qemu:///session` | your own unprivileged daemon |
| `03_ssh.py` | `qemu+ssh://user@host/system` | a remote host through `ssh`, no open port besides sshd |
| `04_tls.py` | `qemu+tls://host/system?pkipath=DIR` | a remote host with client certificates |
| `05_tls_with_sasl.py` | `qemu+tls://host/system` | TLS plus a login (SASL); credentials from the environment |
| `06_async_many_hosts.py` | several | the async client querying many hosts at once |
| `07_inspect_domains.py` | any | domains as typed models |
| `08_host_and_tuning.py` | any | host hardware and the tuning parameters of domains, as dicts |
| `09_watch_events.py` | any | domain events pushed by the daemon (start, stop, crash...) |
| `10_screenshot_and_download.py` | any | a screenshot of a running domain, or a volume copied to a file (streams) |

URI parameters: `keyfile`, `proxy`, `socket`, `netcat`, `command`, `no_tty`,
`known_hosts_verify` (ssh); `pkipath`, `no_verify` (tls). Not supported:
Kerberos (GSSAPI) and SASL over plain `qemu+tcp://`.
