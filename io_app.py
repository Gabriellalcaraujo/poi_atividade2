import os
import tempfile
import time
import uuid

import uvicorn
from fastapi import FastAPI, Query

app = FastAPI(title="App IO-bound")

DIRETORIO = os.environ.get("IO_DIR", tempfile.gettempdir())
os.makedirs(DIRETORIO, exist_ok=True)

TAMANHO_BLOCO_KB = 64
BLOCO = os.urandom(TAMANHO_BLOCO_KB * 1024)  # gerado uma única vez, reutilizado nas gravações


def descartar_cache(fd: int) -> None:
    """Remove o arquivo do cache de páginas, para que a leitura vá ao disco (Linux)."""
    if hasattr(os, "posix_fadvise"):
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)


def operar_arquivo(kb: int) -> int:
    caminho = os.path.join(DIRETORIO, f"poi_io_{uuid.uuid4().hex}.bin")
    try:
        blocos, resto_kb = divmod(kb, TAMANHO_BLOCO_KB)
        with open(caminho, "wb") as f:
            for _ in range(blocos):
                f.write(BLOCO)
            if resto_kb:
                f.write(BLOCO[: resto_kb * 1024])
            f.flush()
            os.fsync(f.fileno())
            descartar_cache(f.fileno())
        lidos = 0
        with open(caminho, "rb") as f:
            while True:
                dados = f.read(TAMANHO_BLOCO_KB * 1024)
                if not dados:
                    break
                lidos += len(dados)
        return lidos
    finally:
        if os.path.exists(caminho):
            os.remove(caminho)


@app.get("/health")
def health():
    return {"status": "ok", "app": "io", "pid": os.getpid()}


@app.get("/io")
def io(kb: int = Query(1024, ge=1, le=16_384)):
    inicio = time.perf_counter()
    lidos = operar_arquivo(kb)
    duracao = time.perf_counter() - inicio
    return {"kb": kb, "bytes_lidos": lidos, "tempo_servico_s": round(duracao, 6), "pid": os.getpid()}


if __name__ == "__main__":
    uvicorn.run(
        "io_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8003")),
        workers=int(os.environ.get("WORKERS", "1")),
        log_level="warning",
    )
