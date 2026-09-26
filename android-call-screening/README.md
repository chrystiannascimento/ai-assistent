# Esqueleto — App de Triagem de Chamadas

Estrutura mínima de um projeto Android (Gradle + Kotlin) com um
`CallScreeningService` que apenas permite todas as chamadas, sem lógica de
triagem ou streaming de áudio ainda.

## O que existe

- `AssistenteCallScreeningService.kt` — servico registrado no manifest via
  `android.telecom.CallScreeningService`, com `onScreenCall` implementado de
  forma passiva (nunca bloqueia ou rejeita).

## O que falta (próximos passos, fora do escopo desta fase)

1. Solicitar ao usuário, via `RoleManager.ROLE_CALL_SCREENING`, que este app
   seja definido como app de triagem de chamadas padrão do sistema.
2. Capturar o áudio da chamada em andamento (API de telefonia não expõe isso
   diretamente ao `CallScreeningService` — vai exigir uma abordagem separada,
   provavelmente via `InCallService` + `VoIP`/acessibilidade, a pesquisar).
3. Encaminhar o áudio capturado para o pipeline Wyoming (STT -> orquestrador
   -> TTS) já usado pelo assistente de voz doméstico.
4. Decidir a política de bloqueio (lista de contatos, heurísticas, pergunta
   ao usuário em tempo real).

Este projeto não builda sozinho sem o Android SDK e o Gradle wrapper
instalados — não faz parte do `pytest`/`check_dependencies.py` deste
repositório.
