"""
Générateur de documents PDF — FacturePro
=========================================
Deux types de documents :
  - Ticket de caisse  : format étroit (80mm), style caissier
  - Facture           : format A4, présentation professionnelle
"""

import os
from datetime import datetime
from app_path import app_path
import config as cfg

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable, Image)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def _fmt(value) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", " ")
    except Exception:
        return "0"


def _fmt2(value) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return "0,00"


def get_output_path(numero: str, type_doc: str = "facture") -> str:
    """Retourne le chemin de sortie du PDF."""
    dossier = cfg.get("dossier_factures", "factures")
    if not os.path.isabs(dossier):
        dossier = app_path(dossier)
    os.makedirs(dossier, exist_ok=True)
    safe = numero.replace("/", "-").replace("\\", "-")
    prefix = "TICKET" if type_doc == "ticket" else "FAC"
    return os.path.join(dossier, f"{prefix}_{safe}.pdf")


def _load_logo():
    """Charge le logo depuis la config."""
    logo_path = cfg.get("logo_path", "")
    if logo_path and os.path.isfile(logo_path):
        return logo_path
    # Chemin relatif à l'app
    alt = app_path(logo_path) if logo_path else ""
    if alt and os.path.isfile(alt):
        return alt
    return None


# ══════════════════════════════════════════════════════════════════════════════
# TICKET DE CAISSE (format 80mm)
# ══════════════════════════════════════════════════════════════════════════════

TICKET_WIDTH  = 80 * mm
TICKET_MARGIN = 4 * mm


