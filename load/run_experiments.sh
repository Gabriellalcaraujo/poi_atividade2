#!/usr/bin/env bash
# Roda no HOST (fora da VM). Uso:
#   SSH_TARGET=usuario@127.0.0.1 SSH_OPTS="-p 2222" \
#   ./run_experiments.sh http://127.0.0.1:8000/cpu cenario1_1cpu_1gb "5 10 20 40 80" 60
#
# Requer k6 no host. Se SSH_TARGET estiver definido, inicia ~/monitor.sh na VM
# a cada nível de demanda e copia o CSV de volta.
set -euo pipefail

URL=$1
SCEN=$2
RATES=$3
DUR=${4:-60}
COOLDOWN=${COOLDOWN:-15}
DIR=results/$SCEN
mkdir -p "$DIR"

for R in $RATES; do
  echo ">>> cenário=$SCEN demanda=${R} req/s duração=${DUR}s"
  MON=""
  if [ -n "${SSH_TARGET:-}" ]; then

    ssh ${SSH_OPTS:-} "$SSH_TARGET" "bash ~/monitor.sh /tmp/mon_$R.csv $((DUR + 6))" &
    MON=$!
    sleep 2
  fi

  k6 run -q -e URL="$URL" -e RATE="$R" -e DURATION="${DUR}s" \
         -e OUT="$DIR/rate_$R.json" load-test.js

  if [ -n "$MON" ]; then
    wait "$MON"
    # shellcheck disable=SC2086
    scp -q $(echo "${SSH_OPTS:-}" | sed 's/-p /-P /') "$SSH_TARGET:/tmp/mon_$R.csv" "$DIR/mon_$R.csv"
  fi
  sleep "$COOLDOWN"   
done
echo "Concluído. Resultados em $DIR"