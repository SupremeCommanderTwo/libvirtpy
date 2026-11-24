"""Save a screenshot of a running domain, or download a storage volume.

Both are read-only streams: the daemon sends the bytes and the client writes them
to a file.

    python examples/real/10_screenshot_and_download.py screenshot vm shot.png
    python examples/real/10_screenshot_and_download.py download POOL VOLUME out.img
"""

import argparse
import shutil
import sys

from common import run

from libvirtpy.client import LibvirtClient


def screenshot(client: LibvirtClient, domain: str, target: str) -> None:
    """Save a screenshot of a running domain.

    :param client: an open client.
    :param domain: the domain name; it must be running.
    :param target: the file to write.
    """
    with client.take_domain_screenshot(domain) as image, open(target, "wb") as output:
        shutil.copyfileobj(image, output)
    print(f"saved the screen of {domain} ({image.reply}) to {target}")


def download(client: LibvirtClient, pool: str, volume: str, target: str) -> None:
    """Copy a storage volume to a file.

    :param client: an open client.
    :param pool: the storage pool name.
    :param volume: the volume name.
    :param target: the file to write.
    """
    with client.download_pool_volume(pool, volume) as source, open(target, "wb") as out:
        size = shutil.copyfileobj(source, out) or out.tell()
    print(f"saved {pool}/{volume} to {target} ({size} bytes)")


def main() -> int:
    """Run the example.

    :returns: the exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--uri", default="qemu:///system", help="libvirt URI")
    commands = parser.add_subparsers(dest="command", required=True)

    shot = commands.add_parser("screenshot", help="screenshot of a running domain")
    shot.add_argument("domain")
    shot.add_argument("target")
    copy = commands.add_parser("download", help="copy a volume to a file")
    copy.add_argument("pool")
    copy.add_argument("volume")
    copy.add_argument("target")
    arguments = parser.parse_args()

    def work() -> None:
        with LibvirtClient.open(arguments.uri, read_only=True) as client:
            if arguments.command == "screenshot":
                screenshot(client, arguments.domain, arguments.target)
            else:
                download(client, arguments.pool, arguments.volume, arguments.target)

    return run(work)


if __name__ == "__main__":
    sys.exit(main())
