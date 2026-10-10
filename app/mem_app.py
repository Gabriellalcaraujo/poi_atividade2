import os
import time

import uvicorn
from fastapi import FastAPI, Query

app = FastAPI(title="App memory-bound")

VARREDURAS = 20


def processar_buffer(mb: int) -> int:
    buf = bytearray(mb * 1024 * 1024)  # alocação e escrita (zeros) de todas as páginas
    bytes_lidos = 0
    for _ in range(VARREDURAS):
        # Procura um byte inexistente: a busca (memchr, vetorizada) percorre o buffer
        # inteiro e é limitada pela largura de banda da memória.
        if buf.find(b"\x01") != -1:
            raise RuntimeError("buffer corrompido")
        bytes_lidos += len(buf)
    del buf
    return bytes_lidos


@app.get("/health")
def health():
    return {"status": "ok", "app": "mem", "pid": os.getpid()}


@app.get("/mem")
def mem(mb: int = Query(64, ge=1, le=256)):
    inicio = time.perf_counter()
    bytes_lidos = processar_buffer(mb)
    duracao = time.perf_counter() - inicio
    return {"mb": mb, "bytes_lidos": bytes_lidos, "tempo_servico_s": round(duracao, 6), "pid": os.getpid()}


if __name__ == "__main__":
    uvicorn.run(
        "mem_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8002")),
        workers=int(os.environ.get("WORKERS", "1")),
        log_level="warning",
    )
