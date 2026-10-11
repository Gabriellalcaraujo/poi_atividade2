"""
Lê results/<cenario>/rate_*.json e mon_*.csv, gera results/summary.csv e gráficos PNG.
"""
import glob
import json
import os

import matplotlib.pyplot as plt
import pandas as pd

WARMUP_SECS = 2  

rows = []
for f in glob.glob(os.path.join("results", "*", "rate_*.json")):
    scen = f.split(os.sep)[1]
    with open(f) as fh:
        d = json.load(fh)
    d["scenario"] = scen
    mon = f.replace("rate_", "mon_").replace(".json", ".csv")
    if os.path.exists(mon):
        m = pd.read_csv(mon).iloc[WARMUP_SECS:]
        cpu = 100 - m["cpu_idle"]
        d["cpu_avg"] = cpu.mean()
        d["cpu_max"] = cpu.max()
        d["iowait_avg"] = m["cpu_wait"].mean()
        d["mem_used_mb"] = m["mem_used_mb"].max()
        d["swap_used_mb"] = m["swap_used_mb"].max()
    rows.append(d)

df = pd.DataFrame(rows).sort_values(["scenario", "rate_target"])
if "servico_avg_ms" in df:
    df["espera_ms"] = df["avg_ms"] - df["servico_avg_ms"]
df.to_csv("results/summary.csv", index=False)
print(df.to_string(index=False))

metrics = [
    ("p95_ms", "Tempo de resposta p95 (ms)"),
    ("avg_ms", "Tempo de resposta médio (ms)"),
    ("servico_avg_ms", "Tempo de serviço médio no servidor (ms)"),
    ("espera_ms", "Tempo de espera médio (resposta - serviço) (ms)"),
    ("throughput", "Vazão efetiva (req/s)"),
    ("fail_rate", "Taxa de falhas"),
    ("cpu_avg", "Utilização média de CPU (%)"),
    ("mem_used_mb", "Memória usada - pico (MB)"),
]
for col, label in metrics:
    if col not in df:
        continue
    plt.figure(figsize=(7, 4.5))
    for scen, g in df.groupby("scenario"):
        plt.plot(g["rate_target"], g[col], marker="o", label=scen)
    plt.xlabel("Demanda (req/s)")
    plt.ylabel(label)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.savefig(f"results/{col}.png", dpi=150, bbox_inches="tight")
    plt.close()
print("Gráficos salvos em results/*.png")