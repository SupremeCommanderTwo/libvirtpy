"""Backup XML as a running job reports it."""

from libvirtpy.xml.backup import Backup
from tests.helpers.xmlcompare import differences


def test_running_backup_disk_keeps_the_index_the_daemon_adds() -> None:
    # libvirt 11.6 adds ``index`` to the disks of a running job (not in its schema).
    xml = (
        "<domainbackup mode='pull'><server transport='unix' socket='/s'/>"
        "<disks><disk name='vda' backup='yes' type='file' backupmode='full' index='4'>"
        "<scratch file='/t.qcow2'/></disk></disks></domainbackup>"
    )

    backup = Backup.from_xml(xml)

    assert backup.disks is not None and backup.disks.disks[0].index == 4
    assert list(differences(xml, backup.to_xml(encoding="unicode"))) == []
