#!/usr/bin/env bash
# Prepare a fresh VPS (Debian/Ubuntu or Fedora/RHEL family) as a libvirt host for
# the remote tests of libvirtpy: SSH, TLS and, optionally, SASL.
#
#   sudo ./setup_test_vps.sh --ssh-key "ssh-ed25519 AAAA... me@laptop" \
#                            --client-ip 203.0.113.7 [--sasl] [--host vps.example.org]
#
# It is safe to run again. It never touches sshd_config and never enables or
# resets a firewall: it only adds allow rules to one that is already running.
# Use --dry-run to see what it would do (no root needed).

set -euo pipefail

TEST_USER="lvxtest"
SSH_KEY=""
CLIENT_IP=""
WITH_SASL=0
DRY_RUN=0
HOSTS=()
PKI_DIR="/root/libvirtpy-client-pki"
SASL_USER="lvxtest"
SASL_PASSWORD=""

usage() {
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
    cat <<'USAGE'

Options:
  --ssh-key KEY       public key (text or file) allowed to log in as the test user
  --client-ip IP      your address: firewall rules allow SSH and TLS only from it
  --host NAME_OR_IP   name or address the TLS certificate is valid for (repeatable;
                      default: the host name and the addresses of this machine)
  --user NAME         test user for qemu+ssh (default: lvxtest)
  --sasl              require a SASL login on TLS (user lvxtest, random password)
  --sasl-password PW  use this SASL password instead of a random one
  --dry-run           print the commands instead of running them
USAGE
}

log() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '+ %s\n' "$*"
    else
        "$@"
    fi
}

write_file() { # write_file PATH MODE  (content on stdin)
    local path="$1" mode="$2"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '+ write %s (mode %s):\n' "$path" "$mode"
        sed 's/^/    /'
        return
    fi
    install -d "$(dirname "$path")"
    cat > "$path"
    chmod "$mode" "$path"
}

parse_arguments() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ssh-key) SSH_KEY="$2"; shift 2 ;;
            --client-ip) CLIENT_IP="$2"; shift 2 ;;
            --host) HOSTS+=("$2"); shift 2 ;;
            --user) TEST_USER="$2"; shift 2 ;;
            --sasl) WITH_SASL=1; shift ;;
            --sasl-password) SASL_PASSWORD="$2"; shift 2 ;;
            --dry-run) DRY_RUN=1; shift ;;
            -h | --help) usage; exit 0 ;;
            *) usage >&2; die "unknown option: $1" ;;
        esac
    done
    if [ -f "$SSH_KEY" ]; then SSH_KEY="$(cat "$SSH_KEY")"; fi
    if [ "$DRY_RUN" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then die "run as root (sudo)"; fi
    if [ -z "$SSH_KEY" ]; then warn "no --ssh-key: qemu+ssh will not be usable"; fi
    if [ -z "$CLIENT_IP" ]; then
        warn "no --client-ip: the TLS port will not be restricted by this script;"
        warn "restrict it yourself, a libvirt daemon must not be open to the internet"
    fi
}

install_packages() {
    log "Installing libvirt, qemu and tools"
    if command -v apt-get > /dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        run apt-get update -y
        run apt-get install -y libvirt-daemon-system libvirt-clients qemu-system-x86 \
            qemu-utils openssl sasl2-bin libsasl2-modules netcat-openbsd
    elif command -v dnf > /dev/null 2>&1; then
        run dnf install -y libvirt-daemon-driver-qemu libvirt-daemon-driver-storage-core \
            libvirt-daemon-driver-network libvirt-daemon-config-network libvirt-client \
            libvirt-daemon-common qemu-kvm-core qemu-img openssl cyrus-sasl-lib \
            cyrus-sasl-plain cyrus-sasl-md5 cyrus-sasl-scram nmap-ncat
    else
        die "no apt-get or dnf: install libvirt, qemu, openssl and cyrus-sasl by hand"
    fi
}

detect_daemon() { # sets DAEMON (virtproxyd | libvirtd) and MAIN_SERVICE
    if systemctl list-unit-files 2> /dev/null | grep '^virtproxyd.socket' > /dev/null; then
        DAEMON="virtproxyd"
    else
        DAEMON="libvirtd"
    fi
    log "Daemon style: $DAEMON"
}

start_daemons() {
    log "Starting libvirt"
    if [ "$DAEMON" = "virtproxyd" ]; then
        for name in virtqemud virtnetworkd virtstoraged virtnodedevd virtsecretd \
            virtinterfaced virtnwfilterd virtproxyd; do
            run systemctl enable --now "$name.socket" "$name-ro.socket" || true
        done
    else
        # sockets only: if libvirtd.service runs on its own, systemd refuses to
        # activate the TLS socket ("Socket service libvirtd.service already active")
        run systemctl enable --now libvirtd.socket libvirtd-ro.socket \
            libvirtd-admin.socket || true
    fi
    if [ ! -e /dev/kvm ]; then
        warn "no /dev/kvm: this VPS has no nested virtualisation. The daemons work,"
        warn "but define test domains with type='qemu' (software emulation), not 'kvm'."
    fi
}

