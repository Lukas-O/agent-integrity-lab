#!/usr/bin/env bash
set -euo pipefail

# This setup belongs only on the disposable GitHub-hosted runner.
if [[ ${GITHUB_ACTIONS:-} != true || ${RUNNER_ENVIRONMENT:-} != github-hosted ]]; then
  echo 'This script requires a GitHub-hosted Actions runner.' >&2
  exit 1
fi

probe() {
  # A trusted executable tests the same namespace setup, before any candidate runs.
  /usr/bin/bwrap --unshare-user --unshare-all --disable-userns \
    --die-with-parent --new-session --cap-drop ALL \
    --ro-bind / / -- /usr/bin/true
}

if probe; then
  echo 'Bubblewrap namespace setup already works.'
  exit 0
fi

if [[ $(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null) != 1 ]]; then
  echo 'Sandbox preflight failed without the expected AppArmor restriction.' >&2
  exit 1
fi

# Ubuntu documents a per-executable userns allowance:
# https://documentation.ubuntu.com/release-notes/24.04/
# Keep the system-wide restriction enabled; permit only this sandbox executable.
sudo tee /etc/apparmor.d/agent-integrity-bwrap >/dev/null <<'PROFILE'
abi <abi/4.0>,
include <tunables/global>
profile agent-integrity-bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
}
PROFILE
sudo apparmor_parser --replace /etc/apparmor.d/agent-integrity-bwrap
probe
echo 'Bubblewrap namespace setup works with its scoped AppArmor allowance.'
