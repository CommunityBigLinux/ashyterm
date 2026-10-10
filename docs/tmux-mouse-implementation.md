# Implementação: roteamento da roda por modo de mouse

Causa raiz e evidências em `tmux-mouse-diagnosis.md`.

## Regra

```text
Ctrl + roda                         → zoom da fonte (inalterado)
modo "native"                       → GTK/VTE (inalterado)
wheel_reaches_application() == True → VTE (relatório de mouse ou setas)
caso contrário                      → rolagem própria do Ashy no histórico
```

`wheel_reaches_application(terminal, adjustment)` em
`terminal/scroll_mode_guard.py` retorna `True` quando:

1. o PTY ativou um modo de rastreamento (9, 1000, 1001, 1002 ou 1003) —
   **mesmo com histórico**; ou
2. não há histórico (`upper - lower <= page_size`) — fallback para PTYs não
   observados (tela alternativa: o VTE converte a roda em setas).

A mesma função decide nos três pontos que antes repetiam a comparação do
`Adjustment`: `ScrollHandler._on_terminal_scroll` (quem fica com o evento),
`ApplicationScrollHandler._scale_delta` (aplicar a sensibilidade do usuário ao
relatório) e `ApplicationScrollMomentum.get_vadjustment` (continuar a inércia).

## Estado por terminal

`ScrollModeGuard.for_terminal(terminal)` guarda um único `ScrollModeGuard` em
`terminal._ashy_mode_guard`. Ele pertence ao fluxo de saída, não ao
controlador de rolagem: mover um painel para outra aba recria o
`ApplicationScrollHandler`, mas o estado do tmux continua válido.

`HighlightedTerminalProxy._prepare_pty_data` chama
`observe_terminal_output(term, data)` em toda leitura do PTY, antes do buffer
de escapes parciais e antes de o VTE ver os bytes. Se houve mudança relevante
(modo de entrada, RIS, DECSTR), a inércia de aplicativo pendente é cancelada —
nenhum relatório antigo é reenviado após `mouse off`.

## Semântica espelhada (VTE 0.84, verificada com DECRQM)

| Entrada | VTE / guard |
|---|---|
| `?1000h`, `?1002h`, `?1003h`, `?9h`, `?1001h` | rastreamento ligado (flags independentes) |
| `?1006h` sozinho | só codificação SGR — **não** liga rastreamento |
| `?1002h` + `?1000l` | continua ligado (1002) |
| `?1049h/l` | não altera o mouse |
| `ESC c` (RIS), `CSI ! p` (DECSTR) | limpa modos ativos e salvos |
| `CSI ? Pm s` / `CSI ? Pm r` | XTSAVE / XTRESTORE; restaurar consome o valor; sem valor salvo → desligado |
| `ESC` ou U+009B dentro de OSC/DCS/APC | aborta a string; o CSI seguinte vale |
| texto sem `ESC` dentro de OSC/DCS | ignorado |
| U+009B (`C2 9B`) | CSI; `0x9B` cru (ex.: “ě”) é texto |
| C0 dentro de CSI | executado; o CSI continua |
| CAN/SUB, caractere não ASCII dentro de CSI | cancela |
| intermediário (`$`), subparâmetro (`:`), `>`/`=` | ignorado |
| mais de 32 parâmetros | ignorado |

O teste `test_guard_matches_installed_vte` reconfere essa tabela contra o VTE
instalado sempre que há display (pulado em CI sem display).

## Desempenho

- Por evento de roda: um `getattr` + teste de conjunto; sem alocação.
- Por leitura do PTY: blocos sem `ESC`/`C2` saem por `in` em C; CSIs completos
  são reconhecidos por uma regex e só `h l s r p` chegam ao Python; o
  analisador byte a byte trata apenas sequências cortadas entre leituras.
- Medido (blocos de 4 KiB, Python 3.14):

| Amostra | antes | depois |
|---|---|---|
| sessão tmux real (37 KB) | 14,1 MB/s | 20,4 MB/s |
| ASCII puro | 11 358 MB/s | 10 869 MB/s |
| SGR colorido | 9,4 MB/s | 18,1 MB/s |
| UTF-8 pt/cs | 12,3 MB/s | 162,2 MB/s |

Sem timers, threads ou referências a widgets novos; o guard contém apenas
bytes, um `set` e um `dict` e vive junto com o terminal.

## Limitações conhecidas

- **PTY não observado:** se o usuário desligar destaque de saída, colorização
  do `cat` **e** OSC 52, o VTE lê o PTY sozinho e o Ashy não vê os modos. A
  tela alternativa continua funcionando pelo fallback; rastreamento na tela
  normal com histórico (tmux `smcup@`, `fzf --height`) não.
- **Sensibilidade:** como já acontecia na tela alternativa, a sensibilidade do
  mouse multiplica os relatórios (padrão 30 → 3 relatórios por clique; o
  Konsole envia 1). O modo "native" envia 1.
- **Shift + roda** não força a rolagem do histórico do Ashy durante o
  rastreamento (o Konsole faz isso); não foi incluído para não ampliar o escopo.
