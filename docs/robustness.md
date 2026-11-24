# Timeouts, keepalive and slow readers

A client talks to a process that can hang, a network that can drop silently, and
events that arrive faster than you read them. Three settings of `open()` keep that
under control.

## Dead daemons: keepalive

Like libvirt's own client, libvirtpy pings the daemon when it has been silent.

```python
client = LibvirtClient.open(
    "qemu+tls://host/system",
    keepalive_interval=5.0,  # seconds of silence before a ping (the default)
    keepalive_count=5,  # unanswered pings before giving up (the default)
)
```

A daemon (or a network) that stays silent for `keepalive_interval * (keepalive_count +
1)` seconds, 30 by default, ends the connection: every waiting call and every
subscription fails with {class}`~libvirtpy.rpc.session.ConnectionLostError`, and later
calls fail at once. Pass `keepalive_interval=None` to turn it off. A *busy* daemon that
still answers pings is never given up, however long a call takes.

Without the `reconnect` option (next section) a lost connection stays lost: open a
new client.

## Automatic reconnect

```python
client = LibvirtClient.open(
    "qemu+ssh://root@host/system",
    reconnect=True,
    reconnect_attempts=5,  # tries before giving up (the default)
    reconnect_delay=1.0,  # seconds before the 2nd try, doubling, at most 30 s
)
```

With `reconnect=True`, a call made after the connection was lost opens a new one
(connecting, authenticating and opening again, over SSH, TLS or a socket) and goes on:
the first attempt is immediate, the next ones wait `reconnect_delay`, twice that, and
so on. If every attempt fails, the call raises `ConnectionError("cannot reconnect after
N attempts: ...")`; a refused login (`AuthFailedError`) is not retried.

What is, and is not, carried over:

| | After a reconnect |
|---|---|
| The next call | goes through on the new connection |
| The call that was running when the connection broke | **fails** with `ConnectionLostError`: libvirt may have done it or not, so the library never repeats it for you |
| Domains, networks, ... you hold as models | still valid: they are identified by name and UUID |
| Event subscriptions | registered again on the new connection and keep delivering; `subscription.reconnects` counts it. **Events sent while the connection was down are lost**, so re-read the state you care about |
| Open streams (console, upload, download) | end with an error; open them again |
| `client.close()` | stops reconnecting for good |

If a subscription cannot be restored, it ends with the `ConnectionError` instead.

Combine it with the keepalive: the keepalive is what notices a connection that dropped
silently, and the reconnect is what replaces it.

## Slow calls: timeouts

By default a call waits as long as it takes, because a volume wipe or a big upload can
be slow. To bound it:

```python
from libvirtpy.rpc.session import CallTimeoutError

client = LibvirtClient.open("qemu:///system", timeout=30)
try:
    client.get_hostname()
except CallTimeoutError:
    ...  # the connection is still usable
```

`CallTimeoutError` is also a `TimeoutError`. A reply that arrives after the timeout is
dropped quietly. With the async client, cancelling a call (`asyncio.wait_for`, a
cancelled task) is safe in the same way.

## Slow readers: bounded event queues

A subscription keeps at most `max_events` events (10,000 by default) for a reader that
has not caught up. When it is full the **oldest** event is dropped and counted:

```python
with client.events("domain", max_events=1000) as events:
    for event in events:
        handle(event)
    print(events.dropped, "events were lost")
```

If you cannot afford to lose any, read fast and hand the events to your own queue.

## Hostile input

The decoders are fuzz-tested: whatever bytes a daemon (or something pretending to be
one) sends, the library raises its own errors (`LibvirtPyError` and subclasses), never
an `IndexError` or the like, and a SCRAM server cannot make the client compute for
minutes with a huge iteration count.
