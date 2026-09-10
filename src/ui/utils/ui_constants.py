"""
Módulo central de Design Tokens e Constantes de Interface (UI) para o Medusa VTT.

Este módulo define a fonte da verdade canônica para espaçamentos (8-Point Grid),
dimensões de controles, padronização tipográfica e paleta de cores (Dark Fantasy).
NÃO CONTÉM PRINTS NEM LÓGICA EXECUTÁVEL (Data/Constants puras).
"""

from typing import Tuple

# Tipo alias para tuplas de cor RGBA
RGBAColor = Tuple[int, int, int, int]


class Spacing:
    """
    Grid de Espaçamento e Escala de 8pt (8-Point Grid) com subdivisão de 4pt.
    Todos os paddings, margins e gaps devem ser múltiplos estritos desta escala.
    """
    TINY: int = 4        # Micro-espaçamento (ícones pequenos, badges, offsets finos)
    SM: int = 8          # Margem interna de botões compactos, gap entre botões adjacentes
    MD: int = 16         # Padding interno padrão de contêineres/painéis, isolamento de seções
    LG: int = 24         # Margens externas entre blocos de conteúdo e grids
    XL: int = 32         # Separadores de seções principais e cabeçalhos globais

    # Aliases semânticos para clareza em layouts
    GAP_TINY: int = 4
    GAP_SMALL: int = 8
    GAP_MEDIUM: int = 16
    GAP_LARGE: int = 24
    GAP_XLARGE: int = 32
    CONTAINER_PADDING: int = 16


class Dimensions:
    """
    Dimensões métricas, alturas mínimas, raios de borda e espessuras canônicas.
    """
    # Alturas e dimensões de botões
    BTN_HEIGHT_DEFAULT: float = 36.0     # Altura canônica para botões padrão de ação (36-40px)
    BTN_HEIGHT_LARGE: float = 40.0       # Botões de destaque / CTA principal
    BTN_HEIGHT_COMPACT: float = 28.0     # Botões compactos de cabeçalho ou barra de ferramentas
    BTN_SIZE_COMPACT_SM: float = 28.0    # Botões quadrados pequenos (28x28px - ex: +, -, turno)
    BTN_SIZE_COMPACT_MD: float = 32.0    # Botões quadrados médios (32x32px)
    BTN_PADDING_X_MIN: float = 12.0      # Padding horizontal mínimo para evitar texto encostado
    BTN_PADDING_Y_MIN: float = 6.0       # Padding vertical mínimo

    # Gaps entre botões e grupos de controle
    BTN_GAP_INLINE: float = 8.0          # Espaçamento entre botões da mesma família de ação
    BTN_GAP_DESTRUCTIVE: float = 16.0   # Isolamento obrigatório para botões de ação destrutiva

    # Inputs e Controles de Formulário
    INPUT_HEIGHT_DEFAULT: float = 36.0
    INPUT_HEIGHT_COMPACT: float = 28.0
    INPUT_PADDING_X: float = 10.0

    # Estruturas Globais e Painéis
    HEADER_HEIGHT: float = 56.0          # Altura da barra superior do Mestre (DMHeader)
    TAB_BAR_HEIGHT: float = 40.0         # Altura das abas de navegação
    MODAL_MIN_WIDTH: float = 360.0       # Largura mínima de modais e caixas de diálogo
    MODAL_PADDING: float = 16.0          # Padding interno obrigatório em modais

    # Cantos Arredondados (Corner Radii)
    CORNER_RADIUS_SM: float = 4.0        # Badges e micro-tags
    CORNER_RADIUS_DEFAULT: float = 6.0   # Botões e inputs
    CORNER_RADIUS_CARD: float = 8.0      # Cards, contêineres e painéis flutuantes
    CORNER_RADIUS_MODAL: float = 10.0    # Caixas modais e popups

    # Espessura de Bordas (Stroke / Outline Width)
    BORDER_WIDTH_DEFAULT: float = 1.0    # Borda sutil padrão
    BORDER_WIDTH_ACTIVE: float = 1.5     # Borda de estado ativo / selecionado
    BORDER_WIDTH_THICK: float = 2.0      # Borda de foco, destaque ou colisão tática