create_test_user() {
    log "Creating the test user '$TEST_USER'"
    if ! id "$TEST_USER" > /dev/null 2>&1; then
        run useradd --create-home --shell /bin/bash "$TEST_USER"
    fi
    run usermod -aG libvirt "$TEST_USER" || warn "group 'libvirt' not found"
    if [ -n "$SSH_KEY" ]; then
        local home
        home="$(getent passwd "$TEST_USER" | cut -d: -f6 || true)"
        home="${home:-/home/$TEST_USER}"
        run install -d -m 700 -o "$TEST_USER" -g "$TEST_USER" "$home/.ssh"
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '+ add the key to %s/.ssh/authorized_keys\n' "$home"
        elif ! grep -qxF "$SSH_KEY" "$home/.ssh/authorized_keys" 2> /dev/null; then
            printf '%s\n' "$SSH_KEY" >> "$home/.ssh/authorized_keys"
            chown "$TEST_USER:$TEST_USER" "$home/.ssh/authorized_keys"
            chmod 600 "$home/.ssh/authorized_keys"
        fi
    fi
}

default_hosts() {
    if [ "${#HOSTS[@]}" -eq 0 ]; then
        HOSTS+=("$(hostname -f 2> /dev/null || hostname)")
        warn "the certificate will cover only this machine's own names and addresses;"
        warn "a VPS often hides its public IP (NAT): pass it with --host PUBLIC_IP"
        local address
        for address in $(hostname -I 2> /dev/null || true); do HOSTS+=("$address"); done
    fi
}

subject_alt_names() {
    local entries="" index=1 host
    for host in "${HOSTS[@]}"; do
        if [[ "$host" =~ ^[0-9.]+$ ]] || [[ "$host" == *:* ]]; then
            entries+="IP.$index = $host"$'\n'
        else
            entries+="DNS.$index = $host"$'\n'
        fi
        index=$((index + 1))
    done
    printf '%s' "$entries"
}

make_certificates() {
    log "Making the CA, the server certificate and a client certificate"
    if [ -f /etc/pki/CA/cacert.pem ] && [ -f /etc/pki/libvirt/servercert.pem ]; then
        warn "certificates exist in /etc/pki: keeping them (delete them to remake)"
        return
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '+ openssl: CA, server certificate for: %s, client certificate\n' "${HOSTS[*]}"
        printf '+ install them in /etc/pki and %s\n' "$PKI_DIR"
        return
    fi

    local work
    work="$(mktemp -d)"
    cd "$work"
    openssl req -x509 -newkey rsa:3072 -nodes -days 825 -sha256 \
        -subj "/CN=libvirtpy test CA" -keyout ca.key -out cacert.pem 2> /dev/null

    {
        printf 'basicConstraints = CA:FALSE\nextendedKeyUsage = serverAuth\n'
        printf 'subjectAltName = @alt\n[alt]\n'
        subject_alt_names
    } > server.ext
    openssl req -newkey rsa:3072 -nodes -subj "/CN=${HOSTS[0]}" \
        -keyout serverkey.pem -out server.csr 2> /dev/null
    openssl x509 -req -in server.csr -CA cacert.pem -CAkey ca.key -CAcreateserial \
        -days 825 -sha256 -extfile server.ext -out servercert.pem 2> /dev/null

    printf 'basicConstraints = CA:FALSE\nextendedKeyUsage = clientAuth\n' > client.ext
    openssl req -newkey rsa:3072 -nodes -subj "/CN=lvxtest-client" \
        -keyout clientkey.pem -out client.csr 2> /dev/null
    openssl x509 -req -in client.csr -CA cacert.pem -CAkey ca.key -CAcreateserial \
        -days 825 -sha256 -extfile client.ext -out clientcert.pem 2> /dev/null

    install -d -m 755 /etc/pki/CA /etc/pki/libvirt
    install -d -m 750 /etc/pki/libvirt/private
    install -m 644 cacert.pem /etc/pki/CA/cacert.pem
    install -m 644 servercert.pem /etc/pki/libvirt/servercert.pem
    install -m 600 serverkey.pem /etc/pki/libvirt/private/serverkey.pem
    install -m 644 clientcert.pem /etc/pki/libvirt/clientcert.pem
    install -m 600 clientkey.pem /etc/pki/libvirt/private/clientkey.pem

    install -d -m 700 "$PKI_DIR"
    install -m 644 cacert.pem clientcert.pem "$PKI_DIR/"
    install -m 600 clientkey.pem "$PKI_DIR/"
    cd /
    rm -rf "$work"
}

