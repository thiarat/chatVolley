from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time
import os
import io
import pdfplumber
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from chatpdf_pipeline import ChatPDFPipeline

load_dotenv()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Volleyball Rules RAG API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = ChatPDFPipeline()

# --- DB Connection ---
def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Ensure sslmode=require is in the URL (Supabase needs it)
        if "sslmode" not in db_url:
            sep = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{sep}sslmode=require"
        return psycopg2.connect(db_url)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "volleyball_rag"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qa_log (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            source_chunk TEXT,
            confidence REAL,
            response_time_ms INTEGER,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            session_id VARCHAR(36)
        )
    """)
    # Add session_id column for existing tables that don't have it yet
    cur.execute("""
        ALTER TABLE qa_log ADD COLUMN IF NOT EXISTS session_id VARCHAR(36)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            qa_id INTEGER NOT NULL REFERENCES qa_log(id),
            rating TEXT NOT NULL CHECK(rating IN ('like', 'dislike')),
            timestamp TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # Table for soft-deleted sessions (ซ่อนจาก sidebar แต่ข้อมูลยังอยู่ใน DB)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hidden_sessions (
            session_id VARCHAR(36) PRIMARY KEY,
            hidden_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ PostgreSQL DB initialized")

def auto_load_pdf():
    if rag.get_document_count() > 0:
        print(f"ℹ️  ChatPDF source_id มีอยู่แล้ว — ข้ามการอัปโหลด")
        return
    candidates = [os.path.join(_BASE_DIR, "volleyball_rules.pdf")]
    pdf_path = next((p for p in candidates if os.path.exists(p)), None)
    if pdf_path is None:
        print("⚠️  ไม่พบไฟล์ PDF — ข้ามการโหลดอัตโนมัติ")
        return
    success = rag.load_from_file(pdf_path)
    if not success:
        print("❌ อัปโหลด PDF ไปยัง ChatPDF ไม่สำเร็จ")

try:
    init_db()
except Exception as _e:
    print(f"⚠️  init_db failed (will retry on first request): {_e}")

try:
    auto_load_pdf()
except Exception as _e:
    print(f"⚠️  auto_load_pdf failed: {_e}")

# --- Models ---
class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None   # UUID สร้างจาก frontend

class AskResponse(BaseModel):
    id: int
    question: str
    answer: str
    source_chunk: Optional[str]
    confidence: Optional[float]
    response_time_ms: int
    warning: Optional[str] = None

class FeedbackRequest(BaseModel):
    qa_id: int
    rating: str

class FeedbackResponse(BaseModel):
    success: bool
    message: str

class HistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    source_chunk: Optional[str]
    confidence: Optional[float]
    response_time_ms: int
    timestamp: str
    feedback: Optional[str]

# --- Endpoints ---
@app.get("/")
def root():
    return {"message": "Volleyball Rules RAG API v2 🏐 (PostgreSQL)"}

@app.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest):
    if not body.question.strip():
        raise HTTPException(400, "คำถามต้องไม่ว่างเปล่า")

    start = time.time()
    result = rag.query(body.question)
    elapsed_ms = int((time.time() - start) * 1000)

    answer = result.get("answer", "ไม่พบคำตอบ")
    source_chunk = result.get("source_chunk")
    confidence = result.get("confidence")
    warning = None
    if confidence is not None and 0.0 < confidence < 0.5:
        warning = "⚠️ AI ไม่แน่ใจในคำตอบนี้ กรุณาตรวจสอบกติกาต้นฉบับด้วย"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO qa_log (question, answer, source_chunk, confidence, response_time_ms, session_id) "
        "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (body.question, answer, source_chunk, confidence, elapsed_ms, body.session_id)
    )
    qa_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return AskResponse(id=qa_id, question=body.question, answer=answer,
                       source_chunk=source_chunk, confidence=confidence,
                       response_time_ms=elapsed_ms, warning=warning)

@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(body: FeedbackRequest):
    if body.rating not in ("like", "dislike"):
        raise HTTPException(400, "rating ต้องเป็น like หรือ dislike")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM qa_log WHERE id = %s", (body.qa_id,))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(404, "ไม่พบ qa_id นี้")
    cur.execute("INSERT INTO feedback (qa_id, rating) VALUES (%s,%s)", (body.qa_id, body.rating))
    conn.commit()
    cur.close()
    conn.close()
    return FeedbackResponse(success=True, message=f"บันทึก {body.rating} สำเร็จ!")

@app.get("/history")
def get_history(limit: int = 100):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT q.id, q.question, q.answer, q.source_chunk,
               q.confidence, q.response_time_ms,
               to_char(q.timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
               f.rating AS feedback
        FROM qa_log q
        LEFT JOIN feedback f ON f.qa_id = q.id
        ORDER BY q.timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"data": [dict(r) for r in rows], "total": len(rows)}

