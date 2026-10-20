"""
Leitura de PDF de medição (PC) para pré-preencher o formulário de lançamento.

Extrai: PC, prestador (razão/fantasia), OC, END ID, atividade, regional (rodapé) e valor total.
Depende do layout padrão dos PCs de medição CITRA (texto embutido, não OCR).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader


REGIONAIS = {"TNO", "TSP", "TRJ", "TLE", "TCO", "TNE", "TSL", "TSE", "TNE"}


@dataclass
class PcMedicaoImport:
    pc: str = ""
    razao_social: str = ""
    fantasia: str = ""
    oc: str = ""
    end_id: str = ""
    atividade: str = ""
    regional: str = ""
    valor_total: float = 0.0
    warnings: list[str] = field(default_factory=list)
    source_path: str = ""


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return _clean(value).upper()


def _parse_money_br(value: str) -> float | None:
    cleaned = value.strip().replace("R$", "").replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _pdf_items(path: Path) -> tuple[str, list[dict[str, Any]]]:
    reader = PdfReader(str(path))
    parts: list[str] = []
    items: list[dict[str, Any]] = []
    for page in reader.pages:
        def visitor(text, cm, tm, font_dict, font_size):
            cleaned = _clean(text)
            if not cleaned:
                return
            x, y = float(tm[4]), float(tm[5])
            parts.append(cleaned)
            if x == 0 and y == 0:
                return
            items.append({"x": x, "y": y, "text": cleaned})

        page.extract_text(visitor_text=visitor)
    return " ".join(parts), items


def _pdf_rows(items: list[dict[str, Any]], tolerance: float = 5.0) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=lambda v: (-v["y"], v["x"])):
        for row in rows:
            if abs(row[0]["y"] - item["y"]) <= tolerance:
                row.append(item)
                break
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda v: v["x"])
    return rows


def _row_text(row: list[dict[str, Any]]) -> str:
    return _clean(" ".join(it["text"] for it in row))


def _row_contains(row: list[dict[str, Any]], text: str) -> bool:
    target = _norm(text)
    return any(target in _norm(it["text"]) for it in row)


def _strip_documento_do_nome(nome: str) -> str:
    """Remove CNPJ/CPF grudado no início ou fim do nome."""
    t = _clean(nome)
    # CNPJ no início: 60.327.056 ou 60.327.056/0001-87
    t = re.sub(r"^[\d.]{6,}/\d{4}-\d{2}\s*", "", t)
    t = re.sub(r"^[\d.]{8,}\s+", "", t)
    # CPF/CNPJ só dígitos no final
    t = re.sub(r"\s+\d{11,14}$", "", t)
    t = re.sub(r"\s+\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", "", t)
    return _clean(t)


def _extract_pc(text: str) -> str:
    m = re.search(r"(PC_\d+(?:-\d{2}-\d{2}-\d{4})?)", text, re.IGNORECASE)
    if m:
        return m.group(1).upper().replace("PC_", "PC_")
    m = re.search(r"PC[_\s-]*(\d+(?:-\d{2}-\d{2}-\d{4})?)", text, re.IGNORECASE)
    if m:
        return f"PC_{m.group(1)}"
    return ""


def _extract_total(text: str, rows: list[list[dict[str, Any]]]) -> float | None:
    # Preferir linha SUBTOTAL com valor à direita
    for row in rows:
        if not _row_contains(row, "SUBTOTAL"):
            continue
        joined = _row_text(row)
        amounts = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", joined)
        if amounts:
            val = _parse_money_br(amounts[-1])
            if val and val > 0:
                return val
    # Fallback: TOTAL no texto (maior valor perto de TOTAL)
    for m in re.finditer(r"TOTAL\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})", text, re.I):
        val = _parse_money_br(m.group(1))
        if val and val > 0:
            return val
    amounts = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", text)
    parsed = [v for v in (_parse_money_br(a) for a in amounts) if v and v > 0]
    return max(parsed) if parsed else None


def _extract_razao_fantasia(rows: list[list[dict[str, Any]]]) -> tuple[str, str]:
    razao = ""
    fantasia = ""
    for row in rows:
        texts = [it["text"] for it in row]
        joined = _row_text(row)
        if _row_contains(row, "RAZÃO SOCIAL") or _row_contains(row, "RAZAO SOCIAL"):
            # pega trechos depois do label, antes de regional no canto
            parts = []
            for it in row:
                t = it["text"]
                if _norm(t) in {"RAZÃO SOCIAL", "RAZAO SOCIAL", "REGIONAL"}:
                    continue
                if _norm(t) in REGIONAIS:
                    continue
                if it["x"] > 520 and len(t) <= 4:
                    continue
                parts.append(t)
            razao = _strip_documento_do_nome(" ".join(parts))
        if _row_contains(row, "FANTASIA"):
            parts = []
            for it in row:
                t = it["text"]
                nt = _norm(t)
                if nt == "FANTASIA" or nt in REGIONAIS:
                    continue
                if re.match(r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$", t):
                    continue
                if it["x"] > 480 and ("/" in t or re.match(r"^[\d./-]+$", t)):
                    continue
                if nt in {"0", "-", "N/A"}:
                    continue
                parts.append(t)
            fantasia = _strip_documento_do_nome(" ".join(parts))
            if fantasia in {"0", "-"}:
                fantasia = ""
    return razao, fantasia


def _extract_oc_end_id(text: str) -> tuple[str, str]:
    oc = ""
    end_id = ""
    # Padrão rodapé: OC 1061024 END_ID MSTL5_0531 SITE_ID
    m = re.search(
        r"\bOC\s+([A-Z0-9._-]+)\s+END_ID\s+([A-Z0-9._-]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        oc_cand = m.group(1).strip()
        end_id = m.group(2).strip()
        if oc_cand not in {"-", ".", "–", "—"}:
            oc = oc_cand
        return oc, end_id

    m_end = re.search(r"END_ID\s+([A-Z0-9._-]+)", text, re.IGNORECASE)
    if m_end:
        end_id = m_end.group(1).strip()

    # OC isolado no rodapé (evitar cabeçalho "OC / PO")
    for m_oc in re.finditer(r"\bOC\s+([A-Z0-9._-]+)", text, re.IGNORECASE):
        cand = m_oc.group(1).strip()
        if cand.upper() in {"/", "PO", "ITEM"}:
            continue
        if cand not in {"-", ".", "–", "—"}:
            oc = cand
            break
    return oc, end_id


def _extract_regional_rodape(text: str, rows: list[list[dict[str, Any]]]) -> str:
    """Regional do bloco inferior (lado da cidade), não a do topo."""
    # No texto linear, após END_ID / SITE_ID costuma aparecer CIDADE ... REGIONAL Txx
    m = re.search(
        r"END_ID\s+\S+.*?REGIONAL\s+([A-Z]{2,4})\b",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m and m.group(1).upper() in REGIONAIS or (m and len(m.group(1)) <= 4):
        reg = m.group(1).upper()
        if reg in REGIONAIS or reg.startswith("T"):
            return reg

    # Linhas baixas (y < 400) com código de regional
    for row in rows:
        if row[0]["y"] > 400:
            continue
        if not (_row_contains(row, "CIDADE") or _row_contains(row, "REGIONAL")):
            # ainda assim pode ser só o código
            for it in row:
                if _norm(it["text"]) in REGIONAIS and it["x"] > 250:
                    return _norm(it["text"])
            continue
        for it in row:
            nt = _norm(it["text"])
            if nt in REGIONAIS:
                return nt
    # Último recurso: qualquer regional em y baixo
    for row in rows:
        if row[0]["y"] > 380:
            continue
        for it in row:
            if _norm(it["text"]) in REGIONAIS:
                return _norm(it["text"])
    return ""


def _extract_atividade(rows: list[list[dict[str, Any]]]) -> str:
    """Descrições de itens entre cabeçalho da tabela e SUBTOTAL."""
    header_y = None
    subtotal_y = None
    for row in rows:
        if _row_contains(row, "OC / PO") or (
            _row_contains(row, "DESCRIÇÃO") and _row_contains(row, "ITEM")
        ):
            header_y = row[0]["y"]
        if _row_contains(row, "SUBTOTAL"):
            subtotal_y = row[0]["y"]

    if header_y is None or subtotal_y is None:
        return ""

    descricoes: list[str] = []
    skip_tokens = {
        "SUBTOTAL", "DESCONTO", "TOTAL", "R$", "R", "SV", "UND", "QNTD", "UNIT",
        "FATURAMENTO", "DT LIBERAÇÃO", "MOBILIZAÇÃO DOS", "SERVIÇOS", "CONCLUSÃO DOS",
        "50% NA", "50% APÓS", "100%", "40%", "30%", "20%", "ITEM/JUSTIFICATIVAS",
        "OBSERVAÇÕES", "DESCRIÇÃO SERVIÇO MATERIAL/SERVIÇO",
    }
    for row in rows:
        y = row[0]["y"]
        if not (subtotal_y + 15 < y < header_y - 5):
            continue
        # texto na faixa da descrição (coluna central)
        parts = []
        for it in row:
            if it["x"] < 140 or it["x"] > 520:
                continue
            t = _clean(it["text"])
            nt = _norm(t)
            if not t or nt in skip_tokens:
                continue
            if "JUSTIFICATIVA" in nt or nt.startswith("OBSERVA"):
                continue
            if re.fullmatch(r"[\d\s.,/%-]+", t):
                continue
            if re.fullmatch(r"\d+", t):
                continue
            parts.append(t)
        if not parts:
            continue
        frase = _clean(" ".join(parts))
        if len(frase) < 4:
            continue
        if frase not in descricoes:
            descricoes.append(frase)

    return " / ".join(descricoes[:5])


def importar_pc_medicao(path: str | Path) -> PcMedicaoImport:
    """
    Lê um PDF de PC de medição e devolve os campos para o formulário.
    Levanta ValueError se PC ou valor total não forem encontrados.
    """
    path = Path(path)
    if not path.exists():
        raise ValueError(f"Arquivo não encontrado: {path}")

    text, items = _pdf_items(path)
    rows = _pdf_rows(items)
    warnings: list[str] = []

    pc = _extract_pc(text)
    if not pc:
        raise ValueError(
            "Não foi possível identificar o número do PC no PDF.\n\n"
            "Verifique se o arquivo é um PC de medição válido (texto selecionável, não só imagem)."
        )

    razao, fantasia = _extract_razao_fantasia(rows)
    if not razao and not fantasia:
        warnings.append("Prestador (razão social / fantasia) não identificado.")

    oc, end_id = _extract_oc_end_id(text)
    if not end_id:
        warnings.append("END ID não identificado.")
    if not oc:
        warnings.append("OC / PO não identificado (pode estar vazio no PDF).")

    regional = _extract_regional_rodape(text, rows)
    if not regional:
        warnings.append("Regional do rodapé não identificada.")

    atividade = _extract_atividade(rows)
    if not atividade:
        warnings.append("Descrição do serviço não identificada.")

    total = _extract_total(text, rows)
    if total is None or total <= 0:
        raise ValueError(
            "Não foi possível identificar o valor total do PC no PDF.\n\n"
            "Verifique se o documento possui SUBTOTAL / TOTAL legíveis."
        )

    return PcMedicaoImport(
        pc=pc,
        razao_social=razao,
        fantasia=fantasia,
        oc=oc,
        end_id=end_id,
        atividade=atividade,
        regional=regional,
        valor_total=total,
        warnings=warnings,
        source_path=str(path),
    )


def match_prestador_cadastrado(
    razao_pdf: str,
    fantasia_pdf: str,
    fornecedores: list[dict],
) -> str | None:
    """
    Retorna a razão social cadastrada se razão ou fantasia do PDF baterem
    (comparação case-insensitive, só por nome).
    """
    candidatos_pdf = []
    for nome in (razao_pdf, fantasia_pdf):
        n = _norm(nome)
        if n and n not in {"0", "-", "N/A"}:
            candidatos_pdf.append(n)

    if not candidatos_pdf:
        return None

    for f in fornecedores:
        razao = _norm(f.get("RAZÃO SOCIAL") or f.get("razao_social") or "")
        fantasia = _norm(f.get("RAZÃO FANTASIA") or f.get("razao_fantasia") or "")
        for cand in candidatos_pdf:
            if razao and (cand == razao or cand in razao or razao in cand):
                return (f.get("RAZÃO SOCIAL") or f.get("razao_social") or "").strip()
            if fantasia and (cand == fantasia or cand in fantasia or fantasia in cand):
                return (f.get("RAZÃO SOCIAL") or f.get("razao_social") or "").strip()
    return None
