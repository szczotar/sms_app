"""Renders instrukcja_obslugi.md to a PDF using reportlab.

Rerun this whenever instrukcja_obslugi.md changes:
    python docs/generate_manual_pdf.py

Only understands the small Markdown subset used in instrukcja_obslugi.md:
headings (#/##/###), bullet lists (- ), numbered lists (1. ), bold (**),
inline code (`), and simple pipe tables. Not a general-purpose converter.
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS_DIR = Path(__file__).parent
SOURCE_MD = DOCS_DIR / "instrukcja_obslugi.md"
OUTPUT_PDF = DOCS_DIR / "Instrukcja_obslugi_PSYCHE_SMS.pdf"

# Base14 PDF fonts don't cover Polish diacritics; DejaVu Sans does and ships
# with Windows alongside the usual fonts.
_FONTS_DIR = Path(r"C:\Windows\Fonts")
_FONT_REGULAR = _FONTS_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONTS_DIR / "DejaVuSans-Bold.ttf"


def _register_fonts():
    if not _FONT_REGULAR.exists() or not _FONT_BOLD.exists():
        raise FileNotFoundError(
            f"Nie znaleziono DejaVuSans w {_FONTS_DIR} - potrzebny do polskich znakow w PDF."
        )
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(_FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(_FONT_BOLD)))


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "PLTitle", fontName="DejaVuSans-Bold", fontSize=20, leading=26,
        spaceAfter=18, textColor=colors.HexColor("#4B2A82"),
    ))
    styles.add(ParagraphStyle(
        "PLH2", fontName="DejaVuSans-Bold", fontSize=14, leading=18,
        spaceBefore=18, spaceAfter=8, textColor=colors.HexColor("#4B2A82"),
    ))
    styles.add(ParagraphStyle(
        "PLH3", fontName="DejaVuSans-Bold", fontSize=11.5, leading=15,
        spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#7A3F9E"),
    ))
    styles.add(ParagraphStyle(
        "PLBody", fontName="DejaVuSans", fontSize=10, leading=14.5, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "PLBullet", fontName="DejaVuSans", fontSize=10, leading=14.5,
    ))
    styles.add(ParagraphStyle(
        "PLTableCell", fontName="DejaVuSans", fontSize=9.5, leading=13,
    ))
    styles.add(ParagraphStyle(
        "PLTableHeader", fontName="DejaVuSans-Bold", fontSize=9.5, leading=13,
        textColor=colors.white,
    ))
    return styles


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_INLINE_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def _inline_markup(text: str) -> str:
    text = escape(text)
    text = _INLINE_BOLD_RE.sub(r"<b>\1</b>", text)
    text = _INLINE_CODE_RE.sub(r'<font face="DejaVuSans" color="#7A3F9E">\1</font>', text)
    return text


def _flush_paragraph(buffer: list[str], story: list, styles):
    if buffer:
        story.append(Paragraph(_inline_markup(" ".join(buffer)), styles["PLBody"]))
        buffer.clear()


def _flush_bullets(bullets: list[str], story: list, styles):
    if bullets:
        items = [
            ListItem(Paragraph(_inline_markup(b), styles["PLBullet"]), spaceAfter=4)
            for b in bullets
        ]
        story.append(ListFlowable(items, bulletType="bullet", start="-", leftIndent=14))
        story.append(Spacer(1, 8))
        bullets.clear()


def _flush_numbered(items_text: list[str], story: list, styles):
    if items_text:
        items = [
            ListItem(Paragraph(_inline_markup(t), styles["PLBullet"]), spaceAfter=4)
            for t in items_text
        ]
        story.append(ListFlowable(items, bulletType="1", leftIndent=14))
        story.append(Spacer(1, 8))
        items_text.clear()


def _flush_table(rows: list[list[str]], story: list, styles):
    if not rows:
        return
    header, *body = rows
    data = [[Paragraph(_inline_markup(c), styles["PLTableHeader"]) for c in header]]
    for row in body:
        data.append([Paragraph(_inline_markup(c), styles["PLTableCell"]) for c in row])
    table = Table(data, colWidths=[4.2 * cm, None], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4B2A82")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9BEDD")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F1FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    rows.clear()


def _parse_table_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


def build_story(markdown_text: str, styles) -> list:
    story: list = []
    paragraph_buf: list[str] = []
    bullet_buf: list[str] = []
    numbered_buf: list[str] = []
    table_rows: list[list[str]] = []

    def flush_all():
        _flush_paragraph(paragraph_buf, story, styles)
        _flush_bullets(bullet_buf, story, styles)
        _flush_numbered(numbered_buf, story, styles)
        _flush_table(table_rows, story, styles)

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if not line.strip():
            flush_all()
            continue

        if line.startswith("# "):
            flush_all()
            story.append(Paragraph(_inline_markup(line[2:]), styles["PLTitle"]))
            continue

        if line.startswith("## "):
            flush_all()
            story.append(Paragraph(_inline_markup(line[3:]), styles["PLH2"]))
            continue

        if line.startswith("### "):
            flush_all()
            story.append(Paragraph(_inline_markup(line[4:]), styles["PLH3"]))
            continue

        if line.lstrip().startswith("| "):
            _flush_paragraph(paragraph_buf, story, styles)
            if _TABLE_SEPARATOR_RE.match(line.strip()):
                continue
            table_rows.append(_parse_table_row(line))
            continue
        else:
            _flush_table(table_rows, story, styles)

        if line.lstrip().startswith("- "):
            _flush_paragraph(paragraph_buf, story, styles)
            bullet_buf.append(line.lstrip()[2:])
            continue
        else:
            _flush_bullets(bullet_buf, story, styles)

        numbered_match = re.match(r"^\d+\.\s+(.*)$", line.lstrip())
        if numbered_match:
            _flush_paragraph(paragraph_buf, story, styles)
            numbered_buf.append(numbered_match.group(1))
            continue
        else:
            _flush_numbered(numbered_buf, story, styles)

        paragraph_buf.append(line.strip())

    flush_all()
    return story


def main():
    _register_fonts()
    styles = _build_styles()
    markdown_text = SOURCE_MD.read_text(encoding="utf-8")
    story = build_story(markdown_text, styles)

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Instrukcja obslugi - Przypomnienia SMS PSYCHE",
    )
    doc.build(story)
    print(f"Zapisano: {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
