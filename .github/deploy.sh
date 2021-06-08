#!/bin/bash

while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -r|--role)
        DEPLOYMENT_ROLE="$2"
        shift 2
        ;;
        -e|--environment)
        ENVIRONMENT="$2"
        shift 2
        ;;
        *)    # unknown option
        echo "Unknown option supplied"
        exit 27
        ;;
    esac
done


ZONES=$(\
    bazelisk query \
    "kind(deployment_zone, attr(deployment_role, $DEPLOYMENT_ROLE,  //src/zones/...))" \
    --output label \
    )

for zone in "${ZONES[@]}"
do
    echo "Deploying into $zone...; fasten your seatbelts..."
    unset TARGETS
    TARGETS=$( \
            bazelisk query \
            "kind(deploy_*, \
            attr(deployment_zone, $zone , //...) \
            intersect
            attr(tags, $ENVIRONMENT, //...) \
            )" --output label \
        )
    # shellcheck disable=SC2206 
    TARGETS=($TARGETS)
    unset last_target
    last_target=${TARGETS[ ${#TARGETS[@]} - 1 ]}
    for target in "${TARGETS[@]}"
    do
        echo "Deploying $target...; we have lift off 🚀..."
        if [ "$target" == "$last_target" ];
        then
            bazelisk run "$target"
        else
            bazelisk run "$target" &
        fi
    done
     
done

# collect jobs
EXIT=0
for job in $(jobs -p)
do
    wait "$job" || (( EXIT=1 ))
done

exit "$EXIT"
