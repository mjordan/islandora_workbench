#!/usr/bin/env bash
# Runs INSIDE the ISLE "drupal" container (see setup-isle-test-env.sh, which pipes this file in).
# Configures Drupal for the Islandora Workbench integration tests. Safe to run repeatedly.
#
# Environment (all optional):
#   WB_PERMISSIONS        Comma-separated permissions for the "workbench_user" role (required for the role step).
#   WB_ADMIN_PASSWORD     Password for the "admin" user (default: admin).
#   WB_TEST_USER          Name of the non-admin test user (default: test-user).
#   WB_TEST_USER_PASSWORD Its password (default: testPassword).
#   WB_ROLE               Role name (default: workbench_user).
#   WB_MODULE_CONFIG_DIR  Where the integration module's optional config lives.

set -euo pipefail

WB_ADMIN_PASSWORD="${WB_ADMIN_PASSWORD:-admin}"
WB_TEST_USER="${WB_TEST_USER:-test-user}"
WB_TEST_USER_PASSWORD="${WB_TEST_USER_PASSWORD:-testPassword}"
WB_ROLE="${WB_ROLE:-workbench_user}"
WB_MODULE_CONFIG_DIR="${WB_MODULE_CONFIG_DIR:-/var/www/drupal/web/modules/contrib/islandora_workbench_integration/config/optional}"

step() { printf '\n==> %s\n' "$*"; }

step "Disabling standalone media URLs"
drush config:set media.settings standalone_url FALSE -y
drush cr

step "Importing Islandora default migrations"
drush migrate:import --userid=1 --tag=islandora -y

step "Allowing .jpg in the generic File media type"
EXTS="$(drush config:get field.field.media.file.field_media_file settings.file_extensions --format=string)"
if printf '%s' "$EXTS" | grep -qw "jpg"; then
  echo "jpg already present"
else
  echo "Updating extensions to: $EXTS jpg"
  drush config:set field.field.media.file.field_media_file settings.file_extensions "$EXTS jpg" -y
fi

step "Importing Islandora Workbench Integration configuration"
drush config:import --partial --source="$WB_MODULE_CONFIG_DIR" -y
drush cr

step "Setting the admin password"
drush user:password admin "$WB_ADMIN_PASSWORD"

step "Creating the ${WB_ROLE} role"
if drush role:list --format=json | grep -q "\"${WB_ROLE}\""; then
  echo "Role ${WB_ROLE} already exists"
else
  drush role:create "${WB_ROLE}"
fi
if [ -n "${WB_PERMISSIONS:-}" ]; then
  drush role:perm:add "${WB_ROLE}" "${WB_PERMISSIONS}"
else
  echo "WB_PERMISSIONS is empty; not changing the role's permissions" >&2
fi

step "Creating the ${WB_TEST_USER} user"
if drush user:information "${WB_TEST_USER}" >/dev/null 2>&1; then
  echo "User ${WB_TEST_USER} already exists; resetting its password"
  drush user:password "${WB_TEST_USER}" "${WB_TEST_USER_PASSWORD}"
else
  drush user:create "${WB_TEST_USER}" --mail='test@noreply.com' --password="${WB_TEST_USER_PASSWORD}"
fi
drush user:role:add "${WB_ROLE}" "${WB_TEST_USER}"

echo
echo "Drupal provisioned for the Islandora Workbench integration tests."
