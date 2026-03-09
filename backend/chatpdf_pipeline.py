import os
import re
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

CHATPDF_API_BASE = "https://api.chatpdf.com/v1"

# ใช้ model เล็กเร็วสำหรับ filter เท่านั้น (ประหยัด quota)
FILTER_LLM_MODEL = "llama-3.1-8b-instant"


class ChatPDFPipeline:
    """
    Pipeline ที่ใช้ ChatPDF API แทน ChromaDB + Groq สำหรับการตอบคำถาม

    Flow:
      1. ตรวจสอบว่าคำถามเกี่ยวกับวอลเลย์บอลหรือไม่  (Groq fast model)
      2. ถ้าใช่  → ส่งคำถามไปยัง ChatPDF API → คืนคำตอบ
      3. ถ้าไม่  → ปฏิเสธทันที (ไม่เสีย ChatPDF quota)
    """

    def __init__(self):
        # ── ChatPDF credentials ───────────────────────────────────────────────
        self._api_key = os.getenv("CHATPDF_API_KEY", "").strip()
        if not self._api_key:
            raise RuntimeError("CHATPDF_API_KEY is not set in .env")

        self._source_id = os.getenv("CHATPDF_SOURCE_ID", "").strip()
        self._chatpdf_headers = {"x-api-key": self._api_key}

        # ── Groq LLM (fast model สำหรับ pre-filter เท่านั้น) ─────────────────
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is not set in .env")
        self._llm = ChatGroq(
            api_key=groq_key,
            model_name=FILTER_LLM_MODEL,
            temperature=0.0,
        )

        if self._source_id:
            print(f"✅ ChatPDF pipeline ready — sourceId: {self._source_id}")
        else:
            print("⚠️  ChatPDF sourceId ยังไม่มี — กรุณาอัปโหลด PDF")

    # ── Document management ───────────────────────────────────────────────────

    def get_document_count(self) -> int:
        """Return 1 ถ้ามี source_id แล้ว, 0 ถ้ายังไม่ได้อัปโหลด"""
        return 1 if self._source_id else 0

    def load_from_file(self, pdf_path: str) -> bool:
        """
        อัปโหลดไฟล์ PDF จาก local path ไปยัง ChatPDF API
        เมื่อสำเร็จจะบันทึก sourceId ลงใน .env อัตโนมัติ
        """
        print(f"📤 กำลังอัปโหลด {pdf_path} ไปยัง ChatPDF ...")
        try:
            with open(pdf_path, "rb") as f:
                files = [("file", (os.path.basename(pdf_path), f, "application/pdf"))]
                resp = requests.post(
                    f"{CHATPDF_API_BASE}/sources/add-file",
                    headers=self._chatpdf_headers,
                    files=files,
                    timeout=120,
                )
            if resp.status_code == 200:
                self._source_id = resp.json().get("sourceId", "")
                self._persist_source_id()
                print(f"✅ อัปโหลดสำเร็จ — sourceId: {self._source_id}")
                return True
            else:
                print(f"❌ ChatPDF upload failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as exc:
            print(f"❌ ChatPDF upload error: {exc}")
            return False

    def load_from_bytes(self, content: bytes, filename: str) -> bool:
        """
        อัปโหลดไฟล์ PDF จาก bytes (ใช้กับ /upload-rules endpoint)
        """
        print(f"📤 กำลังอัปโหลด {filename} ไปยัง ChatPDF ...")
        try:
            files = [("file", (filename, content, "application/pdf"))]
            resp = requests.post(
                f"{CHATPDF_API_BASE}/sources/add-file",
                headers=self._chatpdf_headers,
                files=files,
                timeout=120,
            )
            if resp.status_code == 200:
                self._source_id = resp.json().get("sourceId", "")
                self._persist_source_id()
                print(f"✅ อัปโหลดสำเร็จ — sourceId: {self._source_id}")
                return True
            else:
                print(f"❌ ChatPDF upload failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as exc:
            print(f"❌ ChatPDF upload error: {exc}")
            return False

    def load_document(self, text: str, source_name: str = "document") -> int:
        """Stub สำหรับ compatibility — ChatPDF ต้องการไฟล์จริง ไม่ใช่ text"""
        print("⚠️  ChatPDFPipeline ไม่รองรับ load_document(text) — ใช้ load_from_file() แทน")
        return 0

    def _persist_source_id(self):
        """บันทึก CHATPDF_SOURCE_ID ลงใน .env เพื่อให้ใช้ได้ต่อหลัง restart"""
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = []
        found = False
        for line in lines:
            if line.startswith("CHATPDF_SOURCE_ID="):
                new_lines.append(f"CHATPDF_SOURCE_ID={self._source_id}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"CHATPDF_SOURCE_ID={self._source_id}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    # ── Confidence scorer ─────────────────────────────────────────────────────

    def _score_confidence(self, question: str, answer: str) -> float:
        """
        ใช้ Groq ประเมินคุณภาพของคำตอบที่ได้รับจาก ChatPDF
        คืนค่าระหว่าง 0.0 (ไม่มั่นใจเลย) ถึง 1.0 (มั่นใจมาก)

        เกณฑ์:
          1.0  คำตอบตรงประเด็น ครบถ้วน อ้างอิงกฎชัดเจน
          0.75 คำตอบตรงประเด็น แต่ขาดรายละเอียดบางส่วน
          0.50 คำตอบเกี่ยวข้องบางส่วน หรือคลุมเครือ
          0.25 คำตอบไม่ตรงประเด็นมาก
          0.0  บอกว่าไม่พบข้อมูล / ไม่รู้ / นอกขอบเขต
        """
        # ตรวจคร่าว ๆ ก่อนเรียก LLM — ประหยัด API call
        low_confidence_phrases = [
            "ไม่พบ", "ไม่มีข้อมูล", "ไม่ทราบ", "ไม่แน่ใจ",
            "i don't know", "not found", "no information",
            "cannot find", "does not contain",
        ]
        answer_lower = answer.lower()
        if any(p in answer_lower for p in low_confidence_phrases):
            return 0.15

        try:
            prompt = (
                "ประเมินความมั่นใจของคำตอบนี้ในระดับ 0.0 ถึง 1.0\n\n"
                f"คำถาม: {question}\n\n"
                f"คำตอบ: {answer[:600]}\n\n"
                "เกณฑ์:\n"
                "1.0 = ตรงประเด็น ครบถ้วน มีอ้างอิงกฎชัดเจน\n"
                "0.75 = ตรงประเด็น แต่ขาดรายละเอียด\n"
                "0.50 = เกี่ยวข้องบางส่วน หรือคลุมเครือ\n"
                "0.25 = ไม่ตรงประเด็นมาก\n"
                "0.0 = ไม่พบข้อมูล / ไม่รู้\n\n"
                "ตอบเป็นตัวเลขทศนิยมเพียงอย่างเดียว เช่น 0.85 ห้ามตอบอื่น"
            )
            resp = self._llm.invoke([HumanMessage(content=prompt)])
            text = resp.content.strip()
            match = re.search(r"[01]\.?\d*", text)
            if match:
                score = float(match.group())
                return round(min(max(score, 0.0), 1.0), 3)
        except Exception as exc:
            print(f"⚠️  Confidence scoring failed: {exc}")
        return 0.5   # default กลาง ๆ ถ้าเกิด error

    # ── Pre-filter: ตรวจสอบว่าคำถามเกี่ยวกับวอลเลย์บอลหรือไม่ ────────────────

    def _is_volleyball_related(self, question: str) -> bool:
        """
        ใช้ Groq (model เล็กเร็ว) จำแนกว่าคำถามเกี่ยวกับวอลเลย์บอลหรือไม่
        คืน True ถ้าเกี่ยว, False ถ้าไม่เกี่ยว
        ถ้า LLM เกิด error → คืน True (fail-open เพื่อไม่บล็อกคำถามที่ถูกต้อง)
        """
        try:
            prompt = (
                "คุณต้องตัดสินว่าคำถามต่อไปนี้เกี่ยวข้องกับ"
                "วอลเลย์บอล กติกาวอลเลย์บอล หรือกีฬาวอลเลย์บอลหรือไม่\n\n"
                f"คำถาม: {question}\n\n"
                "ตอบเพียง: ใช่  หรือ  ไม่ใช่  เท่านั้น ห้ามตอบอื่น"
            )
            resp = self._llm.invoke([HumanMessage(content=prompt)])
            answer = resp.content.strip()
            return "ใช่" in answer
        except Exception as exc:
            print(f"⚠️  Filter LLM error: {exc} — allowing question through")
            return True   # fail-open

    # ── Main query ────────────────────────────────────────────────────────────

    def query(self, question: str, n_results: int = 5) -> dict:
        """
        1. ตรวจว่าคำถามเกี่ยวกับวอลเลย์บอลไหม
        2. ถ้าใช่ → ส่งไปยัง ChatPDF API แล้วคืนคำตอบ
        3. ถ้าไม่ → คืนข้อความปฏิเสธทันที
        """
        # ── ยังไม่ได้ตั้งค่า source_id ──────────────────────────────────────
        if not self._source_id:
            return {
                "answer": "❌ ยังไม่ได้เชื่อมต่อกับเอกสาร กรุณาอัปโหลด PDF ก่อน",
                "source_chunk": None,
                "confidence": None,
            }

        # ── Step 1: Pre-filter ─────────────────────────────────────────────
        if not self._is_volleyball_related(question):
            return {
                "answer": (
                    "❌ คำถามนี้ไม่เกี่ยวข้องกับกติกาวอลเลย์บอล\n\n"
                    "ระบบนี้ตอบได้เฉพาะคำถามที่เกี่ยวกับ **กติกาและกฎการแข่งขันวอลเลย์บอล** เท่านั้น\n"
                    "กรุณาลองถามใหม่ เช่น:\n"
                    "• ลิเบโรคืออะไร?\n"
                    "• เซตหนึ่งต้องได้กี่แต้ม?\n"
                    "• ผู้เล่นสัมผัสลูกได้กี่ครั้ง?"
                ),
                "source_chunk": None,
                "confidence": None,
            }

        # ── Step 2: ส่งคำถามไปยัง ChatPDF API ────────────────────────────
        try:
            payload = {
                "sourceId": self._source_id,
                "messages": [{"role": "user", "content": question}],
            }
            resp = requests.post(
                f"{CHATPDF_API_BASE}/chats/message",
                headers={**self._chatpdf_headers, "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )

            if resp.status_code == 200:
                answer = resp.json().get("content", "ไม่ได้รับคำตอบจาก ChatPDF")
                # ── Step 3: ให้ Groq ประเมิน confidence ──────────────────
                confidence = self._score_confidence(question, answer)
                return {
                    "answer": answer,
                    "source_chunk": None,
                    "confidence": confidence,
                }
            else:
                error_msg = resp.json().get("message", resp.text) if resp.content else resp.text
                return {
                    "answer": f"⚠️ ChatPDF ตอบสนองผิดพลาด (HTTP {resp.status_code}): {error_msg}",
                    "source_chunk": None,
                    "confidence": None,
                }

        except requests.Timeout:
            return {
                "answer": "⚠️ ChatPDF ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง",
                "source_chunk": None,
                "confidence": None,
            }
        except Exception as exc:
            return {
                "answer": f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ ChatPDF: {exc}",
                "source_chunk": None,
                "confidence": None,
            }
