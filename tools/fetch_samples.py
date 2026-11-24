"""Download libvirt's sample XML and RelaxNG schemas into ``.cache/libvirt``.

The corpus comes from the official release tarball of one pinned libvirt
version. Changing ``LIBVIRT_VERSION`` (and its ``TARBALL_SHA256``) is a
deliberate, reviewed change: verify the new tarball's GPG signature
(``<url>.asc``, signed by the libvirt release manager) before pinning its hash.

Only XML samples, schemas and protocol definitions are extracted; libvirt's
files are LGPL-licensed and are never committed to this repository.

Usage: ``python tools/fetch_samples.py [--force]``
"""

import argparse
import hashlib
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

LIBVIRT_VERSION = "12.9.0"
TARBALL_SHA256 = "dcf579d8a949f4cbf56820529d48f200382a48ea12855ffded7c16a189353cd7"
TARBALL_URL = f"https://download.libvirt.org/libvirt-{LIBVIRT_VERSION}.tar.xz"

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPOSITORY_ROOT / ".cache" / "libvirt"
VERSION_FILE_NAME = "VERSION"

# Directories of the tarball (relative to its top folder) whose files we keep,
# with the file suffixes to keep in each.
EXTRACTED_TREES = {
    PurePosixPath("src/conf/schemas"): (".rng",),
    PurePosixPath("tests"): (".xml",),
    PurePosixPath("examples/xml"): (".xml",),
    PurePosixPath("src/nwfilter/xml"): (".xml",),
    # The wire protocol definitions (XDR) and the error codes.
    PurePosixPath("src/remote"): (".x",),
    PurePosixPath("src/rpc"): (".x", ".pl"),
    PurePosixPath("include/libvirt"): (".h",),
}

DOWNLOAD_TIMEOUT_SECONDS = 120


class FetchError(Exception):
    """The corpus could not be downloaded or extracted."""


def cached_version() -> str | None:
    """Return the libvirt version in the cache, or ``None`` if there is none."""
    version_file = CACHE_DIR / VERSION_FILE_NAME
    if not version_file.is_file():
        return None
    return version_file.read_text(encoding="utf-8").strip()


def download_tarball(destination: Path) -> None:
    """Download the pinned tarball to ``destination`` and check its SHA-256.

    :param destination: the file to write the tarball to.
    :raises FetchError: if the checksum does not match the pinned one.
    """
    print(f"Downloading {TARBALL_URL}")

    with (
        urllib.request.urlopen(TARBALL_URL, timeout=DOWNLOAD_TIMEOUT_SECONDS) as reply,
        destination.open("wb") as tarball,
    ):
        shutil.copyfileobj(reply, tarball)

    actual_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    if actual_sha256 != TARBALL_SHA256:
        raise FetchError(
            f"SHA-256 mismatch for {TARBALL_URL}: "
            f"expected {TARBALL_SHA256}, got {actual_sha256}"
        )


def wanted_path(member: tarfile.TarInfo) -> PurePosixPath | None:
    """Return where to extract ``member`` inside the cache, or ``None`` to skip it.

    Only regular files with a plain relative path inside one of
    ``EXTRACTED_TREES`` are kept; links and unusual paths are skipped.

    :param member: an entry of the libvirt tarball.
    :returns: the path relative to the cache, without the tarball's top folder.
    """
    if not member.isfile():
        return None

    path = PurePosixPath(member.name)
    if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        return None

    relative = PurePosixPath(*path.parts[1:])  # drop "libvirt-<version>/"
    for tree, suffixes in EXTRACTED_TREES.items():
        if relative.is_relative_to(tree) and relative.suffix in suffixes:
            return relative
    return None


def extract_corpus(tarball_path: Path, destination: Path) -> int:
    """Extract the wanted files of the tarball into ``destination``.

    :param tarball_path: the downloaded ``.tar.xz`` file.
    :param destination: the directory to extract into.
    :returns: the number of files extracted.
    """
    count = 0

    with tarfile.open(tarball_path, mode="r:xz") as tarball:
        for member in tarball:
            relative = wanted_path(member)
            if relative is None:
                continue

            source = tarball.extractfile(member)
            if source is None:
                continue

            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            count += 1
    return count


def replace_cache(new_cache: Path) -> None:
    """Move ``new_cache`` to ``CACHE_DIR``, removing a previous corpus first.

    :param new_cache: the directory that holds the freshly extracted corpus.
    :raises FetchError: if ``CACHE_DIR`` exists but is not a corpus we wrote.
    """
    if CACHE_DIR.exists():
        if not (CACHE_DIR / VERSION_FILE_NAME).is_file():
            raise FetchError(f"{CACHE_DIR} exists but is not a corpus; not touching it")
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(new_cache), str(CACHE_DIR))


def fetch(*, force: bool) -> None:
    """Make sure ``CACHE_DIR`` holds the corpus of ``LIBVIRT_VERSION``.

    :param force: download again even if the cached version is the right one.
    """
    if cached_version() == LIBVIRT_VERSION and not force:
        print(f"{CACHE_DIR} already holds libvirt {LIBVIRT_VERSION}")
        return

    with tempfile.TemporaryDirectory(prefix="libvirtpy-corpus-") as work_dir:
        tarball_path = Path(work_dir) / "libvirt.tar.xz"
        download_tarball(tarball_path)

        new_cache = Path(work_dir) / "corpus"
        count = extract_corpus(tarball_path, new_cache)

        version_file = new_cache / VERSION_FILE_NAME
        version_file.write_text(LIBVIRT_VERSION + "\n", encoding="utf-8")
        replace_cache(new_cache)

    print(f"Extracted {count} files of libvirt {LIBVIRT_VERSION} into {CACHE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--force", action="store_true", help="download again even if cached"
    )

    arguments = parser.parse_args()

    try:
        fetch(force=arguments.force)
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
