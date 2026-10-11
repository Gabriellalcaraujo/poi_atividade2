
#!/usr/bin/env bash
# Roda DENTRO da VM. Uso: ./monitor.sh saida.csv [segundos]   (0 = até Ctrl+C)

OUT=${1:-monitor.csv}
SECS=${2:-0}
 
echo "ts,cpu_user,cpu_sys,cpu_idle,cpu_wait,mem_used_mb,mem_avail_mb,swap_used_mb" > "$OUT"
i=0
while [ "$SECS" -eq 0 ] || [ "$i" -lt "$SECS" ]; do
  read -r r b swpd fr bf ch si so bi bo in cs us sy id wa st < <(vmstat 1 2 | tail -1)
  read -r used avail < <(free -m | awk '/Mem:/{print $3, $7}')
  echo "$(date +%s),$us,$sy,$id,$wa,$used,$avail,$((swpd / 1024))" >> "$OUT"
  i=$((i + 1))
done
