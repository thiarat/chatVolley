import os
import re
import requests
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv, set_key

load_dotenv()

CHATPDF_API_BASE = "https://api.chatpdf.com/v1"
GROQ_MODEL       = "llama-3.1-8b-instant"   # ใช้สำหรับ confidence scoring เท่านั้น


class ChatPDFPipeline:
    """
    Pipeline ถาม-ตอบกติกาวอลเลย์บอล

    Flow:
      1. ChatPDF API        → ส่งคำถามตรง ๆ ไปยัง PDF แล้วรับคำตอบกลับมา
      2. Score confidence   → Groq ประเมินคุณภาพคำตอบ (0.0 – 1.0)
                              ถ้าคำตอบบ่งบอกว่า "ไม่พบ / ไม่เกี่ยว" → off_topic = True
                              → แสดงข้อความปฏิเสธแทนคำตอบเดิม
    """

    def __init__(self):
        self._api_key   = os.getenv("CHATPDF_API_KEY", "").strip()
        self._source_id = os.getenv("CHATPDF_SOURCE_ID", "").strip()
        if not self._api_key:
            raise RuntimeError("CHATPDF_API_KEY is not set in .env")

        self._chatpdf_headers = {"x-api-key": self._api_key}

        # ── Groq LLM (confidence scoring) ────────────────────────────────────
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is not set in .env")
        self._llm = ChatGroq(
            api_key=groq_key,
            model_name=GROQ_MODEL,
            temperature=0,
        )

    # ── Document helpers ──────────────────────────────────────────────────────

    def load_from_file(self, pdf_path: str) -> bool:
        """อัปโหลด PDF จาก local path ไปยัง ChatPDF"""
        try:
            with open(pdf_path, "rb") as f:
                resp = requests.post(
                    f"{CHATPDF_API_BASE}/sources/add-file",
                    headers=self._chatpdf_headers,
                    files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                    timeout=60,
                )
            resp.raise_for_status()
            self._source_id = resp.json()["sourceId"]
            self._persist_source_id()
            print(f"✅ ChatPDF source loaded: {self._source_id}")
            return True
        except Exception as e:
            print(f"❌ ChatPDF upload failed: {e}")
            return False

    def load_from_bytes(self, content: bytes, filename: str) -> bool:
        """อัปโหลด PDF จาก bytes ไปยัง ChatPDF"""
        try:
            resp = requests.post(
                f"{CHATPDF_API_BASE}/sources/add-file",
                headers=self._chatpdf_headers,
                files={"file": (filename, content, "application/pdf")},
                timeout=60,
            )
            resp.raise_for_status()
            self._source_id = resp.json()["sourceId"]
            self._persist_source_id()
            print(f"✅ ChatPDF source loaded: {self._source_id}")
            return True
        except Exception as e:
            print(f"❌ ChatPDF upload failed: {e}")
            return False

    def _persist_source_id(self):
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        try:
            set_key(env_path, "CHATPDF_SOURCE_ID", self._source_id)
        except Exception as e:
            print(f"⚠️  Could not persist source_id: {e}")

    def get_document_count(self) -> int:
        return 1 if self._source_id else 0

    def load_document(self, text: str):
        """stub – ใช้ load_from_file() หรือ load_from_bytes() แทน"""
        print("⚠️  load_document() ไม่รองรับ ใช้ load_from_file() แทน")

    # ── Confidence scoring ────────────────────────────────────────────────────

    # คำที่ ChatPDF มักใช้เมื่อไม่พบข้อมูล หรือคำถามไม่เกี่ยว
    _OFF_TOPIC_PHRASES = [
        # ภาษาไทย
        "ขออภัย", "ขอโทษ",
        "ไม่พบข้อมูล", "ไม่มีข้อมูล", "ไม่ทราบ", "ไม่แน่ใจ",
        "ไม่เกี่ยวข้อง", "ไม่อยู่ในเอกสาร", "ไม่สามารถตอบ",
        "นอกเหนือจากขอบเขต", "อยู่นอกเหนือ", "ไม่ได้กล่าวถึง",
        "ไม่พบในเอกสาร", "ไม่มีในเอกสาร", "ไม่ตรงกับ",
        "ไม่เกี่ยวกับวอลเลย์", "ไม่เกี่ยวกับกติกา",
        # English
        "i don't know", "i do not know",
        "not found", "no information",
        "cannot find", "does not contain",
        "not related", "not available",
        "outside the scope", "not mentioned",
        "i'm sorry", "i am sorry", "apologies",
        "unable to find", "no relevant",
        "not in the document",
    ]

    def _score_confidence(self, question: str, answer: str) -> dict:
        """
        ประเมินคุณภาพของคำตอบจาก ChatPDF

        คืน dict:
          {
            "confidence": float (0.0 – 1.0),
            "off_topic":  bool   # True = ไม่เกี่ยว หรือไม่พบข้อมูล
          }

        เกณฑ์:
          1.0  ตรงประเด็น ครบถ้วน มีอ้างอิงกฎชัดเจน
          0.75 ตรงประเด็น แต่ขาดรายละเอียดบางส่วน
          0.50 เกี่ยวข้องบางส่วน หรือคลุมเครือ
          0.25 ไม่ตรงประเด็นมาก
          0.0  ไม่พบข้อมูล / ไม่รู้ / ไม่เกี่ยวกับวอลเลย์บอล
        """
        answer_lower = answer.lower()

        # ── Fast-path: ตรวจคำบ่งบอก off-topic ก่อนเรียก LLM ──────────────────
        if any(phrase in answer_lower for phrase in self._OFF_TOPIC_PHRASES):
            return {"confidence": 0.0, "off_topic": True}

        # ── Groq evaluation ───────────────────────────────────────────────────
        try:
            prompt = (
                "ประเมินความมั่นใจของคำตอบนี้ในระดับ 0.0 ถึง 1.0\n\n"
                f"คำถาม: {question}\n\n"
                f"คำตอบ: {answer[:600]}\n\n"
                "เกณฑ์:\n"
                "1.0  = ตรงประเด็น ครบถ้วน มีอ้างอิงกฎชัดเจน\n"
                "0.75 = ตรงประเด็น แต่ขาดรายละเอียด\n"
                "0.50 = เกี่ยวข้องบางส่วน หรือคลุมเครือ\n"
                "0.25 = ไม่ตรงประเด็นมาก\n"
                "0.0  = ไม่พบข้อมูล / ไม่รู้ / ไม่เกี่ยวกับวอลเลย์บอล\n\n"
                "ตอบเป็นตัวเลขทศนิยมเพียงอย่างเดียว เช่น 0.85  ห้ามตอบอื่น"
            )
            resp  = self._llm.invoke([HumanMessage(content=prompt)])
            text  = resp.content.strip()
            match = re.search(r"[01]\.?\d*", text)
            if match:
                score     = round(min(max(float(match.group()), 0.0), 1.0), 3)
                off_topic = (score == 0.0)   # LLM ให้ 0.0 → ถือว่า off_topic
                return {"confidence": score, "off_topic": off_topic}
        except Exception as exc:
            print(f"⚠️  Confidence scoring failed: {exc}")

        return {"confidence": 0.5, "off_topic": False}   # default กลาง ๆ

    # ── Main query ────────────────────────────────────────────────────────────

    def query(self, question: str) -> dict:
        """
        ขั้นตอน:
          1. ส่งคำถามไปยัง ChatPDF API → รับคำตอบ
          2. _score_confidence() ประเมินคำตอบ
             - off_topic = True → แทนที่ด้วยข้อความปฏิเสธ + confidence 0.0
             - off_topic = False → คืนคำตอบพร้อม confidence จริง
        """
        if not self._source_id:
            return {
                "answer":       "⚠️ ยังไม่ได้โหลดเอกสาร กรุณาอัปโหลด PDF กติกาวอลเลย์บอลก่อน",
                "source_chunk": None,
                "confidence":   0.0,
            }

        # ── Step 1: ChatPDF API ───────────────────────────────────────────────
        try:
            resp = requests.post(
                f"{CHATPDF_API_BASE}/chats/message",
                headers={**self._chatpdf_headers, "Content-Type": "application/json"},
                json={
                    "sourceId": self._source_id,
                    "messages": [{"role": "user", "content": question}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw_answer = resp.json().get("content", "ไม่ได้รับคำตอบจาก ChatPDF")

            # ── Step 2: Score confidence ──────────────────────────────────────
            result    = self._score_confidence(question, raw_answer)
            confidence = result["confidence"]
            off_topic  = result["off_topic"]

            if off_topic:
                return {
                    "answer": (
                        f"ขออภัย ไม่พบข้อมูลที่เกี่ยวข้องกับคำถาม \"{question}\" "
                        f"ในเอกสารกติกาวอลเลย์บอล "
                        f"กรุณาถามคำถามเกี่ยวกับกติกาวอลเลย์บอลเท่านั้น"
                    ),
                    "source_chunk": None,
                    "confidence":   0.0,
                }

            return {
                "answer":       raw_answer,
                "source_chunk": None,
                "confidence":   confidence,
            }

        except requests.Timeout:
            return {
                "answer":       "⚠️ ChatPDF ไม่ตอบสนองภายในเวลาที่กำหนด กรุณาลองใหม่",
                "source_chunk": None,
                "confidence":   0.0,
            }
        except Exception as e:
            print(f"❌ ChatPDF query error: {e}")
            return {
                "answer":       "เกิดข้อผิดพลาดในการเชื่อมต่อ ChatPDF กรุณาลองใหม่อีกครั้ง",
                "source_chunk": None,
                "confidence":   0.0,
            }
