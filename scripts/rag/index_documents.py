"""만성질환 진료지침·서비스 가이드 4종을 RAGDocument(PGVector) 에 인덱싱한다.

대상 파일 (frontmatter 의 source_id → app/models/rag.py RAGDocument.source 로 매핑):
    KDA2025          — 2025 당뇨병 진료지침
    KSH2022          — 2022 고혈압 진료지침 5판
    DYS_GUIDELINE    — 이상지질혈증 치료지침 4판
    GUIDE            — 서비스 이용 가이드

파이프라인:
    1. python-frontmatter 로 파일 메타 + 본문 분리
    2. `## XXX_SEC_dddd — 제목` 또는 `## XXX_FIG_dddd — 제목` 정규식으로 섹션 분할
    3. 각 섹션의 `### Section Metadata` 블록을 dict 로 파싱
       - allowed_for_embedding == false 또는 use_restriction == excluded_from_rag 섹션 제외
    4. 임베딩 텍스트 = `### Content` + `### RAG 검색용 요약` + `### 검색 키워드` 결합
       (팀원 `ai_worker/rag/rag_chunker.py` 와 동일 로직)
    5. 500자/100자 overlap RecursiveCharacterTextSplitter 로 청크 분할 (10자 미만 제거)
    6. OpenAI text-embedding-3-small (1536d) 로 배치 임베딩 (배치 50, 3회 재시도)
    7. Tortoise ORM 으로 RAGDocument 적재

실행:
    uv run python -m scripts.rag.index_documents              # 기본 (이미 적재된 source 는 건너뜀)
    uv run python -m scripts.rag.index_documents --reset      # 같은 source_id 들의 기존 행 삭제 후 재적재
    uv run python -m scripts.rag.index_documents --dry-run    # 임베딩/적재 없이 청크 수만 리포트
    uv run python -m scripts.rag.index_documents --dump out.json  # 청크 전체를 JSON 파일로 덤프 (검수용, DB·API 미사용)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import frontmatter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.models.rag import DocumentType, RAGDocument
from scripts.rag.topic_mapping import _get_topics

# ─────────────────────────────────────────────
# 경로 / 대상 파일
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "RAG" / "final docs"

FILES: list[Path] = sorted(DOCS_DIR.glob("*.md"))


def _find_file(name_nfc: str) -> Path:
    """NFC/NFD 인코딩 차이를 무시하고 DOCS_DIR 에서 파일을 찾는다."""
    import unicodedata

    nfc = unicodedata.normalize("NFC", name_nfc)
    for f in DOCS_DIR.iterdir():
        if unicodedata.normalize("NFC", f.name) == nfc:
            return f
    return DOCS_DIR / name_nfc  # 없으면 원래 경로 반환 (오류 메시지용)


def _find_latest_by_prefix(prefix: str) -> Path:
    """prefix 로 시작하는 .md 파일 중 파일명 기준 가장 최신(사전순 마지막)을 반환한다.
    예) '서비스_이용_가이드_' → '서비스_이용_가이드_20261001.md' 자동 선택.
    파일이 없으면 오류 메시지용 더미 경로를 반환한다.
    """
    import unicodedata

    nfc_prefix = unicodedata.normalize("NFC", prefix)
    candidates = [
        f
        for f in DOCS_DIR.iterdir()
        if f.suffix == ".md" and unicodedata.normalize("NFC", f.name).startswith(nfc_prefix)
    ]
    if not candidates:
        return DOCS_DIR / f"{prefix}*.md"  # 없으면 더미 경로 (오류 메시지용)
    return max(candidates, key=lambda f: unicodedata.normalize("NFC", f.name))


# ─────────────────────────────────────────────
# 청킹 / 임베딩 설정 (팀원 프로토타입과 동일 파라미터)
# ─────────────────────────────────────────────
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MIN_CHUNK_LEN = 100

EMBEDDING_BATCH = 50
EMBEDDING_RETRY = 3
EMBEDDING_RETRY_DELAY = 5  # seconds

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

# `## KDA2025_SEC_0001 — 당뇨병`, `## DYS_FIG_001 — ...`, `## GUIDE_SEC_001 — ...`,
# 그리고 `## KSLA2022_SEC_0020_A — ...` (숫자 뒤 _접미사) 형태까지 모두 매칭.
SEC_HEADER = re.compile(
    r"^## ([A-Z][A-Z0-9_]+(?:_SEC_\d+(?:_[A-Z0-9]+)?|_FIG_\d+|FIG_\d+)) — (.+)$",
    re.MULTILINE,
)

# 서비스 가이드 + 챌린지 카탈로그는 GUIDELINE(의료 진료지침) 이 아니라 OTHER 로 적재하고
# metadata.doc_type 으로 구분한다. retrieve 의 source_type="service" 필터에서 둘 다 매치.
# (`DocumentType` enum 에 SERVICE_GUIDE 신규 값을 추가하려면 컬럼 길이도 ALTER 가 필요해
#  최소 변경 원칙상 OTHER + metadata + source 로 우회.)
SERVICE_GUIDE_SOURCES = {"GUIDE", "CHALLENGE_CATALOG"}

# scripts/rag/index_documents.py 에 추가할 TOPIC_MAPPING
# topic 값: diagnosis / medication / lifestyle / complication / risk / monitoring / service


# M-6 sanity 허용 figure 접두사 — 각 진료지침이 본문에 다른 자료의 figure 를 인용하는
# 경우가 있어 source_id prefix 외에 추가 허용 (silent 매치 경고 false positive 방지).
_KNOWN_FIGURE_PREFIXES = ("DYS_FIG_", "HTN_FIG_", "DM_FIG_", "CHALL_SEC_", "CHALL_FIG_")


# ─────────────────────────────────────────────
# 청킹 헬퍼
# ─────────────────────────────────────────────
def parse_section_metadata(meta_block: str) -> dict[str, str]:
    """`### Section Metadata` 블록의 bullet 리스트 → dict."""
    result: dict[str, str] = {}
    for raw in meta_block.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        line = line[2:]
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip("`").strip('"').strip("'")
    return result


def split_section_text(text: str) -> list[tuple[int, int, str]]:
    """(chunk_index, chunk_total, chunk_text) 튜플 목록을 돌려준다."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [(0, 1, text)]
    pieces = splitter.split_text(text)
    total = len(pieces)
    return [(i, total, p) for i, p in enumerate(pieces)]


