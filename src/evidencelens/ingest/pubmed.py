import gzip
from pathlib import Path
from typing import Iterator
import polars as pl
from lxml import etree

KEEP = {"PubmedArticle", "DeleteCitation"}

def _txt(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""

def parse_file(path: Path) -> Iterator[dict]:
    """Streamingly parses large compressed PubMed XML files without crashing RAM."""
    with gzip.open(path, "rb") as fh:
        for _, el in etree.iterparse(fh, events=("end",), huge_tree=True):
            if el.tag not in KEEP:
                continue
            if el.tag == "DeleteCitation":
                for p in el.findall("PMID"):
                    yield {"op": "delete", "pmid": _txt(p)}
            else:
                mc = el.find("MedlineCitation")
                art = mc.find("Article")
                parts = []
                for at in art.findall("Abstract/AbstractText"):
                    label = at.get("Label")
                    parts.append(f"{label}: {_txt(at)}" if label else _txt(at))
                
                year = (art.findtext("Journal/JournalIssue/PubDate/Year")
                        or (art.findtext("Journal/JournalIssue/PubDate/MedlineDate") or "")[:4])
                
                yield {
                    "op": "upsert",
                    "pmid": _txt(mc.find("PMID")),
                    "title": _txt(art.find("ArticleTitle")),
                    "abstract": " ".join(p for p in parts if p),
                    "year": int(year) if year.isdigit() else None,
                    "journal": art.findtext("Journal/Title"),
                    "language": art.findtext("Language"),
                    "mesh": [_txt(x) for x in mc.findall("MeshHeadingList/MeshHeading/DescriptorName")],
                }
            # Clear element from memory to protect your 8GB RAM
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]