class Typography:
    """
    Escala tipográfica proporcional e fontes canônicas para Arcade UI.
    """
    # Tamanhos de fonte (Font Sizes em pt/px)
    SIZE_TAB_TITLE: int = 18             # Títulos principais de abas (18-20px)
    SIZE_TAB_TITLE_LG: int = 20          # Título destacado de modal/painel
    SIZE_HEADER: int = 16                # Cabeçalhos de seção (14-16px)
    SIZE_SUBHEADER: int = 14             # Subtítulos e títulos de cards
    SIZE_BODY: int = 12                  # Corpo de texto e labels principais (11-12px)
    SIZE_LABEL: int = 11                 # Labels compactos e valores de atributos
    SIZE_BADGE: int = 10                 # Badges e tags de status (9-10px)
    SIZE_MICRO: int = 9                  # Micro-textos informativos e atalhos

    # Pilha tipográfica com fallbacks do sistema operacional
    FONT_FAMILY_PRIMARY: Tuple[str, ...] = ("Segoe UI", "Calibri", "Arial", "sans-serif")
    FONT_FAMILY_MONO: Tuple[str, ...] = ("Consolas", "Courier New", "monospace")
    FONT_FAMILY_UI: Tuple[str, ...] = ("Consolas", "Calibri", "Segoe UI", "Arial")


class Colors:
    """
    Paleta canônica Dark Fantasy e definições RGBA para a interface do Medusa VTT.
    """
    # Identidade Dark Fantasy Fundamental
    BG_DARK: RGBAColor = (14, 18, 24, 255)         # #0E1218 - Fundo principal da aplicação
    BG_PANEL: RGBAColor = (20, 26, 36, 255)        # #141A24 - Fundo de painéis e barras de controle
    BG_PANEL_ALT: RGBAColor = (26, 34, 46, 255)    # Fundo alternado para listas e cabeçalhos
    BG_CARD: RGBAColor = (30, 40, 55, 255)         # #1E2837 - Cards de itens, combatentes e monstros
    BG_CARD_HOVER: RGBAColor = (38, 50, 70, 255)   # Destaque de hover em cards
    BG_MODAL: RGBAColor = (18, 24, 32, 245)        # Fundo semi-opaco para janelas modais
    BG_OVERLAY: RGBAColor = (0, 0, 0, 180)         # Overlay escurecido de fundo para modais

    # Acentos e Identidade Tática (D&D 5E)
    ACCENT_GOLD: RGBAColor = (241, 196, 15, 255)   # #F1C40F - Dourado místico (destaques, títulos, foco)
    PC_BLUE: RGBAColor = (41, 128, 185, 255)       # #2980B9 - Jogadores (PCs)
    NPC_RED: RGBAColor = (192, 57, 43, 255)        # #C0392B - Monstros / NPCs (Carmim)

    # Bordas e Divisores
    BORDER_DEFAULT: RGBAColor = (50, 65, 90, 200)  # Borda padrão de painéis e contêineres
    BORDER_SUBTLE: RGBAColor = (40, 50, 65, 120)   # Borda sutil interna / divisores
    BORDER_MUTED: RGBAColor = (30, 40, 55, 150)    # Divisor suave de linhas
    BORDER_FOCUS: RGBAColor = (241, 196, 15, 255)  # Borda em estado de foco (Ouro Místico)

    # Tipografia e Cores de Texto
    TEXT_PRIMARY: RGBAColor = (240, 244, 248, 255) # Texto principal de alto contraste
    TEXT_SECONDARY: RGBAColor = (189, 195, 199, 255)# Texto secundário e descrições
    TEXT_MUTED: RGBAColor = (120, 140, 160, 255)   # Textos desabilitados, hints e placeholders
    TEXT_HIGHLIGHT: RGBAColor = (241, 196, 15, 255)# Texto com ênfase dourada
    TEXT_WHITE: RGBAColor = (255, 255, 255, 255)   # Branco puro para títulos de botões
    TEXT_DARK: RGBAColor = (20, 26, 36, 255)       # Texto escuro para botões com fundo claro

    # Feedback Semântico
    SUCCESS: RGBAColor = (46, 204, 113, 255)       # #2ECC71 - Vida cheia, confirmação, sucesso
    SUCCESS_BG: RGBAColor = (27, 94, 52, 255)      # Fundo para botões e badges de sucesso
    SUCCESS_BORDER: RGBAColor = (46, 204, 113, 255)

    WARNING: RGBAColor = (243, 156, 18, 255)       # #F39C12 - Vida média, alertas, neutro
    WARNING_BG: RGBAColor = (120, 80, 15, 255)     # Fundo para alertas e avisos
    WARNING_BORDER: RGBAColor = (241, 196, 15, 255)

    DANGER: RGBAColor = (231, 76, 60, 255)         # #E74C3C - Vida crítica, dano, ação destrutiva
    DANGER_BG: RGBAColor = (120, 30, 25, 255)      # Fundo para botões de deletar/cancelar
    DANGER_BORDER: RGBAColor = (192, 57, 43, 255)

    INFO: RGBAColor = (52, 152, 219, 255)          # #3498DB - Seleção ativa, turnos, informações
    INFO_BG: RGBAColor = (31, 78, 121, 255)        # Fundo para itens selecionados
    INFO_BORDER: RGBAColor = (93, 173, 226, 255)

    # Parâmetros de Modificação de Estado
    DISABLED_ALPHA_FACTOR: float = 0.40            # Redução de opacidade para estado desabilitado (40%)
    HOVER_BRIGHTNESS_DELTA: float = 0.15           # Clareamento percentual no hover (+15%)
    ACTIVE_BRIGHTNESS_DELTA: float = -0.10         # Escurecimento percentual no active (-10%)


