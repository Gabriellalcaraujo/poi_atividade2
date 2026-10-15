#!/usr/bin/env bash
# Roda no HOST. Executa os cenários da aplicação Memory-bound (M1–M4):
# para cada um, desliga a VM, ajusta vCPUs/limite/RAM, liga, sobe mem_app.py
# e roda run_experiments.sh REPS vezes.
# Uso: ./run_mem_scenarios.sh [cenários...]   (padrão: M1 M2 M3 M4)
set -euo pipefail
cd "$(dirname "$0")"

VM=${VM:-minha_vm}
SSH_TARGET=${SSH_TARGET:-osboxes@127.0.0.1}
SSH_OPTS=${SSH_OPTS:-"-p 2222"}
URL=${URL:-"http://127.0.0.1:8002/mem?mb=64"}
RATES=${RATES:-"2 4 6 8 10 12"}
DUR=${DUR:-30}
REPS=${REPS:-3}
export SSH_TARGET SSH_OPTS COOLDOWN=${COOLDOWN:-15}

# nome: vCPUs limite_cpu RAM_MB WORKERS
declare -A CFG=(
  [M1]="1 100 512 1"
  [M2]="1 100 1024 1"
  [M3]="1 100 2048 1"
  [M4]="2 100 2048 2"
)

vm_ssh() { ssh $SSH_OPTS -o BatchMode=yes -o ConnectTimeout=5 "$SSH_TARGET" "$@"; }

vm_off() {
  VBoxManage showvminfo "$VM" --machinereadable | grep -q '^VMState="running"' || return 0
  VBoxManage controlvm "$VM" acpipowerbutton
  for _ in $(seq 60); do
    VBoxManage showvminfo "$VM" --machinereadable | grep -q '^VMState="poweroff"' && return 0
    sleep 2
  done
  VBoxManage controlvm "$VM" poweroff
  sleep 3
}

start_app() {
  local workers=$1
  vm_ssh "pkill -f '[m]em_app.py'" || true
  sleep 1
  vm_ssh "cd ~/poi_atividade2/app && \
    WORKERS=$workers setsid -f .venv/bin/python mem_app.py > ~/mem_app.log 2>&1 < /dev/null"
  for _ in $(seq 30); do
    curl -sf -m 2 http://127.0.0.1:8002/health > /dev/null && return 0
    sleep 1
  done
  echo "mem_app não respondeu" >&2; return 1
}

[ $# -gt 0 ] || set -- M1 M2 M3 M4
for S in "$@"; do
  read -r CPUS CAP MEM WORKERS <<< "${CFG[$S]}"
  echo "=== $S: ${CPUS} vCPU, limite ${CAP}%, ${MEM} MB, WORKERS=${WORKERS}"
  vm_off
  VBoxManage modifyvm "$VM" --cpus "$CPUS" --cpuexecutioncap "$CAP" --memory "$MEM"
  VBoxManage startvm "$VM" --type headless
  until vm_ssh true 2> /dev/null; do sleep 3; done
  vm_ssh "nproc; free -m" | tee "results_${S}_vm.txt"
  for R in $(seq "$REPS"); do
    start_app "$WORKERS"
    ./run_experiments.sh "$URL" "${S}_r${R}" "$RATES" "$DUR"
  done
  mkdir -p "results/${S}_r1" && mv "results_${S}_vm.txt" "results/${S}_r1/vm_config.txt"
done
echo "Todos os cenários concluídos."
