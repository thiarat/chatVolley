import os
import re
import uuid
from dotenv import load_dotenv

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from rank_bm25 import BM25Okapi

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────
CHUNK_SIZE_CHARS    = 600    # max characters per chunk
CHUNK_OVERLAP_CHARS = 120    # overlap characters between chunks
N_RETRIEVE          = 6      # candidate chunks to fetch (vector + BM25)
N_FINAL             = 3      # top chunks after reranking → sent to LLM
MAX_CHUNK_CHARS     = 1500   # max chars per chunk shown in context
MAX_CONTEXT_CHARS   = 5500   # total context character cap

# New multilingual collection name (forces re-index from old English-only one)
COLLECTION_NAME = "volleyball_rules_v2"
OLD_COLLECTION  = "volleyball_rules"

# Multilingual sentence-transformer (supports Thai, ~420 MB on first run)
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Larger, more capable LLM for Thai language
LLM_MODEL = "llama-3.3-70b-versatile"


# ─── Thai-friendly chunker ────────────────────────────────────────────────────
def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Paragraph-aware chunker that works well with Thai text.

    Strategy:
      1. Normalise line endings and collapse triple+ newlines.
      2. Split on double newlines (paragraph boundaries).
      3. Merge consecutive paragraphs until the chunk reaches `chunk_size`.
      4. Carry the last `overlap` characters into the next chunk for continuity.
      5. Oversized single paragraphs are further split by single newlines.
    """
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if not current:
            current = para
        elif len(current) + len(para) + 2 <= chunk_size:
            current += "\n\n" + para
        else:
            chunks.append(current)
            tail = current[-overlap:] if len(current) > overlap else current
            current = (tail + "\n\n" + para).strip()

    if current:
        chunks.append(current)

    # Second pass: split any still-oversized chunks by single newlines
    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= chunk_size * 1.5:
            final.append(chunk)
        else:
            lines = [ln.strip() for ln in chunk.split("\n") if ln.strip()]
            sub = ""
            for line in lines:
                if not sub:
                    sub = line
                elif len(sub) + len(line) + 1 <= chunk_size:
                    sub += "\n" + line
                else:
                    final.append(sub)
                    sub = line
            if sub:
                final.append(sub)

    return [c for c in final if len(c.strip()) > 20]


# ─── BM25 tokeniser (language-agnostic character trigrams) ───────────────────
def _tokenize(text: str) -> list[str]:
    """
    Character-level trigram tokeniser — works for Thai without a word segmenter.
    Whitespace tokens are also included to help with numeric / Latin content.
    """
    text = text.strip()
    if not text:
        return []
    grams = [text[i : i + 3] for i in range(max(len(text) - 2, 1))]
    words = text.split()
    return grams + words


# ─── RAGPipeline ──────────────────────────────────────────────────────────────
class RAGPipeline:
    def __init__(self):
        # ── Multilingual embedding function ──────────────────────────────────
        self._embed_fn = SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )

        # ── ChromaDB ─────────────────────────────────────────────────────────
        persist_path = os.path.join(os.path.dirname(__file__), "chroma_db")
        self._client = chromadb.PersistentClient(path=persist_path)

        # Remove the old English-only collection so the PDF gets re-indexed
        try:
            self._client.delete_collection(OLD_COLLECTION)
            print(f"🗑️  Removed old collection '{OLD_COLLECTION}' — will re-index with multilingual model")
        except Exception:
            pass  # Already gone, nothing to do

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

        # ── Groq LLM ─────────────────────────────────────────────────────────
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in the environment")
        self._llm = ChatGroq(
            api_key=api_key,
            model_name=LLM_MODEL,
            temperature=0.1,
        )

        # ── BM25 index (built lazily after first document load) ───────────────
        self._bm25: BM25Okapi | None = None
        self._bm25_docs: list[str] = []
        self._bm25_ids: list[str] = []

    # ── BM25 helpers ──────────────────────────────────────────────────────────

    def _build_bm25(self) -> None:
        """Load all documents from ChromaDB and rebuild the BM25 index."""
        if self._collection.count() == 0:
            return
        result = self._collection.get(include=["documents"])
        self._bm25_docs = result.get("documents") or []
        self._bm25_ids  = result.get("ids") or []
        tokenized = [_tokenize(d) for d in self._bm25_docs]
        self._bm25 = BM25Okapi(tokenized)
        print(f"📊 BM25 index built with {len(self._bm25_docs)} documents")

    # ── Public API ────────────────────────────────────────────────────────────

    def get_document_count(self) -> int:
        return self._collection.count()

    def load_document(self, text: str, source_name: str = "document") -> int:
        """
        Chunk `text` with the Thai-friendly chunker, embed with the multilingual
        model, and upsert into ChromaDB.  Returns the number of chunks created.
        """
        chunks = _chunk_text(text)
        if not chunks:
            return 0

        ids       = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [
            {"source": source_name, "chunk_index": i, "char_count": len(c)}
            for i, c in enumerate(chunks)
        ]

        self._collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        self._bm25 = None   # invalidate so it rebuilds on next query
        return len(chunks)

    # ── Query expansion ───────────────────────────────────────────────────────

    def _expand_query(self, question: str) -> list[str]:
        """
        Ask the LLM to generate 2 paraphrase queries to widen recall.
        Falls back gracefully to [question] on any error.
        """
        try:
            prompt = (
                "คุณเป็นผู้ช่วยสร้างคำถามค้นหากติกาวอลเลย์บอล\n"
                f"คำถามต้นฉบับ: {question}\n\n"
                "สร้างคำถามที่มีความหมายคล้ายกันหรือเกี่ยวข้อง 2 ข้อ "
                "เพื่อช่วยให้ค้นหาข้อมูลกติกาได้ครอบคลุมมากขึ้น\n"
                "ตอบเฉพาะ 2 คำถาม แต่ละข้อขึ้นบรรทัดใหม่ ไม่ต้องมีหมายเลขหรือคำอธิบาย"
            )
            resp = self._llm.invoke([HumanMessage(content=prompt)])
            alts = [
                q.strip()
                for q in resp.content.strip().splitlines()
                if q.strip()
            ][:2]
            queries = [question] + alts
            print(f"🔍 Query expansion: {queries}")
            return queries
        except Exception as exc:
            print(f"⚠️  Query expansion failed ({exc}), using original query only")
            return [question]

    # ── Hybrid retrieval ──────────────────────────────────────────────────────

    def _hybrid_retrieve(
        self, queries: list[str], n: int
    ) -> list[tuple[str, float]]:
        """
        Combine ChromaDB vector search and BM25 keyword search.

        For each query, retrieve `n` candidates from ChromaDB.
        De-duplicate by chunk ID, taking the best vector score per ID.
        Compute BM25 scores for the same queries over the full corpus.
        Merge: combined_score = 0.70 * vec_score + 0.30 * bm25_score
        Return top-`n` (document_text, combined_score) sorted descending.
        """
        # --- Vector search ---
        best_vec: dict[str, tuple[str, float]] = {}
        for q in queries:
            res  = self._collection.query(
                query_texts=[q],
                n_results=min(n, self._collection.count()),
            )
            docs  = res["documents"][0] if res["documents"] else []
            dists = res["distances"][0] if res.get("distances") else []
            ids   = res["ids"][0]       if res["ids"] else []
            for doc, dist, did in zip(docs, dists, ids):
                score = max(0.0, 1.0 - float(dist))
                if did not in best_vec or best_vec[did][1] < score:
                    best_vec[did] = (doc, score)

        # --- BM25 search ---
        if self._bm25 is None:
            self._build_bm25()

        bm25_scores: dict[str, float] = {}
        if self._bm25 and self._bm25_ids:
            for q in queries:
                raw     = self._bm25.get_scores(_tokenize(q))
                max_raw = float(max(raw)) if len(raw) > 0 else 1.0
                max_raw = max_raw if max_raw > 0 else 1.0
                for did, sc in zip(self._bm25_ids, raw):
                    norm = float(sc) / max_raw
                    if did not in bm25_scores or bm25_scores[did] < norm:
                        bm25_scores[did] = norm

        # --- Merge scores (70 % vector, 30 % BM25) ---
        combined: list[tuple[str, float]] = []
        for did, (doc, vec_sc) in best_vec.items():
            bm25_sc  = bm25_scores.get(did, 0.0)
            final_sc = 0.70 * vec_sc + 0.30 * bm25_sc
            combined.append((doc, final_sc))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:n]

    # ── Main query ────────────────────────────────────────────────────────────

    def query(self, question: str, n_results: int = N_RETRIEVE) -> dict:
        """
        Full RAG pipeline:
          1. Query expansion  → 3 queries
          2. Hybrid retrieval → up to N_RETRIEVE candidates
          3. Keep top N_FINAL after reranking
          4. Build context string
          5. Call Groq LLM with improved Thai prompt
        """
        if self._collection.count() == 0:
            return {
                "answer":       "ยังไม่มีเอกสารในระบบ กรุณาอัปโหลด PDF ก่อน",
                "source_chunk": None,
                "confidence":   None,
            }

        # 1. Query expansion
        queries = self._expand_query(question)

        # 2. Hybrid retrieval
        retrieved = self._hybrid_retrieve(queries, n=n_results)

        if not retrieved:
            return {
                "answer":       "ไม่พบข้อมูลที่เกี่ยวข้องในเอกสาร",
                "source_chunk": None,
                "confidence":   0.0,
            }

        # 3. Keep top N_FINAL chunks
        top        = retrieved[:N_FINAL]
        confidence = float(top[0][1])

        # 4. Build context (respect MAX_CONTEXT_CHARS)
        context_parts: list[str] = []
        used_chars = 0
        for doc, _ in top:
            trimmed = doc[:MAX_CHUNK_CHARS]
            if used_chars + len(trimmed) > MAX_CONTEXT_CHARS:
                break
            context_parts.append(trimmed)
            used_chars += len(trimmed)
        context = "\n\n---\n\n".join(context_parts)

        # 5. Generate answer with improved Thai / volleyball-specific prompt
        system_prompt = (
            "คุณคือผู้เชี่ยวชาญด้านกติกาวอลเลย์บอลสากล (FIVB)\n\n"
            "กฎการตอบ:\n"
            "1. ตอบโดยอิงจากเนื้อหาที่ให้มาเท่านั้น ห้ามเพิ่มข้อมูลนอกเนื้อหา\n"
            "2. ตอบเป็นภาษาเดียวกับคำถาม\n"
            "3. หากมีหมายเลขกฎหรือข้อกำหนดในเนื้อหา ให้อ้างอิงด้วย (เช่น กฎข้อ 7.3)\n"
            "4. ถ้ามีหลายประเด็น ให้แบ่งเป็นข้อ ๆ อ่านง่าย\n"
            "5. ถ้าเนื้อหาไม่เพียงพอ ให้ตอบตรง ๆ ว่า 'ไม่พบข้อมูลนี้ในเอกสาร'\n"
            "6. ห้ามคาดเดาหรือแต่งเติมข้อมูลที่ไม่มีในเนื้อหา\n\n"
            f"เนื้อหากติกา:\n{context}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]
        response = self._llm.invoke(messages)
        answer = response.content.strip() if response.content else "ไม่สามารถสร้างคำตอบได้"

        return {
            "answer":       answer,
            "source_chunk": top[0][0][:MAX_CHUNK_CHARS],
            "confidence":   confidence,
        }
