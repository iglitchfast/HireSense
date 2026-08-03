from fpdf import FPDF, XPos, YPos

ACCENT_RGB = (39, 156, 105)
ACCENT_DARK_RGB = (24, 97, 66)
TEXT_RGB = (26, 30, 28)
MUTED_RGB = (105, 112, 108)
RULE_RGB = (223, 228, 224)
BAR_WIDTH = 6
LEFT_MARGIN = 25
RIGHT_MARGIN = 18
PAGE_W = 210
PAGE_H = 297

# fpdf2's built-in core fonts only support Latin-1 — map common "smart" Unicode
# punctuation to ASCII equivalents, then hard-strip anything else that doesn't fit.
_UNICODE_REPLACEMENTS = {
    "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u2022": "-", "\u00a0": " ",
}


def _sanitize(text: str) -> str:
    for bad, good in _UNICODE_REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text.encode("latin-1", "replace").decode("latin-1")


class ResumePDF(FPDF):
    def header(self):
        # Thin accent bar down the full left edge of every page
        self.set_fill_color(*ACCENT_RGB)
        self.rect(0, 0, BAR_WIDTH, PAGE_H, style="F")

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-14)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*MUTED_RGB)
            self.cell(0, 8, f"Page {self.page_no()}", align="R")


def _write_mixed(pdf, line_height, text, base_color, size=10.5, bold_color=None):
    """Writes a line of text, rendering **bold** spans in actual bold weight
    via fpdf2's write(), which auto-wraps and respects the current left
    margin for hanging indents (used for bullet continuation lines)."""
    bold_color = bold_color or base_color
    segments = text.split("**")
    for i, seg in enumerate(segments):
        if not seg:
            continue
        is_bold = i % 2 == 1
        pdf.set_font("Helvetica", "B" if is_bold else "", size)
        pdf.set_text_color(*(bold_color if is_bold else base_color))
        pdf.write(line_height, seg)
    pdf.ln(line_height)


def _draw_bullet_dot(pdf, y_offset=2.3):
    x, y = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*ACCENT_RGB)
    pdf.ellipse(x, y + y_offset, 1.6, 1.6, style="F")
    pdf.set_x(x + 5)


def _split_trailing_dates(text):
    """Splits 'Company Name (2021-Present)' into ('Company Name', '2021-Present')
    for a professional left-title / right-date resume line layout."""
    if text.endswith(")") and "(" in text:
        idx = text.rfind("(")
        title = text[:idx].strip()
        dates = text[idx + 1 : -1].strip()
        if dates:
            return title, dates
    return text, None


def markdown_resume_to_pdf_bytes(resume_markdown: str) -> bytes:
    """
    Converts a resume written in Markdown into a polished, styled PDF:
    accent bar down the page, bold name header with subtitle + divider,
    section headers with marker + rule, job entries with right-aligned
    date ranges, circular bullet markers, and inline **bold** support.
    """
    pdf = ResumePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(LEFT_MARGIN, 20, RIGHT_MARGIN)

    title_set = False
    subtitle_done = False
    content_right_edge = PAGE_W - RIGHT_MARGIN

    lines = [_sanitize(l.rstrip()) for l in resume_markdown.splitlines()]

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped:
            pdf.ln(2.5)
            continue

        # ---- Name (# Title) ----
        if stripped.startswith("# ") and not title_set:
            text = stripped[2:].strip()
            pdf.set_font("Helvetica", "B", 25)
            pdf.set_text_color(*TEXT_RGB)
            pdf.cell(0, 12, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            title_set = True
            continue

        # First plain line right after the name = subtitle/role line
        if title_set and not subtitle_done and not stripped.startswith(("#", "-", "*")):
            pdf.set_font("Helvetica", "", 12)
            pdf.set_text_color(*ACCENT_DARK_RGB)
            pdf.cell(0, 7, stripped, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)
            pdf.set_draw_color(*RULE_RGB)
            pdf.set_line_width(0.4)
            pdf.line(LEFT_MARGIN, pdf.get_y(), content_right_edge, pdf.get_y())
            pdf.ln(5)
            subtitle_done = True
            continue

        # ---- Section header (## SECTION) ----
        if stripped.startswith("## "):
            text = stripped[3:].strip().upper()
            pdf.ln(3)
            pdf.set_fill_color(*ACCENT_RGB)
            pdf.rect(pdf.get_x(), pdf.get_y() + 1.2, 3, 3, style="F")
            pdf.set_x(pdf.get_x() + 6)
            pdf.set_font("Helvetica", "B", 11.5)
            pdf.set_text_color(*ACCENT_DARK_RGB)
            pdf.cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_draw_color(*RULE_RGB)
            pdf.set_line_width(0.3)
            pdf.line(LEFT_MARGIN, pdf.get_y() + 1, content_right_edge, pdf.get_y() + 1)
            pdf.ln(4)
            continue

        # ---- Sub-header (### Role, Company (dates)) ----
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            title, dates = _split_trailing_dates(text)
            pdf.set_font("Helvetica", "B", 10.8)
            pdf.set_text_color(*TEXT_RGB)
            if dates:
                pdf.cell(120, 6.5, title, new_x=XPos.RIGHT, new_y=YPos.TOP)
                pdf.set_font("Helvetica", "I", 9.5)
                pdf.set_text_color(*MUTED_RGB)
                pdf.cell(0, 6.5, dates, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                pdf.cell(0, 6.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(0.5)
            continue

        # ---- Bullet points ----
        if stripped.startswith(("- ", "* ")):
            text = stripped[2:].strip()
            base_left = pdf.l_margin
            pdf.set_left_margin(base_left + 5)
            pdf.set_x(base_left + 5)
            _draw_bullet_dot(pdf)
            _write_mixed(pdf, 5.6, text, TEXT_RGB, size=10, bold_color=TEXT_RGB)
            pdf.set_left_margin(base_left)
            pdf.set_x(base_left)
            continue

        # ---- Plain paragraph text ----
        text = stripped.replace("#", "").strip()
        color = TEXT_RGB if title_set else MUTED_RGB
        _write_mixed(pdf, 5.6, text, color, size=10, bold_color=color)

    return bytes(pdf.output())