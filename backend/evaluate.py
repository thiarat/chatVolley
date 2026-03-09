#!/usr/bin/env python3
"""
evaluate.py – Offline evaluation script for the Volleyball RAG chatbot.

Usage:
    cd backend
    python evaluate.py                          # default: http://localhost:8000
    python evaluate.py --base-url http://localhost:8000
    python evaluate.py --output-dir ./results

The script runs a curated set of volleyball-rules test questions,
checks whether key answer keywords are present, and prints a summary
table.  Results are also saved to a timestamped CSV file.
"""

import argparse
import csv
import os
import time
from datetime import datetime
from pathlib import Path

import requests

# ─── Test suite ───────────────────────────────────────────────────────────────
# Each case has:
#   id       – unique test identifier
#   question – question in Thai (mirrors real user queries)
#   keywords – ANY ONE keyword must appear in the answer to pass
#   note     – human-readable description of what is being tested
TEST_CASES = [
    {
        "id": "TC01",
        "question": "ทีมวอลเลย์บอลสนามใหญ่มีผู้เล่นกี่คน?",
        "keywords": ["6", "หก"],
        "note": "จำนวนผู้เล่นในสนาม",
    },
    {
        "id": "TC02",
        "question": "เซตปกติต้องได้กี่แต้มจึงจะชนะ?",
        "keywords": ["25", "ยี่สิบห้า"],
        "note": "แต้มชนะต่อเซตปกติ",
    },
    {
        "id": "TC03",
        "question": "เซตไทเบรก (เซต 5) ต้องได้กี่แต้มจึงจะชนะ?",
        "keywords": ["15", "สิบห้า"],
        "note": "แต้มชนะไทเบรก",
    },
    {
        "id": "TC04",
        "question": "ลิเบโรคืออะไร และมีข้อจำกัดอะไรบ้าง?",
        "keywords": ["ลิเบโร", "รับ", "ตำแหน่ง"],
        "note": "บทบาทและข้อจำกัดของลิเบโร",
    },
    {
        "id": "TC05",
        "question": "การหมุนตำแหน่งผู้เล่นทำอย่างไร?",
        "keywords": ["หมุน", "ตำแหน่ง", "ตามเข็ม", "เสิร์ฟ"],
        "note": "กฎการหมุนตำแหน่ง",
    },
    {
        "id": "TC06",
        "question": "แต่ละทีมสัมผัสลูกบอลได้สูงสุดกี่ครั้งต่อการรับหนึ่งครั้ง?",
        "keywords": ["3", "สาม", "สามครั้ง"],
        "note": "จำนวนการสัมผัสลูกต่อทีม",
    },
    {
        "id": "TC07",
        "question": "ผู้เล่นสามารถแตะตาข่ายระหว่างการเล่นได้หรือไม่?",
        "keywords": ["ตาข่าย", "สัมผัส", "ผิดกติกา", "ห้าม", "ไม่ได้"],
        "note": "กฎเกี่ยวกับการแตะตาข่าย",
    },
    {
        "id": "TC08",
        "question": "ขนาดสนามวอลเลย์บอลมาตรฐานกว้างและยาวเท่าไหร่?",
        "keywords": ["18", "9", "เมตร"],
        "note": "ขนาดสนามแข่งขัน",
    },
    {
        "id": "TC09",
        "question": "ความสูงของตาข่ายสำหรับผู้ชายคือเท่าไหร่?",
        "keywords": ["2.43", "243"],
        "note": "ความสูงตาข่ายชาย",
    },
    {
        "id": "TC10",
        "question": "ความสูงของตาข่ายสำหรับผู้หญิงคือเท่าไหร่?",
        "keywords": ["2.24", "224"],
        "note": "ความสูงตาข่ายหญิง",
    },
    {
        "id": "TC11",
        "question": "ทีมชนะแมตช์เมื่อไหร่?",
        "keywords": ["3", "เซต", "ชนะ", "แมตช์"],
        "note": "เงื่อนไขชนะแมตช์",
    },
    {
        "id": "TC12",
        "question": "การเสิร์ฟผิดกติกาในกรณีใดบ้าง?",
        "keywords": ["เสิร์ฟ", "ผิด", "กติกา", "ผิดกติกา"],
        "note": "ความผิดพลาดในการเสิร์ฟ",
    },
    {
        "id": "TC13",
        "question": "หัวหน้าทีมมีสิทธิ์อะไรบ้างในระหว่างแมตช์?",
        "keywords": ["กัปตัน", "หัวหน้าทีม", "สิทธิ์", "ขอ"],
        "note": "สิทธิ์ของกัปตันทีม",
    },
    {
        "id": "TC14",
        "question": "การหยุดพักในแต่ละเซตมีกี่ครั้งและใช้เวลาเท่าไหร่?",
        "keywords": ["พัก", "30", "วินาที", "ไทม์เอาต์"],
        "note": "กฎการขอหยุดพัก (ไทม์เอาต์)",
    },
    {
        "id": "TC15",
        "question": "ผู้เล่นสำรองเปลี่ยนตัวได้กี่ครั้งต่อเซต?",
        "keywords": ["เปลี่ยน", "สำรอง", "6", "หก", "ครั้ง"],
        "note": "กฎการเปลี่ยนตัวผู้เล่น",
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def keyword_hit(answer: str, keywords: list[str]) -> bool:
    """Return True if ANY keyword is found (case-insensitive) in the answer."""
    lower = answer.lower()
    return any(kw.lower() in lower for kw in keywords)


def confidence_label(conf: float) -> str:
    if conf >= 0.65:
        return "สูง  "
    if conf >= 0.45:
        return "กลาง "
    return "ต่ำ  "


# ─── Main evaluation runner ───────────────────────────────────────────────────
def run_eval(base_url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path  = output_dir / f"eval_results_{timestamp}.csv"

    rows: list[dict] = []
    passed = 0

    print(f"\n{'='*72}")
    print(f"  🏐 Volleyball RAG Evaluation  |  {base_url}")
    print(f"{'='*72}")
    print(f"{'ID':<6} {'ผ่าน':<5} {'Conf':>6} {'ระดับ':<8} {'ms':>6}  คำถาม")
    print(f"{'-'*72}")

    for tc in TEST_CASES:
        start = time.time()
        try:
            r = requests.post(
                f"{base_url}/ask",
                json={"question": tc["question"]},
                timeout=90,
            )
            r.raise_for_status()
            data       = r.json()
            elapsed_ms = int((time.time() - start) * 1000)

            answer     = data.get("answer", "")
            confidence = float(data.get("confidence") or 0.0)
            hit        = keyword_hit(answer, tc["keywords"])
            passed    += int(hit)

            status = "✅" if hit else "❌"
            level  = confidence_label(confidence)
            print(
                f"{tc['id']:<6} {status:<5} {confidence:>5.3f}  {level}  "
                f"{elapsed_ms:>5}ms  {tc['question'][:38]}"
            )

            rows.append(
                {
                    "id":         tc["id"],
                    "question":   tc["question"],
                    "keywords":   "|".join(tc["keywords"]),
                    "pass":       hit,
                    "confidence": round(confidence, 4),
                    "latency_ms": elapsed_ms,
                    "note":       tc["note"],
                    "answer":     answer[:400],
                }
            )

        except Exception as exc:
            elapsed_ms = int((time.time() - start) * 1000)
            print(
                f"{tc['id']:<6} {'ERR':<5} {'N/A':>6}  {'ERROR':<8}  "
                f"{elapsed_ms:>5}ms  {tc['question'][:38]}"
            )
            print(f"       ⚠️  {exc}")
            rows.append(
                {
                    "id":         tc["id"],
                    "question":   tc["question"],
                    "keywords":   "|".join(tc["keywords"]),
                    "pass":       False,
                    "confidence": 0.0,
                    "latency_ms": elapsed_ms,
                    "note":       tc["note"],
                    "answer":     f"ERROR: {exc}",
                }
            )

    # ── Summary ───────────────────────────────────────────────────────────────
    total    = len(TEST_CASES)
    accuracy = passed / total * 100
    avg_conf = sum(r["confidence"] for r in rows) / total
    avg_lat  = sum(r["latency_ms"] for r in rows) / total

    print(f"{'='*72}")
    print(f"  ✅ Accuracy  : {passed}/{total}  ({accuracy:.1f}%)")
    print(f"  🎯 Avg Conf  : {avg_conf:.3f}  ({confidence_label(avg_conf).strip()})")
    print(f"  ⚡ Avg Lat   : {avg_lat:.0f} ms")
    print(f"{'='*72}\n")

    # ── Save CSV ──────────────────────────────────────────────────────────────
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"📊 ผลลัพธ์บันทึกที่: {csv_path}\n")


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate the Volleyball RAG chatbot"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--output-dir",
        default="./results",
        help="Directory for CSV output (default: ./results)",
    )
    args = parser.parse_args()
    run_eval(args.base_url, Path(args.output_dir))
