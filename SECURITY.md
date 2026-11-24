# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem. Use GitHub's private
vulnerability reporting for this repository (Security tab > "Report a vulnerability").
Describe what you found and how to reproduce it; you will get an answer as soon as
possible.

## What counts

libvirtpy talks to libvirt daemons, sometimes over a network, so these matter most:

- parsing of data sent by a daemon (XDR, framing, SASL messages, XML);
- TLS and SSH handling (certificate checks, the quoting of the remote command);
- authentication (SASL mechanisms, credentials in memory or logs).

## Supported versions

Only the latest release receives fixes while the project is in alpha.
