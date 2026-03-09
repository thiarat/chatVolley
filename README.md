# VolleyRAG v2 — Setup Guide

## สิ่งที่เปลี่ยนใน v2
- 🗃️ Database: SQLite → **PostgreSQL**
- 🎨 Frontend: redesign ใหม่ ธีมขาว-น้ำเงิน แบบ ChatGPT
- 💬 Chat interface พร้อม sidebar ประวัติ
- 📊 Dashboard แยกหน้าต่างหาก

---

## 1. ติดตั้ง PostgreSQL (Windows)

1. ดาวน์โหลดจาก https://www.postgresql.org/download/windows/
2. ติดตั้ง → ตั้ง password สำหรับ user `postgres`
3. เปิด pgAdmin หรือ psql แล้วสร้าง database:

```sql
CREATE DATABASE volleyball_rag;
```

---

## 2. Setup Backend

```bash
cd C:\Users\thair\Documents\AI\miniRag\backend

# สร้าง .env จาก example
copy .env.example .env
# แก้ไข .env ใส่ GROQ_API_KEY และ DB_PASSWORD

# ติดตั้ง dependencies (รวม psycopg2-binary ใหม่)
pip install -r requirements.txt

# วาง PDF กติกาไว้ที่ backend/volleyball_rules.pdf

# รัน
uvicorn main:app --reload --port 8000
```

---

## 3. Setup Frontend

```bash
cd C:\Users\thair\Documents\AI\miniRag\frontend

# Extract ไฟล์ทับ src/ เดิม ไม่ต้อง npm install ใหม่

ng serve
```

เปิด http://localhost:4200

---

## .env ที่ต้องแก้

```
GROQ_API_KEY=gsk_xxxxx
DB_HOST=localhost
DB_PORT=5432
DB_NAME=volleyball_rag
DB_USER=postgres
DB_PASSWORD=ใส่_password_ที่_ตั้งตอนติดตั้ง
```
