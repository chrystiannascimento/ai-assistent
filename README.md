# Assistente de Voz Pessoal (Open Source, Self-Hosted)

Assistente virtual pessoal estilo Gemini/Bixby, rodando inteiramente em homelab
(mini PC + Docker), sem depender de nuvem para o caminho comum de uso.

## Arquitetura

- **Home Assistant** — esqueleto de automação, casa inteligente e pipeline de voz (Assist)
- **Wyoming protocol** — conecta wake word (openWakeWord), STT (Whisper) e TTS (Piper)
- **Ollama (`qwen3:4b`)** — orquestrador local, agente de conversação do HA
- **LiteLLM** — proxy/roteador com fallback do modelo local para modelos maiores (ex.: Claude) via tool-calling (`escalar`)
- **Microsoft Presidio** (analyzer + anonymizer) — pseudonimiza dados sensíveis antes de qualquer chamada escalada para fora da rede local, com reversão na resposta
- **HA Companion App + Tasker** — controle do celular (configuração, fora do escopo deste repositório)
- **App Android (`CallScreeningService`)** — atendimento de chamadas (esqueleto, fase futura)

## Requisitos

- Docker + Docker Compose
- Python 3.11+
- GPU opcional (recomendada para Whisper/Ollama, mas não obrigatória)

## Setup do ambiente Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # preencha com seus valores
```

## Rodando os testes

```bash
pytest -v
```

Testes que dependem de serviços externos reais (Home Assistant, Ollama, etc.)
são pulados automaticamente (`SKIPPED`) com uma mensagem explícita quando o
serviço não está acessível — nunca falham silenciosamente.

## Checando a saúde dos serviços

```bash
python scripts/check_dependencies.py            # saída colorida no terminal
python scripts/check_dependencies.py --json      # saída estruturada (para dashboards)
python scripts/check_dependencies.py --watch --interval 10   # checagem contínua
```

O script retorna exit code `1` se algum serviço **crítico** (Home Assistant ou
Ollama) estiver fora do ar — pensado para uso em CI/cron.

---

## Fases do projeto

### Fase 0 — Base

- `infra/docker-compose.yml` sobe Home Assistant e Ollama.
- `.env.example` documenta todas as variáveis necessárias (sem segredos reais).
- `scripts/check_dependencies.py` já existe, checando HA e Ollama.

```bash
docker compose -f infra/docker-compose.yml up -d
```

### Fase 1 — HA + Ollama

Configuração manual via UI (não é código, faça uma vez por instalação):

1. Suba os containers da Fase 0 (acima).
2. No Ollama, baixe o modelo orquestrador:
   ```bash
   docker exec -it ollama ollama pull qwen3:4b
   ```
3. No Home Assistant (`http://<host>:8123`), complete o onboarding inicial.
4. Gere um **Long-Lived Access Token** em *Perfil > Segurança* e coloque em
   `HA_LONG_LIVED_TOKEN` no `.env`.
5. Instale a integração **Ollama** em *Configurações > Dispositivos e Serviços
   > Adicionar Integração > Ollama*, apontando para `http://<host>:11434` e
   selecionando o modelo `qwen3:4b`.
6. Crie um pipeline de voz em *Configurações > Assistentes de Voz > Adicionar
   Assistente*, usando o agente de conversação Ollama recém-criado.

O smoke test `tests/test_health.py` confirma que o Ollama está no ar e que o
modelo `qwen3:4b` foi carregado.

### Fase 2 — Pipeline de voz (Wyoming)

- `infra/docker-compose.voice.yml` sobe openWakeWord, Whisper e Piper, cada um
  com `healthcheck` próprio.
- `scripts/check_dependencies.py` passa a checar as portas TCP dos três
  serviços (protocolo Wyoming não fala HTTP).

```bash
docker compose -f infra/docker-compose.voice.yml up -d
```

No Home Assistant, adicione as integrações **Wyoming Protocol** para cada um
dos três serviços (wake word, STT, TTS) apontando para host/porta do `.env`,
e selecione-as no pipeline de voz criado na Fase 1.

> Piper foi arquivado em out/2025 upstream; ainda funciona bem como TTS mas
> Kokoro e Coqui XTTS são candidatos a substituição futura (ver backlog).

### Fase 5 — Orquestrador e roteamento

- `orchestrator/config.yaml` — configuração do LiteLLM (`model_list` com o
  orquestrador local e o modelo de escalonamento, mais `fallbacks`).
- `orchestrator/tools/escalar.py` — definição da tool `escalar` exposta ao
  Ollama via function-calling.
- `orchestrator/router.py` — recebe uma pergunta, chama o Ollama local
  primeiro; se o modelo invocar `escalar`, repassa para o LiteLLM (que aplica
  o fallback configurado para o modelo maior).

```bash
docker compose -f infra/docker-compose.orchestrator.yml up -d
```

### Fase 6 — Pseudonimização

- `orchestrator/pseudonimizacao/presidio_client.py` — `anonimizar(texto)` e
  `reverter(texto, mapa)`, usando os serviços Presidio analyzer/anonymizer.
- O mapa placeholder→valor real vive em memória com TTL curto
  (`PSEUDONIMIZACAO_TTL_SEGUNDOS` no `.env`) — nunca é persistido em disco.
- Toda chamada ao LiteLLM (Fase 5) passa primeiro pela pseudonimização;
  a resposta é revertida antes de chegar ao usuário.

### Fase 7 — Esqueleto do app de chamadas (futuro)

- `android-call-screening/` contém apenas a estrutura mínima de um projeto
  Android com um `CallScreeningService` vazio.
- **Não implementado nesta fase:** streaming de áudio da chamada para o
  pipeline STT/LLM/TTS. Isso é o próximo passo depois que o esqueleto for
  validado manualmente no dispositivo.

---

## Backlog / melhorias futuras

Itens abaixo são intencionalmente **não implementados** ainda — registrados
aqui para não se perderem:

- **Observabilidade**: Grafana + Prometheus, ou um dashboard simples
  consumindo a saída `--json` do `check_dependencies.py`, para acompanhar
  latência de cada etapa do pipeline de voz e taxa de escalonamento do
  orquestrador ao longo do tempo.
- **Gestão de segredos**: substituir `.env` puro por `age` ou `sops` para
  criptografar chaves de API no repositório conforme mais provedores forem
  adicionados.
- **Avaliação da qualidade do roteamento**: dataset de perguntas rotuladas
  (deveria escalar / não deveria) para medir a precisão da decisão do
  `qwen3:4b` e ajustar o system prompt com dados.
- **Cache semântico**: cache de intents recorrentes (ex.: "que horas são",
  "ligar luz da sala") para evitar chamada ao LLM em perguntas repetidas.
- **Backup**: incluir os volumes do Home Assistant e do armazenamento do mapa
  de pseudonimização (Redis, se usado) na rotina de backup.
- **Isolamento de rede**: colocar Presidio, LiteLLM e Ollama em uma rede
  Docker separada da que expõe o HA à LAN.
- **Rate limiting**: guard na tool `escalar` para evitar loops de decisão que
  gerem chamadas excessivas (e custo) ao modelo grande.
- **Plano de degradação**: comportamento de falha graciosa (mensagem de erro,
  não travamento) para comandos de voz e chamadas quando o mini PC estiver
  indisponível.