configure_tls() {
    log "Enabling TLS on port 16514"
    local config="/etc/libvirt/$DAEMON.conf"
    if [ "$DAEMON" = "virtproxyd" ]; then
        run systemctl enable --now virtproxyd-tls.socket
    else
        run systemctl stop libvirtd.service || true
        run systemctl enable --now libvirtd-tls.socket || warn \
            "no libvirtd-tls.socket: start libvirtd with --listen (see its unit)"
    fi
    if [ "$WITH_SASL" -eq 1 ]; then
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '+ set auth_tls = "sasl" in %s\n' "$config"
        else
            sed -i '/^auth_tls *=/d' "$config"
            printf 'auth_tls = "sasl"\n' >> "$config"
        fi
    fi
}

configure_sasl() {
    [ "$WITH_SASL" -eq 1 ] || return 0
    log "Configuring SASL (SCRAM-SHA-256, DIGEST-MD5, PLAIN over TLS)"
    if [ -z "$SASL_PASSWORD" ]; then
        SASL_PASSWORD="$(openssl rand -hex 12 2> /dev/null || echo "change-me-$$")"
    fi
    write_file /etc/sasl2/libvirt.conf 644 << 'CONF'
mech_list: scram-sha-256 digest-md5 plain
sasldb_path: /etc/libvirt/passwd.db
CONF
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '+ saslpasswd2 -a libvirt -f /etc/libvirt/passwd.db %s\n' "$SASL_USER"
    else
        printf '%s' "$SASL_PASSWORD" | saslpasswd2 -p -a libvirt \
            -f /etc/libvirt/passwd.db "$SASL_USER"
        chmod 640 /etc/libvirt/passwd.db
    fi
    # stop the daemon so that its sockets start it again with the new settings
    if [ "$DAEMON" = "virtproxyd" ]; then
        run systemctl stop virtproxyd.service 2> /dev/null || true
    else
        run systemctl stop libvirtd.service || true
    fi
}

verify_listening() {
    [ "$DRY_RUN" -eq 0 ] || return 0
    log "Checking that something listens on 16514"
    sleep 1
    if ss -ltn 2> /dev/null | grep ':16514 ' > /dev/null; then
        echo "ok: port 16514 is listening"
        return 0
    fi
    warn "nothing listens on 16514/tcp. Look at:"
    warn "  systemctl status virtproxyd-tls.socket libvirtd-tls.socket"
    warn "  journalctl -u virtproxyd -u libvirtd -n 50 --no-pager"
}

configure_firewall() {
    [ -n "$CLIENT_IP" ] || return 0
    log "Allowing SSH and TLS from $CLIENT_IP only (existing firewall, if any)"
    if command -v ufw > /dev/null 2>&1 && ufw status 2> /dev/null | grep active > /dev/null; then
        run ufw allow from "$CLIENT_IP" to any port 22 proto tcp
        run ufw allow from "$CLIENT_IP" to any port 16514 proto tcp
    elif command -v firewall-cmd > /dev/null 2>&1 && firewall-cmd --state > /dev/null 2>&1; then
        for port in 22 16514; do
            run firewall-cmd --permanent --add-rich-rule \
                "rule family=ipv4 source address=$CLIENT_IP port port=$port protocol=tcp accept"
        done
        run firewall-cmd --reload
        warn "firewalld: remove the generic 'ssh' service rule and do not open 16514 to all"
    else
        warn "no active ufw or firewalld: make sure 16514/tcp is reachable only from $CLIENT_IP"
        warn "(for example with the provider's firewall panel)"
    fi
}

summary() {
    local host="${HOSTS[0]}"
    log "Done. On your machine:"
    cat << SUMMARY

  # 1. the client certificates (TLS)
  scp -r root@$host:$PKI_DIR ~/.pki/libvirt-vps      # or use ?pkipath=
  # (files: cacert.pem, clientcert.pem, clientkey.pem)

  # 2. SSH
  python examples/real/03_ssh.py 'qemu+ssh://$TEST_USER@$host/system'

  # 3. TLS (certificate only)
  python examples/real/04_tls.py "qemu+tls://$host/system?pkipath=\$HOME/.pki/libvirt-vps"
SUMMARY
    if [ "$WITH_SASL" -eq 1 ]; then
        cat << SUMMARY

  # 4. TLS + SASL
  export LIBVIRT_USER=$SASL_USER
  export LIBVIRT_PASSWORD='$SASL_PASSWORD'
  python examples/real/05_tls_with_sasl.py "qemu+tls://$host/system?pkipath=\$HOME/.pki/libvirt-vps"
SUMMARY
    fi
    cat << 'SUMMARY'

  The certificate is valid for 825 days. Nothing was changed in sshd_config.
  When you are done: delete the test user (userdel -r), /etc/pki/libvirt,
  /etc/pki/CA/cacert.pem and the firewall rules, or destroy the VPS.
SUMMARY
}

main() {
    parse_arguments "$@"
    default_hosts
    install_packages
    detect_daemon
    start_daemons
    create_test_user
    make_certificates
    configure_tls
    configure_sasl
    verify_listening
    configure_firewall
    summary
}

main "$@"
