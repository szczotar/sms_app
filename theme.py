"""Brand palette and shared look-and-feel, derived from assets/psyche_logo.png."""

import customtkinter as ctk

PURPLE = "#5C2675"
PURPLE_DARK = "#3E1A50"
PURPLE_LIGHT = "#7C4193"

MAGENTA = "#E61B74"
MAGENTA_DARK = "#B81460"
MAGENTA_LIGHT = "#F04F92"

BG = "#F6F3F8"
CARD = "#FFFFFF"
CARD_HOVER = "#FBF3F8"
BORDER = "#E7DCEC"

TEXT = "#2B1730"
MUTED = "#8A7A93"
WHITE = "#FFFFFF"

WARNING_BG = "#FFCC00"
WARNING_FG = "#2B1730"

FONT_FAMILY = "Segoe UI"


def setup():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


def font(size=13, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)