def generate_ticket(numero, client, telephone, date_str, lignes,
                    total, methode_paiement="Espèces") -> str:
    """
    Génère un ticket de caisse au format 80mm.
    Retourne le chemin du fichier PDF généré.
    """
    if not REPORTLAB_OK:
        raise ImportError("reportlab est requis : pip install reportlab")

    path = get_output_path(numero, "ticket")

    # Hauteur dynamique selon le nombre de lignes
    nb_lignes = len(lignes)
    hauteur = max(120 * mm, (60 + nb_lignes * 8 + 40) * mm)

    c = rl_canvas.Canvas(path, pagesize=(TICKET_WIDTH, hauteur))
    y = hauteur - TICKET_MARGIN

    conf = cfg.load()
    nom_commerce  = conf.get("nom", "MON COMMERCE")
    adresse       = conf.get("adresse", "")
    telephone_com = conf.get("telephone", "")
    slogan        = conf.get("slogan", "")
    msg_merci     = conf.get("message_remerciement", "Merci !")
    mention_pmt   = conf.get("mention_paiement", "")

    couleur_hex = conf.get("couleur_primaire", "#1a56db")
    try:
        coul = colors.HexColor(couleur_hex)
    except Exception:
        coul = colors.HexColor("#1a56db")

    W = TICKET_WIDTH
    x_left  = TICKET_MARGIN
    x_right = W - TICKET_MARGIN
    x_mid   = W / 2

    def line(y_pos):
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(x_left, y_pos, x_right, y_pos)

    def dashed_line(y_pos):
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.setDash(2, 2)
        c.line(x_left, y_pos, x_right, y_pos)
        c.setDash()

    def text_center(txt, y_pos, size=8, bold=False, color=colors.black):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(color)
        c.drawCentredString(x_mid, y_pos, txt)

    def text_left(txt, y_pos, size=7.5, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(colors.black)
        c.drawString(x_left + 2, y_pos, txt)

    def text_right(txt, y_pos, size=7.5, bold=False):
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.setFillColor(colors.black)
        c.drawRightString(x_right - 2, y_pos, txt)

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_path = _load_logo()
    if logo_path:
        try:
            lw = min(40 * mm, W - 2 * TICKET_MARGIN)
            lh = 15 * mm
            c.drawImage(logo_path, x_mid - lw / 2, y - lh,
                        width=lw, height=lh,
                        preserveAspectRatio=True, mask="auto")
            y -= lh + 3 * mm
        except Exception:
            pass

    # ── En-tête ───────────────────────────────────────────────────────────────
    text_center(nom_commerce, y, size=11, bold=True, color=coul)
    y -= 5 * mm
    if slogan:
        text_center(slogan, y, size=7)
        y -= 4 * mm
    if adresse:
        text_center(adresse, y, size=7)
        y -= 4 * mm
    if telephone_com:
        text_center(f"Tél : {telephone_com}", y, size=7)
        y -= 4 * mm

    y -= 2 * mm
    line(y)
    y -= 3 * mm

    # ── Info ticket ───────────────────────────────────────────────────────────
    text_center("TICKET DE CAISSE", y, size=9, bold=True)
    y -= 4 * mm
    text_left(f"N° : {numero}", y, size=7)
    text_right(f"Date : {date_str}", y, size=7)
    y -= 4 * mm
    if client and client.strip() and client.strip().lower() not in ("client", "-", ""):
        text_left(f"Client : {client}", y, size=7)
        y -= 4 * mm
        if telephone:
            text_left(f"Tél : {telephone}", y, size=7)
            y -= 4 * mm

    dashed_line(y)
    y -= 3 * mm

    # ── En-têtes colonnes ─────────────────────────────────────────────────────
    col_desig_w = (W - 2 * TICKET_MARGIN) * 0.50
    col_qte_w   = (W - 2 * TICKET_MARGIN) * 0.15
    col_pu_w    = (W - 2 * TICKET_MARGIN) * 0.17
    col_mt_w    = (W - 2 * TICKET_MARGIN) * 0.18

    x_desig = x_left + 2
    x_qte   = x_desig + col_desig_w
    x_pu    = x_qte   + col_qte_w
    x_mt    = x_pu    + col_pu_w

    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(colors.grey)
    c.drawString(x_desig, y, "Désignation")
    c.drawString(x_qte,   y, "Qté")
    c.drawString(x_pu,    y, "P.U.")
    c.drawRightString(x_right - 2, y, "Montant")
    y -= 2 * mm
    line(y)
    y -= 3 * mm

    # ── Lignes articles ───────────────────────────────────────────────────────
    c.setFillColor(colors.black)
    for ligne in lignes:
        if isinstance(ligne, dict):
            desig = ligne.get("designation", "")
            qte   = ligne.get("quantite", 0)
            pu    = ligne.get("prix_unitaire", 0)
            mt    = ligne.get("montant", 0)
        else:
            desig, qte, pu, mt = ligne[0], ligne[1], ligne[2], ligne[3]

        # Tronquer la désignation si trop longue
        max_chars = 22
        if len(desig) > max_chars:
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.black)
            c.drawString(x_desig, y, desig[:max_chars] + "…")
            y -= 3.5 * mm
            c.drawString(x_desig + 2, y, "")
        else:
            c.setFont("Helvetica", 7)
            c.drawString(x_desig, y, desig)

        c.drawString(x_qte, y, f"{float(qte):g}")
        c.drawString(x_pu,  y, _fmt(pu))
        c.drawRightString(x_right - 2, y, _fmt(mt))
        y -= 4 * mm

    dashed_line(y)
    y -= 3 * mm

    # ── Total ─────────────────────────────────────────────────────────────────
    nb_articles = sum(
        (l.get("quantite", 0) if isinstance(l, dict) else l[1]) for l in lignes
    )
    text_left(f"{int(nb_articles)} article(s)", y, size=7)
    y -= 1 * mm

    # Bande total
    c.setFillColor(coul)
    c.rect(x_left, y - 7 * mm, W - 2 * TICKET_MARGIN, 8 * mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(x_left + 3, y - 5 * mm, "TOTAL")
    c.drawRightString(x_right - 3, y - 5 * mm, f"{_fmt(total)} FCFA")
    y -= 9 * mm

    # Méthode de paiement
    if methode_paiement:
        text_left(f"Paiement : {methode_paiement}", y, size=7.5, bold=True)
        y -= 4 * mm

    if mention_pmt:
        text_center(mention_pmt, y, size=7)
        y -= 4 * mm

    line(y)
    y -= 4 * mm

    # ── Message final ─────────────────────────────────────────────────────────
    text_center(msg_merci, y, size=9, bold=True, color=coul)
    y -= 4 * mm
    text_center(f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", y, size=6.5)

    c.save()
    return path


# ══════════════════════════════════════════════════════════════════════════════
# FACTURE A4
# ══════════════════════════════════════════════════════════════════════════════

def generate_facture(numero, client, telephone, date_str, lignes,
                     total, methode_paiement="") -> str:
    """
    Génère une facture au format A4 professionnel.
    Retourne le chemin du fichier PDF généré.
    """
    if not REPORTLAB_OK:
        raise ImportError("reportlab est requis : pip install reportlab")

    path = get_output_path(numero, "facture")
    conf = cfg.load()

    # Couleurs
    try:
        coul_primaire = colors.HexColor(conf.get("couleur_primaire", "#1a56db"))
    except Exception:
        coul_primaire = colors.HexColor("#1a56db")
    try:
        coul_accent = colors.HexColor(conf.get("couleur_accent", "#0d3d91"))
    except Exception:
        coul_accent = colors.HexColor("#0d3d91")

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    story  = []

    W = A4[0] - 36 * mm  # largeur utile

    # ── En-tête : logo + infos commerce ──────────────────────────────────────
    nom_commerce  = conf.get("nom", "MON COMMERCE")
    adresse       = conf.get("adresse", "")
    telephone_com = conf.get("telephone", "")
    slogan        = conf.get("slogan", "")
    rc            = conf.get("RC", "")
    ninea         = conf.get("NINEA", "")
    titre_doc     = conf.get("titre_facture", "FACTURE")
    msg_merci     = conf.get("message_remerciement", "Merci !")
    mention_pmt   = conf.get("mention_paiement", "")

    def style_p(size=9, bold=False, align=TA_LEFT, color=colors.black, leading=None):
        return ParagraphStyle(
            "custom",
            fontSize=size,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            alignment=align,
            textColor=color,
            leading=leading or (size * 1.3),
        )

    # Tableau en-tête (logo | infos)
    logo_path = _load_logo()
    if logo_path:
        try:
            lw_mm = conf.get("logo_largeur_mm", 45)
            lh_mm = conf.get("logo_hauteur_mm", 18)
            logo_img = Image(logo_path, width=lw_mm * mm, height=lh_mm * mm)
            logo_cell = logo_img
        except Exception:
            logo_cell = Paragraph(nom_commerce,
                                  style_p(16, bold=True, color=coul_primaire))
    else:
        logo_cell = Paragraph(nom_commerce,
                              style_p(16, bold=True, color=coul_primaire))

    info_lines = [
        Paragraph(nom_commerce, style_p(13, bold=True, color=coul_primaire, align=TA_RIGHT)),
    ]
    if slogan:
        info_lines.append(Paragraph(slogan, style_p(8, align=TA_RIGHT, color=colors.grey)))
    if adresse:
        info_lines.append(Paragraph(adresse, style_p(8, align=TA_RIGHT)))
    if telephone_com:
        info_lines.append(Paragraph(f"Tél : {telephone_com}", style_p(8, align=TA_RIGHT)))
    if rc:
        info_lines.append(Paragraph(f"RC : {rc}", style_p(8, align=TA_RIGHT)))
    if ninea:
        info_lines.append(Paragraph(f"NINEA : {ninea}", style_p(8, align=TA_RIGHT)))

    from reportlab.platypus import KeepTogether
    header_tbl = Table(
        [[logo_cell, info_lines]],
        colWidths=[W * 0.4, W * 0.6]
    )
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",  (1, 0), (1, 0),  "RIGHT"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Bande titre ───────────────────────────────────────────────────────────
    titre_tbl = Table(
        [[Paragraph(titre_doc, style_p(18, bold=True, color=colors.black, align=TA_CENTER))]],
        colWidths=[W]
    )
    titre_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), coul_primaire),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(titre_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Infos facture + client ────────────────────────────────────────────────
    cell_fac = [
        Paragraph("Détails du document", style_p(8, color=colors.grey)),
        Paragraph(f"<b>N° :</b> {numero}", style_p(9)),
        Paragraph(f"<b>Date :</b> {date_str}", style_p(9)),
    ]
    if methode_paiement:
        cell_fac.append(Paragraph(f"<b>Paiement :</b> {methode_paiement}", style_p(9)))

    client_lines = [
        Paragraph("Destinataire", style_p(8, color=colors.grey)),
        Paragraph(f"<b>{client}</b>", style_p(10, bold=True)),
    ]
    if telephone:
        client_lines.append(Paragraph(f"Tél : {telephone}", style_p(9)))

    info_tbl = Table(
        [[cell_fac, client_lines]],
        colWidths=[W * 0.45, W * 0.55]
    )
    info_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND",    (0, 0), (0, 0),   colors.HexColor("#f1f5f9")),
        ("BACKGROUND",    (1, 0), (1, 0),   colors.HexColor("#eff6ff")),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("LINEAFTER",     (0, 0), (0, 0),   0.5, colors.HexColor("#e5e7eb")),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Tableau des articles ──────────────────────────────────────────────────
    col_w = [W * 0.45, W * 0.12, W * 0.21, W * 0.22]
    headers = [
        Paragraph("Désignation",    style_p(9, bold=True, color=colors.black)),
        Paragraph("Qté",            style_p(9, bold=True, color=colors.black, align=TA_CENTER)),
        Paragraph("Prix unitaire",  style_p(9, bold=True, color=colors.black, align=TA_RIGHT)),
        Paragraph("Montant",        style_p(9, bold=True, color=colors.black, align=TA_RIGHT)),
    ]
    rows = [headers]

    for i, ligne in enumerate(lignes):
        if isinstance(ligne, dict):
            desig = ligne.get("designation", "")
            qte   = ligne.get("quantite", 0)
            pu    = ligne.get("prix_unitaire", 0)
            mt    = ligne.get("montant", 0)
        else:
            desig, qte, pu, mt = ligne[0], ligne[1], ligne[2], ligne[3]

        row = [
            Paragraph(str(desig), style_p(9)),
            Paragraph(f"{float(qte):g}", style_p(9, align=TA_CENTER)),
            Paragraph(f"{_fmt2(pu)} FCFA", style_p(9, align=TA_RIGHT)),
            Paragraph(f"{_fmt2(mt)} FCFA", style_p(9, align=TA_RIGHT)),
        ]
        rows.append(row)

    articles_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    row_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0),  coul_primaire),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(rows)):
        bg = colors.HexColor("#f9fafb") if i % 2 == 0 else colors.white
        row_styles.append(("BACKGROUND", (0, i), (-1, i), bg))

    articles_tbl.setStyle(TableStyle(row_styles))
    story.append(articles_tbl)
    story.append(Spacer(1, 3 * mm))

    # ── Total ─────────────────────────────────────────────────────────────────
    total_tbl = Table(
        [[Paragraph("TOTAL GÉNÉRAL", style_p(12, bold=True, color=colors.white, align=TA_RIGHT)),
          Paragraph(f"{_fmt2(total)} FCFA", style_p(14, bold=True, color=colors.white, align=TA_RIGHT))]],
        colWidths=[W * 0.6, W * 0.4]
    )
    total_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), coul_accent),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(total_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── Signature & Cachet ────────────────────────────────────────────────────
    afficher_sig    = conf.get("afficher_signature", False)
    afficher_cachet = conf.get("afficher_cachet", False)
    sig_path        = conf.get("signature_path", "")
    cachet_path     = conf.get("cachet_path", "")

    sig_elements = []
    if afficher_sig and sig_path and os.path.isfile(sig_path):
        try:
            sw = conf.get("signature_largeur_mm", 40) * mm
            sh = conf.get("signature_hauteur_mm", 20) * mm
            sig_elements.append(Image(sig_path, width=sw, height=sh,
                                      preserveAspectRatio=True))
        except Exception:
            pass
    cachet_elements = []
    if afficher_cachet and cachet_path and os.path.isfile(cachet_path):
        try:
            cw = conf.get("cachet_largeur_mm", 35) * mm
            ch = conf.get("cachet_hauteur_mm", 35) * mm
            cachet_elements.append(Image(cachet_path, width=cw, height=ch,
                                         preserveAspectRatio=True))
        except Exception:
            pass

    if sig_elements or cachet_elements:
        sc_data = [
            [sig_elements[0] if sig_elements else "",
             cachet_elements[0] if cachet_elements else ""]
        ]
        sc_tbl = Table(sc_data, colWidths=[W * 0.5, W * 0.5])
        sc_tbl.setStyle(TableStyle([
            ("ALIGN",  (0, 0), (0, 0), "LEFT"),
            ("ALIGN",  (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        story.append(sc_tbl)
        story.append(Spacer(1, 4 * mm))

    # ── Pied de page ─────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=colors.HexColor("#e5e7eb")))
    story.append(Spacer(1, 2 * mm))

    footer_parts = []
    if msg_merci:
        footer_parts.append(msg_merci)
    if mention_pmt:
        footer_parts.append(mention_pmt)
    footer_parts.append(f"Document édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")

    for txt in footer_parts:
        story.append(Paragraph(txt, style_p(8, align=TA_CENTER, color=colors.grey)))

    doc.build(story)
    return path


# ══════════════════════════════════════════════════════════════════════════════
# FONCTION UNIFIÉE (compatibilité ascendante)
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf(numero, client, telephone, date_str, lignes, total,
                 methode_paiement="", type_doc="facture") -> str:
    """
    Point d'entrée unifié.
    type_doc : 'facture' | 'ticket'
    """
    if type_doc == "ticket":
        return generate_ticket(numero, client, telephone, date_str,
                               lignes, total, methode_paiement)
    else:
        return generate_facture(numero, client, telephone, date_str,
                                lignes, total, methode_paiement)