# Atividade 2 — Aplicações web com perfis computacionais distintos

Três aplicações *backend* (Python 3 e FastAPI), cada uma com um perfil de carga dominante. Todas expõem `GET /health` e uma rota de trabalho com um parâmetro de intensidade.

| Arquivo | Perfil | Rota | Parâmetro | Porta padrão | Operação |
|---|---|---|---|---|---|
| `cpu_app.py` | CPU-bound | `/cpu?n=N` | `n` (1 a 5 000 000) | 8001 | Conta primos até `n` por divisão tentativa |
| `mem_app.py` | Memory-bound | `/mem?mb=M` | `mb` (1 a 256) | 8002 | Aloca `M` MB, percorre o buffer 20 vezes com busca vetorizada (`memchr`) e libera |
| `io_app.py` | IO-bound | `/io?kb=K` | `kb` (1 a 16 384) | 8003 | Grava `K` KB em blocos de 64 KiB, executa `fsync`, descarta do cache, relê e remove |

Cada resposta JSON inclui `tempo_servico_s` (tempo de processamento no servidor) e `pid` do processo que atendeu à requisição.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Na VM Ubuntu, se necessário: `sudo apt install python3-venv python3-pip`.

## Execução

```bash
python cpu_app.py                  # porta 8001
python mem_app.py                  # porta 8002
python io_app.py                   # porta 8003
```

Variáveis de ambiente opcionais:

- `PORT`: porta de escuta.
- `WORKERS`: número de processos do uvicorn (padrão 1). Como o Python possui o GIL, uma única instância utiliza apenas um núcleo; para que a aplicação CPU-bound se beneficie de mais vCPUs, defina `WORKERS` igual ao número de vCPUs da VM e registre essa escolha na metodologia.
- `IO_DIR` (apenas `io_app.py`): diretório dos arquivos temporários.

Exemplo: `PORT=8001 WORKERS=2 python cpu_app.py`.

## Teste rápido

```bash
curl http://localhost:8001/health
curl "http://localhost:8001/cpu?n=100000"
curl "http://localhost:8002/mem?mb=64"
curl "http://localhost:8003/io?kb=1024"
```

## Referência de intensidade (medições de um teste local, uma requisição por vez)

Valores indicativos, obtidos em outro hardware; as medições oficiais devem ser feitas na VM.

| Aplicação | Parâmetro | Tempo de serviço | Observação |
|---|---|---|---|
| CPU | `n=200000` | 0,135 s | CPU próxima de 100 %, memória constante |
| Memória | `mb=64` | 0,097 s | RSS do processo cresce cerca de 64 MiB; tempo proporcional a `mb` |
| Memória | `mb=256` | 0,571 s | RSS do processo cresce cerca de 256 MiB |
| E/S | `kb=16384` | 0,034 s | Disco do ambiente de teste muito rápido; na VM o tempo será maior |

## Observações metodológicas

1. **CPU-bound e GIL:** um processo Python executa código Python em um único núcleo por vez. Em cada cenário, defina `WORKERS` igual ao número de vCPUs da VM; caso contrário, aumentar as vCPUs não terá efeito.
2. **Memory-bound:** a varredura usa `bytearray.find`, implementado com `memchr` vetorizado, e atinge vazão próxima da largura de banda da memória (cerca de 13 GiB/s no ambiente de teste, contra 1,7 GiB/s com `bytearray.count`). A CPU aparece ocupada porque o núcleo permanece ativo enquanto espera os dados da RAM. O perfil é caracterizado sobretudo pelo consumo de RAM, proporcional a `mb` multiplicado pela concorrência: com 1 GB na VM, demandas elevadas levam à paginação (*swap*) ou ao encerramento do processo pelo *OOM killer*. Monitore `free -m` e `vmstat` durante os testes.
3. **IO-bound:** após o `fsync`, o arquivo é descartado do cache de páginas com `posix_fadvise(POSIX_FADV_DONTNEED)`, para que a leitura também vá ao disco. Essa chamada só existe no Linux; no Windows, a leitura sai do cache. Verifique ainda:
   - se o diretório temporário está em disco (`df -h /tmp`), e não em *tmpfs*; se necessário, use `IO_DIR`;
   - a configuração de *flush* do VirtualBox, que por padrão pode ignorar os pedidos de *flush* do convidado (chave `IgnoreFlush`, ajustável com `VBoxManage setextradata`). Registre a configuração utilizada.
4. **Concorrência no servidor:** as rotas são síncronas e executadas em um *pool* de 40 threads por processo (padrão do `anyio`). Acima de 40 × `WORKERS` requisições simultâneas, as demais aguardam em fila. A diferença entre o tempo de resposta medido no cliente e o `tempo_servico_s` corresponde ao tempo de espera.
5. **Reprodutibilidade:** mantenha os mesmos parâmetros de intensidade entre cenários e repita cada medição ao menos três vezes. Calibre o parâmetro na VM de menor provisionamento para um tempo de serviço de algumas dezenas de milissegundos.
6. **Compatibilidade:** o Ubuntu Server 22.04 usa Python 3.10, compatível com as versões fixadas. Execute o teste rápido dentro da VM antes dos experimentos.
7. **Aplicação sugerida para os experimentos na VM:** a CPU-bound, pois evidencia melhor o efeito da variação de vCPUs.
