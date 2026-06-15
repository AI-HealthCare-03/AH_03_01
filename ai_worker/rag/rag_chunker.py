"""
RAG 파싱 & 청킹 파이프라인
"""

import json
import re
from collections import Counter
from pathlib import Path

import frontmatter

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.rag.topic_mapping import _get_topics
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─────────────────────────────────────────────
# 경로 설정
# ─────────────────────────────────────────────
BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
OUTPUT_DIR = BASE / "output"
OUTPUT_PATH = OUTPUT_DIR / "chunks.json"

OUTPUT_DIR.mkdir(exist_ok=True)  # output 폴더 없으면 자동 생성

# ─────────────────────────────────────────────
# 대상 파일 목록
# ─────────────────────────────────────────────
FILES = [
    DATA_DIR / "KDA2025_section_documentation.md",
    DATA_DIR / "KSH2026_section_documentation.md",
    DATA_DIR / "KSOLA2022_section_documentation.md",
    DATA_DIR / "CHALLENGE_CATALOG_documentation.md",
    DATA_DIR / "서비스_이용_가이드_20260610.md",
]

# ─────────────────────────────────────────────
# 청킹 설정
# ─────────────────────────────────────────────
CHUNK_SIZE = 500  # 글자 수 기준 (한국어 1글자 ≈ 1.5~2토큰)
CHUNK_OVERLAP = 100  # 겹침 글자 수
MIN_CHUNK_LEN = 10  # 이 미만은 빈 청크로 간주하여 제거

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

# ─────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────
SEC_HEADER = re.compile(
    r"^## ([A-Z][A-Z0-9_]+(?:_SEC_\d+|_FIG_\d+|FIG_\d+)) — (.+)$",
    re.MULTILINE,
)


def parse_section_metadata(meta_block: str) -> dict:
    """### Section Metadata 블록의 bullet 리스트를 dict로 변환"""
    result = {}
    for line in meta_block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        line = line[2:]
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip("`").strip('"').strip("'")
    return result


def split_content(text: str, metadata: dict) -> list[dict]:
    """
    CHUNK_SIZE 이하 → 청크 1개 유지
    CHUNK_SIZE 초과 → CHUNK_OVERLAP 겹침으로 분할
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [{**metadata, "chunk_index": 0, "chunk_total": 1, "content": text}]
    pieces = splitter.split_text(text)
    total = len(pieces)
    return [{**metadata, "chunk_index": i, "chunk_total": total, "content": piece} for i, piece in enumerate(pieces)]


# ─────────────────────────────────────────────
# 파서: SEC / FIG 구조 (모든 파일 공통)
# ─────────────────────────────────────────────
def parse_sec_file(filepath: Path) -> list[dict]:
    """## SOURCE_SEC_XXXX — 제목 구조 파일 파싱"""
    if not filepath.exists():
        print(f"  ⚠️  파일 없음, 건너뜀: {filepath}")
        return []

    post = frontmatter.load(filepath)
    file_meta = dict(post.metadata)
    body = post.content
    matches = list(SEC_HEADER.finditer(body))
    chunks = []

    for idx, match in enumerate(matches):
        section_id = match.group(1)
        section_title = match.group(2).strip()

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        block = body[start:end]

        # 섹션 메타데이터
        sec_meta = {}
        meta_match = re.search(r"### Section Metadata\s*\n(.*?)(?=\n### |\Z)", block, re.DOTALL)
        if meta_match:
            sec_meta = parse_section_metadata(meta_match.group(1))

        # 임베딩 제외 필터
        if sec_meta.get("allowed_for_embedding", "True").lower() == "false":
            continue
        if sec_meta.get("use_restriction", "") == "excluded_from_rag":
            continue

        # 임베딩 텍스트: Content + RAG요약 + 키워드
        content_parts = []

        content_match = re.search(r"### Content\s*\n(.*?)(?=\n### |\Z)", block, re.DOTALL)
        if content_match:
            content_parts.append(content_match.group(1).strip())

        rag_match = re.search(r"\n#{3} .*?RAG 검색용 요약.*?\n(.*?)(?=\n#{3} |\Z)", block, re.DOTALL)
        if rag_match:
            content_parts.append("[RAG요약] " + rag_match.group(1).strip())

        kw_match = re.search(r"\n#{3} .*?검색 키워드.*?\n(.*?)(?=\n#{3} |\Z)", block, re.DOTALL)
        if kw_match:
            keywords = [
                line.strip().lstrip("- ").strip()
                for line in kw_match.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]
            if keywords:
                content_parts.append("[키워드] " + ", ".join(keywords))

        full_text = "\n\n".join(filter(None, content_parts))

        base_meta = {
            **{k: v for k, v in file_meta.items() if k not in ("note", "section_count", "base_documentation")},
            **sec_meta,
            "section_id": section_id,
            "section_title": section_title,
            "file": filepath.name,
            "topics": _get_topics(section_id) or None,
        }

        chunks.extend(split_content(full_text, base_meta))

    print(f"  ✅ [{filepath.name}] 섹션 {len(matches)}개 → 청크 {len(chunks)}개")
    return chunks


# ─────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  RAG 청킹 파이프라인")
    print("=" * 55)

    all_chunks = []
    for fpath in FILES:
        all_chunks.extend(parse_sec_file(fpath))

    # 빈 청크 제거
    before = len(all_chunks)
    all_chunks = [c for c in all_chunks if len(c["content"].strip()) >= MIN_CHUNK_LEN]
    removed = before - len(all_chunks)

    # 저장
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    # 결과 리포트
    print()
    print(f"  총 청크: {len(all_chunks)}개  (빈 청크 {removed}개 제거)")
    print()
    print("  소스별 청크 수:")
    for src, cnt in sorted(Counter(c.get("source_id", "?") for c in all_chunks).items()):
        print(f"    {src:20s}: {cnt}개")

    lengths = [len(c["content"]) for c in all_chunks]
    print()
    print(f"  청크 길이 (글자): 최소 {min(lengths)} / 최대 {max(lengths)} / 평균 {sum(lengths) // len(lengths)}")
    print()
    print(f"  저장 완료 → {OUTPUT_PATH}")
    print("=" * 55)