def build_embedding_text(block: str) -> str:
    """팀원과 동일하게 Content + RAG요약 + 키워드 를 합쳐 임베딩 입력 텍스트로 만든다."""
    parts: list[str] = []

    content_match = re.search(r"### Content\s*\n(.*?)(?=^### |\Z)", block, re.DOTALL | re.MULTILINE)
    if content_match:
        parts.append(content_match.group(1).strip())

    rag_match = re.search(r"^#{3,5}.*?RAG 검색용 요약.*?\n(.*?)(?=^#{3,5}|\Z)", block, re.DOTALL | re.MULTILINE)
    if rag_match:
        parts.append("[RAG요약] " + rag_match.group(1).strip())

    kw_match = re.search(r"^#{3,5}.*?(?:검색 키워드|Keywords).*?\n(.*?)(?=^#{3,5}|\Z)", block, re.DOTALL | re.MULTILINE)
    if kw_match:
        keywords = [
            line.strip().lstrip("- ").strip()
            for line in kw_match.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]
        if keywords:
            parts.append("[키워드] " + ", ".join(keywords))

    return "\n\n".join(p for p in parts if p)


def parse_file(filepath: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:  # noqa: C901 — 평면 파싱 분기
    """파일 1개를 파싱해 (file_meta, chunks) 를 돌려준다."""
    if not filepath.exists():
        print(f"  ⚠️  파일 없음, 건너뜀: {filepath}")
        return {}, []

    post = frontmatter.load(filepath)
    file_meta = dict(post.metadata)
    body = post.content
    matches = list(SEC_HEADER.finditer(body))

    # M-6 sanity: section_id 가 frontmatter.source_id 의 prefix(예: "KSLA2022")로 시작하거나
    # 의료 도메인의 알려진 figure 접두사 인지 sample 검증. 정규식 확장으로 의도 외 패턴이
    # 매치되면 즉시 경고 (silent 매치 방지).
    # 알려진 figure 접두사: 각 진료지침이 본문에 다른 자료의 figure 를 인용하는 경우가 있음.
    source_id_str = str(file_meta.get("source_id") or "")
    if source_id_str and matches:
        sample_ids = [m.group(1) for m in matches[:5]]
        for sid in sample_ids:
            if not (sid.startswith(source_id_str) or sid.startswith(_KNOWN_FIGURE_PREFIXES)):
                print(f"  ⚠️  [{filepath.name}] 의심 section_id 매치: {sid} (source_id={source_id_str})")

    chunks: list[dict[str, Any]] = []
    skipped = 0

    for idx, match in enumerate(matches):
        section_id = match.group(1)
        section_title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        block = body[start:end]

        sec_meta: dict[str, str] = {}
        meta_match = re.search(r"### Section Metadata\s*\n(.*?)(?=### |\Z)", block, re.DOTALL)
        if meta_match:
            sec_meta = parse_section_metadata(meta_match.group(1))

        # 임베딩 제외 필터 (팀원과 동일)
        if sec_meta.get("allowed_for_embedding", "True").lower() == "false":
            skipped += 1
            continue
        if sec_meta.get("use_restriction", "") == "excluded_from_rag":
            skipped += 1
            continue
        # pediatric_only 섹션은 일반 성인 검색풀에서 제외.
        # 소아 전용 검색 경로가 생기면 별도 처리 예정.
        if sec_meta.get("use_restriction", "") == "pediatric_only":
            skipped += 1
            continue

        full_text = build_embedding_text(block)
        if not full_text or len(full_text.strip()) < MIN_CHUNK_LEN:
            skipped += 1
            continue

        for chunk_index, chunk_total, chunk_text in split_section_text(full_text):
            if len(chunk_text.strip()) < MIN_CHUNK_LEN:
                continue
            chunks.append(
                {
                    "section_id": section_id,
                    "section_title": section_title,
                    "chunk_index": chunk_index,
                    "chunk_total": chunk_total,
                    "chunk_text": chunk_text,
                    "sec_meta": sec_meta,
                }
            )

    print(f"  ✅ [{filepath.name}] 섹션 {len(matches)}개 (제외 {skipped}) → 청크 {len(chunks)}개")
    return file_meta, chunks


# ─────────────────────────────────────────────
# 임베딩
# ─────────────────────────────────────────────
def _safe_err_repr(e: BaseException) -> str:
    """OpenAI SDK 예외에서 API key prefix/요청 body 가 그대로 stdout/로그에 새는 걸 막는다.

    예외 타입명과 메시지 첫 줄 일부만 노출 (요청 ID/헤더/페이로드 마스킹).
    """
    head = str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {head[:120]}"


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    last_err: Exception | None = None
    for attempt in range(EMBEDDING_RETRY):
        try:
            resp = client.embeddings.create(model=config.OPENAI_EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:  # noqa: BLE001 — OpenAI SDK 의 다양한 예외 통합 처리
            last_err = e
            print(f"  ⚠️  임베딩 오류 (시도 {attempt + 1}/{EMBEDDING_RETRY}): {_safe_err_repr(e)}")
            if attempt < EMBEDDING_RETRY - 1:
                time.sleep(EMBEDDING_RETRY_DELAY)
    raise RuntimeError(f"임베딩 {EMBEDDING_RETRY}회 실패: {_safe_err_repr(last_err) if last_err else 'unknown'}")


# ─────────────────────────────────────────────
# DB 적재
# ─────────────────────────────────────────────
def doc_type_for(source_id: str) -> DocumentType:
    if source_id in SERVICE_GUIDE_SOURCES:
        return DocumentType.OTHER
    return DocumentType.GUIDELINE


def truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[: limit - 1] + "…"


async def load_chunks_to_db(
    source_id: str,
    file_meta: dict[str, Any],
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> int:
    objects: list[RAGDocument] = []
    for chunk, vec in zip(chunks, embeddings, strict=True):
        sec_meta = chunk["sec_meta"]
        topics = _get_topics(chunk["section_id"])
        metadata = {
            # 파일/문서 레벨
            "source_id": source_id,
            "source_title": file_meta.get("source_title"),
            "source_file": file_meta.get("source_file"),
            "disease": file_meta.get("disease"),
            "disease_ko": file_meta.get("disease_ko"),
            "language_original": file_meta.get("language_original"),
            "documentation_type": file_meta.get("documentation_type") or file_meta.get("doc_type"),
            "doc_type": file_meta.get("doc_type")
            or ("service_guide" if source_id in SERVICE_GUIDE_SOURCES else "guideline"),
            # 섹션 레벨
            "section_id": chunk["section_id"],
            "section_title": chunk["section_title"],
            "chunk_total": chunk["chunk_total"],
            "source_pages": sec_meta.get("source_pages"),
            "content_hash": sec_meta.get("content_hash"),
            "translation_status": sec_meta.get("translation_status"),
            "topics": topics if topics else None,  # 빈 리스트는 None으로
        }
        # None 값 제거 (검색 필터/디버깅 가독성)
        metadata = {k: v for k, v in metadata.items() if v is not None}

        objects.append(
            RAGDocument(
                document_type=doc_type_for(source_id),
                source=source_id,
                title=truncate(chunk["section_title"], 200),
                chunk_index=chunk["chunk_index"],
                chunk_text=chunk["chunk_text"],
                embedding=vec,
                metadata=metadata,
                is_active=True,
            )
        )

    # bulk_create 는 PGVector 컬럼도 잘 처리 (asyncpg 연결마다 register_vector 등록됨)
    await RAGDocument.bulk_create(objects, batch_size=100)
    return len(objects)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def dump_chunks_to_json(
    parsed: list[tuple[str, dict[str, Any], list[dict[str, Any]]]],
    out_path: Path,
) -> None:
    """검수용: 모든 청크를 풍부한 메타와 함께 JSON 으로 직렬화한다 (임베딩/DB 미사용)."""
    payload: list[dict[str, Any]] = []
    for source_id, file_meta, chunks in parsed:
        for c in chunks:
            payload.append(
                {
                    "source_id": source_id,
                    "section_id": c["section_id"],
                    "section_title": c["section_title"],
                    "chunk_index": c["chunk_index"],
                    "chunk_total": c["chunk_total"],
                    "char_len": len(c["chunk_text"]),
                    "disease": file_meta.get("disease"),
                    "doc_type": file_meta.get("doc_type") or file_meta.get("documentation_type"),
                    "source_pages": c["sec_meta"].get("source_pages"),
                    "content_hash": c["sec_meta"].get("content_hash"),
                    "translation_status": c["sec_meta"].get("translation_status"),
                    "document_type_target": doc_type_for(source_id).value,
                    "chunk_text": c["chunk_text"],
                }
            )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 간단 통계 리포트
    lengths = [p["char_len"] for p in payload]
    print(f"\n  📄 청크 덤프 → {out_path}")
    print(
        f"  총 청크: {len(payload)}개 | 길이(글자): min={min(lengths)} / max={max(lengths)} / avg={sum(lengths) // len(lengths)}"
    )
    print("  소스별 청크 수:")
    from collections import Counter

    for src, cnt in sorted(Counter(p["source_id"] for p in payload).items()):
        print(f"    {src:18s}: {cnt}")


async def main(  # noqa: C901 — 일회성 ops 스크립트, 단계별 분기를 한 함수에 두는 게 가독성에 유리
    reset: bool,
    dry_run: bool,
    dump_path: Path | None,
    assume_yes: bool = False,
) -> int:
    if not config.OPENAI_API_KEY and not dry_run and dump_path is None:
        print("❌ OPENAI_API_KEY 가 비어 있습니다. envs/.local.env 확인 후 다시 실행하세요.", file=sys.stderr)
        return 2

    print("=" * 60)
    print("  RAG 인덱싱 — final docs → RAGDocument (PGVector 1536d)")
    print(f"  dry_run={dry_run} reset={reset} dump={dump_path}")
    print("=" * 60)

    # 1) 파싱 + 청킹
    parsed: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    for fpath in FILES:
        file_meta, chunks = parse_file(fpath)
        if not chunks:
            continue
        source_id = str(file_meta.get("source_id") or "UNKNOWN")
        parsed.append((source_id, file_meta, chunks))

    total_chunks = sum(len(c) for _, _, c in parsed)
    print(f"\n  총 청크: {total_chunks}개 (소스 {len(parsed)}개)")

    if dump_path is not None:
        dump_chunks_to_json(parsed, dump_path)
        # 덤프는 검수 목적이므로 임베딩/적재 없이 여기서 종료
        return 0

    if dry_run:
        print("\n  --dry-run: 임베딩/적재 없이 종료")
        return 0

    if total_chunks == 0:
        print("  ⚠️  적재할 청크가 없습니다.")
        return 0

    # 2) Tortoise 초기화 (pgvector 코덱은 풀의 init 콜백으로 자동 등록 — databases.py 참조)
    await Tortoise.init(config=TORTOISE_ORM)

    try:
        # 3) reset 옵션: 같은 source 의 기존 행 삭제 (운영 DB 오인 보호)
        sources_in_run = [s for s, _, _ in parsed]
        if reset:
            existing_count = await RAGDocument.filter(source__in=sources_in_run).count()
            print(
                f"\n  ⚠️  --reset: DB={config.DB_HOST}/{config.DB_NAME} 의 "
                f"source {sources_in_run} 총 {existing_count}행을 삭제합니다."
            )
            if assume_yes:
                print("  (--yes 로 확인 생략)")
            else:
                answer = input("  진행하시려면 'yes' 입력: ").strip().lower()
                if answer != "yes":
                    print("  취소되었습니다.")
                    return 1
            deleted = await RAGDocument.filter(source__in=sources_in_run).delete()
            print(f"  ✅ {deleted}행 삭제 완료")
        else:
            # 기본 동작: 이미 적재된 source 는 건너뜀 (중복 적재 방지)
            existing = await RAGDocument.filter(source__in=sources_in_run).distinct().values_list("source", flat=True)
            existing_set = set(existing)
            if existing_set:
                print(f"\n  이미 적재된 source 건너뜀: {sorted(existing_set)}")
                parsed = [t for t in parsed if t[0] not in existing_set]
                if not parsed:
                    print("  → 적재할 새 source 없음 (재적재하려면 --reset).")
                    return 0

        # 4) 임베딩 + 적재 (소스 단위로 처리)
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        grand_total = 0
        for source_id, file_meta, chunks in parsed:
            print(f"\n  ── {source_id}: {len(chunks)}청크 임베딩/적재 ──")
            embeddings: list[list[float]] = []
            for batch_start in range(0, len(chunks), EMBEDDING_BATCH):
                batch = chunks[batch_start : batch_start + EMBEDDING_BATCH]
                texts = [c["chunk_text"] for c in batch]
                vecs = embed_batch(client, texts)
                if vecs and len(vecs[0]) != 1536:
                    raise RuntimeError(f"임베딩 차원이 1536 이 아님: {len(vecs[0])} — 모델/컬럼 차원을 확인하세요.")
                embeddings.extend(vecs)
                print(
                    f"    배치 {batch_start // EMBEDDING_BATCH + 1}"
                    f" / {(len(chunks) + EMBEDDING_BATCH - 1) // EMBEDDING_BATCH}"
                    f" — 누적 {len(embeddings)}/{len(chunks)}"
                )

            inserted = await load_chunks_to_db(source_id, file_meta, chunks, embeddings)
            grand_total += inserted
            print(f"    ✅ {source_id}: {inserted}행 적재")

        # 5) BM25 인덱스 무효화 — 같은 프로세스 안에서만 즉시 효과. FastAPI 워커는
        # 별도 프로세스라 자동 반영되지 않으므로, 운영 워커 재시작 또는 admin
        # reload 신호가 별도로 필요하다는 점을 경고로 남긴다.
        from app.services.ml.retrieval import invalidate_bm25_index

        invalidate_bm25_index()

        # 6) 리포트 — 이번 실행에서 적재된 source 들의 누적 행 수
        print("\n" + "=" * 60)
        print(f"  🎉 적재 완료: 이번 실행 {grand_total}행")
        print("  소스별 누적 행 수 (rag_documents 전체):")
        for src in sorted({s for s, _, _ in parsed}):
            cnt = await RAGDocument.filter(source=src).count()
            print(f"    {src:18s}: {cnt}행")
        print("=" * 60)
        print("  ⚠️  운영 FastAPI 워커는 BM25 인덱스를 부팅 시점에 메모리에 적재하므로")
        print("     본 인덱싱 결과를 즉시 반영하려면 워커 재시작이 필요합니다.")
        return 0
    finally:
        await Tortoise.close_connections()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reset", action="store_true", help="대상 source 의 기존 행 삭제 후 재적재")
    p.add_argument("--dry-run", action="store_true", help="임베딩/적재 없이 청크 통계만 출력")
    p.add_argument(
        "--dump",
        type=Path,
        metavar="OUT.json",
        help="청크 전체를 JSON 파일로 덤프 (검수용, 임베딩/DB 미사용)",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="--reset 의 확인 프롬프트를 건너뛴다 (CI/자동화용)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(
        asyncio.run(
            main(
                reset=args.reset,
                dry_run=args.dry_run,
                dump_path=args.dump,
                assume_yes=args.yes,
            )
        )
    )
