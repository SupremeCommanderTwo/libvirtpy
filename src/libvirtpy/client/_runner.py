"""Drives an ``Operation`` with a blocking or an awaitable transport call."""

from collections.abc import Awaitable, Callable
from typing import TypeVar, cast

from libvirtpy.client.transport import Operation, Request
from libvirtpy.rpc.errors import LibvirtError

__all__ = ["run_async", "run_sync"]

T = TypeVar("T")


def run_sync[T](operation: Operation[T], call: Callable[[Request], object]) -> T:
    """Run an operation, sending each request it yields with ``call``.

    An error from ``call`` is thrown into the operation, which may handle it.

    :param operation: the operation to run.
    :param call: sends one request and returns its reply.
    :returns: the operation's result.
    :raises LibvirtError: if the operation does not handle an error.
    """
    try:
        request = next(operation)
        while True:
            try:
                reply = call(request)
            except LibvirtError as error:
                request = operation.throw(error)
            else:
                request = operation.send(reply)
    except StopIteration as stop:
        return cast(T, stop.value)


async def run_async[T](
    operation: Operation[T], call: Callable[[Request], Awaitable[object]]
) -> T:
    """Run an operation, awaiting ``call`` for each request it yields.

    :param operation: the operation to run.
    :param call: sends one request and returns an awaitable of its reply.
    :returns: the operation's result.
    :raises LibvirtError: if the operation does not handle an error.
    """
    try:
        request = next(operation)
        while True:
            try:
                reply = await call(request)
            except LibvirtError as error:
                request = operation.throw(error)
            else:
                request = operation.send(reply)
    except StopIteration as stop:
        return cast(T, stop.value)
