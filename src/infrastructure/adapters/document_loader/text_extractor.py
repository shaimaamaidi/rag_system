class TextExtractor:
    """Extraction texte / header / table / metadata."""

    @staticmethod
    def remove_header(text: str, header: str) -> str:
        if not header or not text:
            return text
        if header in text:
            text = text.replace(header, "", 1)
        return text.strip()

    @staticmethod
    def extract_tables_metadata(content: str) -> list:
        import re
        tables_metadata = []
        md_tables = re.compile(r"((?:\|.*\|\s*\n)+)", re.MULTILINE).findall(content)
        for idx, table_text in enumerate(md_tables):
            lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
            if len(lines) < 2:
                continue
            col_count = lines[0].count("|") - 1
            row_count = len(lines[2:]) + 1
            tables_metadata.append({"table_index": idx, "row_count": row_count, "col_count": col_count})

        html_tables = re.compile(r"<table.*?>.*?</table>", re.DOTALL | re.IGNORECASE).findall(content)
        for idx, table_html in enumerate(html_tables, start=len(tables_metadata)):
            rows = re.findall(r"<tr.*?>", table_html, re.IGNORECASE)
            cols = re.findall(r"<t[dh].*?>", table_html, re.IGNORECASE)
            tables_metadata.append({"table_index": idx, "row_count": len(rows), "col_count": len(cols)})

        return tables_metadata