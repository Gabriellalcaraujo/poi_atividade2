"""Aplicação CPU-bound.

Rota /cpu?n=N: conta os números primos menores ou iguais a N por divisão
tentativa em Python puro. O trabalho é limitado por CPU (sem E/S e com
memória desprezível). A intensidade cresce de forma aproximadamente
proporcional a N^1,5 / ln(N).

Variáveis de ambiente:
    PORT     porta de escuta (padrão 8001)
    WORKERS  número de processos do uvicorn (padrão 1)
"""
import math
import os
import time

import uvicorn
from fastapi import FastAPI, Query

app = FastAPI(title="App CPU-bound")


def contar_primos(n: int) -> int:
    if n < 2:
        return 0
    total = 1  # o número 2
    for candidato in range(3, n + 1, 2):
        limite = math.isqrt(candidato)
        for divisor in range(3, limite + 1, 2):
            if candidato % divisor == 0:
                break
        else:
            total += 1
    return total


@app.get("/health")
def health():
    return {"status": "ok", "app": "cpu", "pid": os.getpid()}


@app.get("/cpu")
def cpu(n: int = Query(50_000, ge=1, le=5_000_000)):
    inicio = time.perf_counter()
    primos = contar_primos(n)
    duracao = time.perf_counter() - inicio
    return {"n": n, "primos": primos, "tempo_servico_s": round(duracao, 6), "pid": os.getpid()}


if __name__ == "__main__":
    uvicorn.run(
        "cpu_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8001")),
        workers=int(os.environ.get("WORKERS", "1")),
        log_level="warning",
    )
