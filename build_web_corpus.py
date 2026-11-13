"""Create a compact, provenance-checked full-PDF index for the hosted Relay API.

Generated only from the three exact arXiv version PDFs by GitHub Actions.
No downloaded PDFs, credentials or personal data are committed.
"""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path

from retrieval_optimized import normalize
from relay import PAPERS, ROOT

OUT = ROOT / "data" / "web_corpus.json.gz"
PROVENANCE = ROOT / "data" / "web_corpus_manifest.json"


def build():
    import fitz
    manifest = json.loads((ROOT / "data/papers/manifest.json").read_text(encoding="utf-8"))
    if set(manifest) != set(PAPERS):
        raise ValueError("Corpus versions do not match the three assigned paper versions")
    pages = []
    for paper in PAPERS:
        file = ROOT / "data/papers" / (paper + ".pdf")
        source = file.read_bytes()
        if not source.startswith(b"%PDF-"):
            raise ValueError("A corpus file is not a PDF")
        digest = hashlib.sha256(source).hexdigest()
        if digest != manifest[paper]["sha256"]:
            raise ValueError("Source PDF does not match its recorded SHA256")
        with fitz.open(stream=source, filetype="pdf") as pdf:
            for page_no, page in enumerate(pdf, 1):
                text = normalize(page.get_text("text", sort=True))
                if len(text) > 30:
                    pages.append({"paper": paper, "page": page_no, "text": text})
    if len(pages) < 45:
        raise ValueError("Expected at least 45 non-empty research-paper pages")
    payload = {"schema": 1, "source_sha256": {v: manifest[v]["sha256"] for v in PAPERS},
               "pages": pages}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    report = {"schema": 1, "versions": list(PAPERS), "pages": len(pages),
              "uncompressed_bytes": len(raw), "compressed_bytes": OUT.stat().st_size,
              "compressed_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
              "source_sha256": payload["source_sha256"]}
    PROVENANCE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    build()