# =============================================================================
# Funções Utilitárias Puras de Manipulação de Cores (Zero Prints / Zero Side-Effects)
# =============================================================================

def with_alpha(color: RGBAColor, alpha: int) -> RGBAColor:
    """Retorna uma nova tupla RGBA com o canal alfa ajustado (0 a 255)."""
    clamped_alpha = max(0, min(255, int(alpha)))
    return (color[0], color[1], color[2], clamped_alpha)


def lighten(color: RGBAColor, factor: float = Colors.HOVER_BRIGHTNESS_DELTA) -> RGBAColor:
    """
    Clareia uma cor RGBA somando uma fração do brilho restante (padrão +15%).
    Preserva o canal alfa original.
    """
    r = min(255, int(color[0] + (255 - color[0]) * factor))
    g = min(255, int(color[1] + (255 - color[1]) * factor))
    b = min(255, int(color[2] + (255 - color[2]) * factor))
    return (r, g, b, color[3])


def darken(color: RGBAColor, factor: float = abs(Colors.ACTIVE_BRIGHTNESS_DELTA)) -> RGBAColor:
    """
    Escurece uma cor RGBA reduzindo o valor dos canais RGB (padrão -10%).
    Preserva o canal alfa original.
    """
    r = max(0, int(color[0] * (1.0 - factor)))
    g = max(0, int(color[1] * (1.0 - factor)))
    b = max(0, int(color[2] * (1.0 - factor)))
    return (r, g, b, color[3])


def apply_disabled(color: RGBAColor, alpha_factor: float = Colors.DISABLED_ALPHA_FACTOR) -> RGBAColor:
    """
    Aplica a atenuação de opacidade de 40% para elementos em estado desabilitado.
    """
    new_alpha = max(0, min(255, int(color[3] * alpha_factor)))
    return (color[0], color[1], color[2], new_alpha)