@app.post("/upload-rules")
async def upload_rules(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "รองรับเฉพาะ .pdf เท่านั้น")
    contents = await file.read()
    success = rag.load_from_bytes(contents, file.filename)
    if not success:
        raise HTTPException(422, "ไม่สามารถอัปโหลด PDF ไปยัง ChatPDF ได้")
    return {"success": True, "filename": file.filename, "source_id": rag._source_id}

@app.get("/document-status")
def document_status():
    count = rag.get_document_count()
    return {"has_documents": count > 0, "chunk_count": count}

@app.get("/pdf")
def get_pdf():
    """ส่งไฟล์ volleyball_rules.pdf ให้ frontend แสดงใน modal"""
    pdf_path = os.path.join(_BASE_DIR, "volleyball_rules.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "ไม่พบไฟล์ volleyball_rules.pdf")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=volleyball_rules.pdf"},
    )

@app.post("/reindex")
def reindex_documents():
    """Re-upload volleyball_rules.pdf ไปยัง ChatPDF (ได้ sourceId ใหม่)"""
    pdf_path = os.path.join(_BASE_DIR, "volleyball_rules.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "ไม่พบไฟล์ volleyball_rules.pdf")
    success = rag.load_from_file(pdf_path)
    if not success:
        raise HTTPException(422, "ไม่สามารถอัปโหลด PDF ไปยัง ChatPDF ได้")
    return {"success": True, "source_id": rag._source_id}

@app.get("/sessions")
def get_sessions(limit: int = 60):
    """
    คืนรายการ sessions จัดกลุ่มจาก session_id
    - ข้อความที่มี session_id → รวมเป็น 1 session
    - ข้อความเก่าที่ไม่มี session_id → แต่ละแถวเป็น session ตัวเอง (solo_<id>)
    - sessions ที่ถูกซ่อน (hidden_sessions) จะไม่แสดง
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COALESCE(session_id, 'solo_' || id::text)   AS session_id,
            MIN(question)                                 AS title,
            to_char(MIN(timestamp), 'YYYY-MM-DD HH24:MI:SS') AS created_at,
            to_char(MAX(timestamp), 'YYYY-MM-DD HH24:MI:SS') AS last_message_at,
            COUNT(*)                                      AS message_count
        FROM qa_log
        WHERE COALESCE(session_id, 'solo_' || id::text) NOT IN (
            SELECT session_id FROM hidden_sessions
        )
        GROUP BY COALESCE(session_id, 'solo_' || id::text)
        ORDER BY MAX(timestamp) DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"sessions": [dict(r) for r in rows]}

@app.get("/sessions/{session_id}")
def get_session_messages(session_id: str):
    """คืนข้อความทั้งหมดใน session นั้น"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if session_id.startswith("solo_"):
        qa_id = int(session_id.replace("solo_", ""))
        cur.execute("""
            SELECT q.id, q.question, q.answer, q.source_chunk,
                   q.confidence, q.response_time_ms,
                   to_char(q.timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
                   f.rating AS feedback
            FROM qa_log q
            LEFT JOIN feedback f ON f.qa_id = q.id
            WHERE q.id = %s
            ORDER BY q.timestamp ASC
        """, (qa_id,))
    else:
        cur.execute("""
            SELECT q.id, q.question, q.answer, q.source_chunk,
                   q.confidence, q.response_time_ms,
                   to_char(q.timestamp, 'YYYY-MM-DD HH24:MI:SS') AS timestamp,
                   f.rating AS feedback
            FROM qa_log q
            LEFT JOIN feedback f ON f.qa_id = q.id
            WHERE q.session_id = %s
            ORDER BY q.timestamp ASC
        """, (session_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"session_id": session_id, "messages": [dict(r) for r in rows]}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """ซ่อน session จาก sidebar (ไม่ลบข้อมูลจาก DB)"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO hidden_sessions (session_id) VALUES (%s) ON CONFLICT DO NOTHING",
        (session_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True, "message": f"ซ่อน session '{session_id}' แล้ว"}

@app.get("/stats")
def get_stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM qa_log"); total_q = cur.fetchone()[0]
    cur.execute("SELECT AVG(response_time_ms) FROM qa_log"); avg_rt = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM feedback WHERE rating='like'"); likes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM feedback WHERE rating='dislike'"); dislikes = cur.fetchone()[0]
    cur.execute("SELECT AVG(confidence) FROM qa_log WHERE confidence IS NOT NULL"); avg_conf = cur.fetchone()[0] or 0
    cur.close(); conn.close()
    return {
        "total_questions": total_q,
        "avg_response_time_ms": round(float(avg_rt), 1),
        "total_likes": likes,
        "total_dislikes": dislikes,
        "avg_confidence": round(float(avg_conf), 3),
        "satisfaction_rate": round(likes / max(likes + dislikes, 1) * 100, 1)
    }
