# Testes: mouse do tmux e roteamento da roda

## Automatizados

```bash
pytest tests/test_scroll_mode_guard.py -v
pytest tests/test_scroll_handler.py -v
pytest tests/test_application_scroll.py -v
pytest tests/test_application_scroll_momentum.py -v
pytest tests/ -q
```

| Arquivo | O que cobre |
|---|---|
| `test_scroll_mode_guard.py` | Tabela de 37 sequências verificadas no VTE (tmux liga/desliga, `1006` só codificação, modos simultâneos, RIS/DECSTR, XTSAVE/XTRESTORE, OSC/DCS/APC com e sem `ESC`, C1 U+009B × `0x9B` cru, CAN/SUB, C0 em CSI, limite de parâmetros), cada uma cortada em **todas** as posições de leitura; paridade ao vivo com o VTE instalado; estado por terminal; `wheel_reaches_application` com e sem histórico |
| `test_scroll_handler.py` | Regressão: rastreamento + histórico propaga a roda (mouse e touchpad, Automatic/Custom, para cima/baixo) sem tocar o `Adjustment` e cancelando a inércia do histórico; desligar o rastreamento devolve a rolagem própria; Ctrl + roda continua dando zoom |
| `test_application_scroll.py` | Sensibilidade aplicada ao relatório mesmo com histórico; estado preservado ao revincular o controlador (mover painel/aba); cancelamento por mudança de modo |
| `test_application_scroll_momentum.py` | Inércia de touchpad continua sobre o histórico enquanto há rastreamento e para — sem reenvio — quando o tmux desliga o mouse; o proxy observa a saída antes do buffer de escapes |

Resultado em 2026-10-10: `2648 passed, 1 skipped, 1 warning`. O skip e o
aviso (`GLib.unix_signal_add_full` obsoleto no PyGObject) já existiam.

## Manual (BigLinux)

Use um servidor tmux isolado para não tocar a configuração nem sessões do
usuário:

```bash
python -m ashyterm --new-window          # a partir de src/, ou o pacote instalado
# dentro do Ashy:
seq 1 2000                               # histórico prévio no Ashy
tmux -L ashyterm-mouse-test -f /dev/null new-session
tmux set -g mouse on
seq 1 2000
```

1. Roda para cima → modo cópia (`[n/m]` no canto); para baixo volta.
2. `Ctrl+b %` → clicar em cada painel muda o foco; a roda rola o painel sob
   o ponteiro; arrastar seleciona e copia; arrastar a borda redimensiona.
3. `tmux set -g mouse off` → a roda não entra mais no modo cópia.
4. Repita com histórico na tela normal (sem tela alternativa), após
   `tmux -L ashyterm-mouse-test kill-server`:

   ```bash
   printf 'set -ga terminal-overrides ",*:smcup@:rmcup@"\n' > /tmp/tmux-nosmcup.conf
   tmux -L ashyterm-mouse-test -f /tmp/tmux-nosmcup.conf new-session
   ```

   (ou `fzf --height 40%` fora do tmux). Com `mouse off`, a roda deve voltar a
   rolar o histórico do próprio Ashy.
5. Ao final: `tmux -L ashyterm-mouse-test kill-server`.

## Execução registrada

Roteiro automatizado com Ashy real (XWayland, `GDK_BACKEND=x11`), tmux 3.7 em
socket próprio, eventos via XTEST (`xdotool`) e verificação pelo estado do
tmux (`pane_in_mode`, `scroll_position`, painel ativo, buffers, largura):

| Verificação | pacote 26.10.01 | `main` @ 56337741 | correção | Konsole |
|---|---|---|---|---|
| tela alternativa: roda → modo cópia | ✗ | ✓ | ✓ | ✓ |
| histórico na tela normal: roda → modo cópia | ✗ | ✗ | ✓ | ✓ |
| roda no painel sob o ponteiro | ✗ | ✗ (normal) | ✓ | ✓ |
| clique seleciona painel | ✓ | ✓ | ✓ | ✓ |
| arrastar seleciona/copia | ✓ | ✓ | ✓ | ✓ |
| arrastar borda redimensiona | ✓ (alt.)² | ✓ (alt.)² | ✓ | não medido¹ |
| `mouse off` devolve a roda ao Ashy | ✓ | ✓ | ✓ | ✓ |

¹ A janela do Konsole tem decoração do servidor e escala própria; o roteiro
não acertou a coluna da borda. Não indica falha do Konsole.
² Na tela normal a roda rolou o histórico do Ashy em vez do tmux, tirando a
borda da tela capturada; não foi medido.

Também verificado: com destaque, `cat` e OSC 52 desligados (sem proxy), a tela
alternativa continua funcionando (7/7) e o cenário com histórico na tela
normal não é detectado (limitação documentada).

## Não validado neste ambiente

- **SSH real:** não há acesso por chave a um servidor de teste. As sessões SSH
  usam o mesmo `HighlightedTerminalProxy`, coberto pelos testes acima.
- **Wayland nativo:** a injeção de eventos exigiu XWayland. O código de
  roteamento não depende do backend GDK, mas convém um teste manual no
  Wayland nativo.
- **Touchpad físico:** a inércia foi validada por testes unitários; não houve
  gesto real.
