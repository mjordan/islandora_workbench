
# Sample Linux shell script (without a shebang line) to illustrate Workbench's "run_scripts" task.
# All this script does is print a message for each node ID.

# Test to make sure the expected argument, $2, is not empty. If it
# is empty, it exits with a non-zero exit code so Workbench can detect failure.
if [ -z $2 ]; then
echo "Error: second argument, node ID, was empty."
exit 1
else
echo "Processing node id $2."
fi
