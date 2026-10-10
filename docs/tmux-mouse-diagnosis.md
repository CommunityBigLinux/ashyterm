# Diagnóstico: roda do mouse não chega ao tmux (`set -g mouse on`)

> **Data:** 2026-10-10 · **Ambiente:** BigLinux (KDE Plasma Wayland), VTE 0.84.1, tmux 3.7, ashyterm 26.10.01 (pacote) e `main` @ 56337741

## Relato

Com `tmux set -g mouse on`, a roda do mouse não rola o histórico do painel no
Ashy Terminal; no Konsole funciona. O comando do tmux está correto.

## Caminho do evento

```text
mouse/touchpad → GDK → EventControllerScroll do Ashy (CAPTURE, no host)
              → ScrollHandler._on_terminal_scroll ──(EVENT_STOP)──✗
              → controlador "vte-scroll-controller" (envolvido por ApplicationScrollHandler)
              → VTE codifica o relatório (ex.: ESC[<64;x;yM) → PTY → tmux
```

O Ashy instala um `Gtk.EventControllerScroll` em fase **CAPTURE** acima do VTE
para aplicar sensibilidade e inércia próprias ao histórico. Quando ele retorna
`Gdk.EVENT_STOP`, o VTE nunca vê o evento e, portanto, não gera o relatório de
mouse que o tmux espera.

## Causa raiz

A decisão "rolar o histórico do Ashy ou entregar ao aplicativo" não consultava
o estado de *mouse tracking* do terminal — só a geometria do `Gtk.Adjustment`.

1. **Versão empacotada (26.10.01):** sem nenhuma checagem. No tmux (tela
   alternativa, histórico vazio) a rolagem caía em `_is_expected_boundary()`,
   que retornava `True` → `EVENT_STOP`. A roda era consumida sempre.
2. **`main` (a0899d19):** passou a propagar quando
   `upper - lower <= page_size` (sem histórico). Isso cobre o tmux padrão
   (`smcup` → `?1049h`), mas é uma heurística: qualquer aplicativo que ative
   rastreamento de mouse **fora** da tela alternativa, com histórico presente,
   continuava perdendo a roda — tmux com `terminal-overrides ...smcup@:rmcup@`
   (configuração comum para manter o scrollback nativo), `fzf --height`,
   `less -X --mouse`, etc.

O Konsole (e o VTE puro, ver evidência 2) decide pelo modo de mouse ativo:
se o aplicativo pediu rastreamento, a roda é do aplicativo, haja histórico ou não.

## Evidências

1. **Reprodução real** (Ashy + tmux isolado, roda via XTEST, estado lido do
   próprio tmux — procedimento em `tmux-mouse-testing.md`):
   - pacote 26.10.01: `pane_in_mode=0` após rolar para cima (tela alternativa
     e normal) → bug reproduzido;
   - `main` @ 56337741: tela alternativa OK (7/7), mas no cenário com
     histórico (`smcup@`) a roda não chega ao tmux (3/6) — reproduzido também
     pelo teste de regressão `test_mouse_tracking_with_scrollback_reaches_application`,
     que falha 8/8 no código original;
   - com a correção: 7/7 nos dois cenários.
2. **VTE puro, 500 linhas de histórico:** com qualquer um dos modos 9, 1000,
   1001, 1002 ou 1003 o VTE emite `ESC[<64;…M` por clique da roda e não move o
   histórico; sem modo, rola o histórico. O VTE já faz a coisa certa — o
   bloqueio estava no controlador do Ashy.
3. **Ajuste na tela alternativa (VTE 0.84):** `?1049h` zera o histórico
   visível (`upper == page_size`), mesmo após 2000 linhas; `?1000h` na tela
   normal mantém `upper=2001`. Logo, a heurística só acerta na tela alternativa.

## Achados secundários (corrigidos junto)

O `ScrollModeGuard` já existia apenas para cancelar a inércia; comparado ao
VTE real via DECRQM ele divergia em casos que agora importam:

- `ESC` dentro de OSC/DCS **aborta** a string no VTE e o CSI seguinte é
  aplicado (ex.: passthrough `ESC Ptmux; ESC ESC[?1000h ESC \`); o guard ignorava.
- Byte `0x9B` cru (ex.: “ě” = `C4 9B`) era tratado como CSI; o VTE só aceita
  U+009B (`C2 9B`).
- XTRESTORE, CAN/SUB, C0 dentro de CSI e o limite de 32 parâmetros tinham
  semântica diferente.
- O estado ficava no `ApplicationScrollHandler`, recriado ao mover um painel
  para nova aba (`pane_manager.py` desvincula e revincula o controlador): o
  modo de mouse seria perdido com o tmux ainda ativo.
- Só era alimentado se o handler existisse; saída anterior se perdia.

## Justificativa da solução

Espelhar, a partir da saída do PTY, os modos de mouse que o VTE aplica e usar
esse estado (com a heurística de histórico como fallback) para rotear a roda.
É a camada de protocolo, não uma exceção para o processo `tmux`; vale para
qualquer TUI e para sessões SSH (mesmo leitor de PTY). Detalhes em
`tmux-mouse-implementation.md`.
