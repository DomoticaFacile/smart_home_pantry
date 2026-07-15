# Creato da domoticafacile.it

import io
import zipfile
from datetime import datetime


def _esc(text):
    s = str(text if text is not None else "")
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "&quot;").replace("'", "&apos;")

    return "".join(c for c in s if c == "\t" or c == "\n" or ord(c) >= 32)


def _col_letter(idx):

    letters = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def build_xlsx(rows, sheet_name="Prodotti scaduti"):

    sheet_rows = []
    for r_i, row in enumerate(rows):
        cells = []
        for c_i, value in enumerate(row):
            ref = _col_letter(c_i) + str(r_i + 1)
            style = ' s="1"' if r_i == 0 else ""
            cells.append(
                '<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{val}</t></is></c>'.format(
                    ref=ref, style=style, val=_esc(value)
                )
            )
        sheet_rows.append(
            '<row r="{r}">{cells}</row>'.format(r=r_i + 1, cells="".join(cells))
        )

    n_cols = max((len(r) for r in rows), default=1)
    cols_xml = "".join(
        '<col min="{i}" max="{i}" width="24" customWidth="1"/>'.format(i=i + 1)
        for i in range(n_cols)
    )

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<cols>{cols}</cols>"
        "<sheetData>{rows}</sheetData>"
        "</worksheet>"
    ).format(cols=cols_xml, rows="".join(sheet_rows))

    # --- workbook ---
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="{name}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    ).format(name=_esc(sheet_name)[:31] or "Foglio1")

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        "<font><sz val="
        '"11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        "</fonts>"
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        "</styleSheet>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", styles_xml)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    return buf.getvalue()


def expired_rows(products, today=None):

    from datetime import date

    if today is None:
        today = date.today()

    header = [
        "Nome prodotto",
        "Codice a barre",
        "Quantita",
        "Data di scadenza",
        "Giorni dalla scadenza",
    ]
    rows = [header]

    def sort_key(p):
        return p.get("expiry_date") or "9999-12-31"

    for p in sorted(products, key=sort_key):
        expiry = p.get("expiry_date") or ""
        giorni = ""
        if expiry:
            try:
                d = datetime.strptime(expiry, "%Y-%m-%d").date()
                giorni = str((today - d).days)
            except ValueError:
                giorni = ""
        rows.append([
            p.get("name") or "",
            p.get("barcode") or "",
            p.get("quantity", 0),
            expiry,
            giorni,
        ])

    return rows
