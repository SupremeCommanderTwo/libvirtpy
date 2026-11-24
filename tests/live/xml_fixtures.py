"""Big XML documents for the live round-trip tests (long lines are fine here)."""

RICH_DOMAIN = """<domain type='kvm'><name>{name}</name><memory unit='MiB'>128</memory>
  <currentMemory unit='MiB'>96</currentMemory><vcpu placement='static' current='1'>2</vcpu>
  <iothreads>1</iothreads>
  <os><type arch='x86_64' machine='q35'>hvm</type><boot dev='hd'/></os>
  <features><acpi/><apic/><vmport state='off'/></features><cpu mode='host-passthrough'/>
  <clock offset='utc'><timer name='rtc' tickpolicy='catchup'/></clock>
  <on_poweroff>destroy</on_poweroff><on_reboot>restart</on_reboot><on_crash>destroy</on_crash>
  <devices>
    <disk type='file' device='disk'><driver name='qemu' type='qcow2' cache='none' io='threads'
      discard='unmap'/><source file='{disk}'/><target dev='vda' bus='virtio'/></disk>
    <disk type='file' device='cdrom'><driver name='qemu' type='raw'/><target dev='sdb' bus='sata'/>
      <readonly/></disk>
    <controller type='usb' model='qemu-xhci'/><controller type='scsi' model='virtio-scsi'/>
    <interface type='network'><source network='{network}'/><mac address='52:54:00:aa:00:01'/>
      <model type='virtio'/><bandwidth><inbound average='1000' peak='2000' burst='1024'/>
      </bandwidth></interface>
    <interface type='user'><mac address='52:54:00:aa:00:02'/><model type='e1000e'/></interface>
    <serial type='pty'><target type='isa-serial' port='0'><model name='isa-serial'/></target></serial>
    <console type='pty'><target type='serial' port='0'/></console>
    <channel type='unix'><target type='virtio' name='org.qemu.guest_agent.0'/></channel>
    <channel type='spicevmc'><target type='virtio' name='com.redhat.spice.0'/></channel>
    <input type='tablet' bus='usb'/><input type='keyboard' bus='ps2'/>
    <graphics type='spice' autoport='yes'><listen type='address'/><image compression='off'/></graphics>
    <graphics type='vnc' port='-1' autoport='yes'/>
    <sound model='ich9'/><audio id='1' type='none'/>
    <video><model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/></video>
    <redirdev bus='usb' type='spicevmc'/><watchdog model='itco' action='reset'/>
    <memballoon model='virtio'><stats period='5'/></memballoon>
    <rng model='virtio'><backend model='random'>/dev/urandom</backend></rng>
    <panic model='isa'/>
  </devices></domain>"""


EXOTIC_DOMAINS = {
    "tpm": ("", "<tpm model='tpm-crb'><backend type='emulator' version='2.0'/></tpm>"),
    "uefi": ("firmware='efi'", ""),
    "tuning": (
        "",
        "",
    ),
    "numa-topology": ("", ""),
    "hot-plug memory": (
        "",
        "<memory model='dimm'><target><size unit='MiB'>128</size><node>0</node></target></memory>",
    ),
    "sound and video": (
        "",
        "<video><model type='virtio' heads='1' primary='yes'><acceleration accel3d='no'/></model></video>"
        "<sound model='ich9'><codec type='duplex'/></sound><input type='mouse' bus='ps2'/>",
    ),
}
EXOTIC_TOP = {
    "tuning": (
        "<cputune><shares>2048</shares><period>100000</period><quota>-1</quota>"
        "<vcpupin vcpu='0' cpuset='0-1'/><vcpupin vcpu='1' cpuset='2'/>"
        "<emulatorpin cpuset='0-3'/><vcpusched vcpus='0' scheduler='fifo' priority='1'/></cputune>"
        "<numatune><memory mode='strict' nodeset='0'/></numatune>"
        "<blkiotune><weight>300</weight></blkiotune>"
        "<memtune><hard_limit unit='MiB'>512</hard_limit><soft_limit unit='MiB'>300</soft_limit></memtune>"
        "<memoryBacking><source type='memfd'/><access mode='shared'/></memoryBacking>"
        "<metadata><note xmlns:n='urn:lvx:test'><n:owner>test</n:owner></note></metadata>"
        "<sysinfo type='smbios'><system><entry name='manufacturer'>LVX</entry></system></sysinfo>"
        "<seclabel type='dynamic' model='selinux' relabel='yes'/>"
        "<resource><partition>/machine</partition></resource>"
    ),
    "numa-topology": (
        "<cpu mode='custom' match='exact'><model fallback='allow'>qemu64</model>"
        "<topology sockets='1' dies='1' cores='2' threads='1'/>"
        "<numa><cell id='0' cpus='0-1' memory='256' unit='MiB'/></numa></cpu>"
    ),
    "hot-plug memory": (
        "<maxMemory slots='4' unit='MiB'>1024</maxMemory><cpu mode='host-model'>"
        "<numa><cell id='0' cpus='0-1' memory='256' unit='MiB'/></numa></cpu>"
    ),
}
