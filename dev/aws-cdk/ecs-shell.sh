#!/bin/sh

# FIXME: these commands should be added somewhere in CDK instead!!!

set -e

CLUSTER=$(aws ecs list-clusters --output yaml | grep SURFCluster | cut -d '/' -f2)
[ -n "$CLUSTER" ] || (echo no cluster; exit 1)

TASK=$(aws ecs list-tasks --cluster $CLUSTER --output yaml | grep SURFCluster | cut -d '/' -f3)
[ -n "$TASK" ] || (echo no task; exit 1)

CMD="${1:-/bin/bash}"

aws ecs execute-command --cluster $CLUSTER --task $TASK --interactive --command "$CMD"

