# VolleyRAG — Volleyball Rules Chatbot

ระบบ Chatbot ถาม-ตอบกติกาวอลเลย์บอล โดยใช้ RAG (Retrieval-Augmented Generation) + ChatPDF API  
**Backend:** Python / FastAPI · **Frontend:** Angular 17 · **Database:** PostgreSQL

---

## 🗂️ โครงสร้างโปรเจกต์

```
miniRag/
├── backend/          # FastAPI + RAG pipeline
│   ├── main.py
│   ├── rag_pipeline.py
│   ├── chatpdf_pipeline.py
│   ├── requirements.txt
│   ├── .env.example
│   └── volleyball_rules.pdf   ← ไฟล์ PDF กติกา (ต้องมี)
└── frontend/         # Angular 17 web app
    ├── src/
    ├── package.json
    └── proxy.conf.json
```

---

## ✅ Prerequisites

| เครื่องมือ | Version | ดาวน์โหลด |
|---|---|---|
| Python | 3.10+ | https://www.python.org/downloads/ |
| Node.js | 18+ | https://nodejs.org/ |
| Angular CLI | 17 | `npm install -g @angular/cli@17` |
| PostgreSQL | 14+ | https://www.postgresql.org/download/windows/ |

---

## 🔑 API Keys ที่ต้องมี

1. **GROQ API Key** — ฟรี ที่ https://console.groq.com/keys
2. **ChatPDF API Key** — ที่ https://www.chatpdf.com/developers

---

## 🚀 Setup Step-by-Step

### Step 1 — ติดตั้ง PostgreSQL

1. ดาวน์โหลดและติดตั้ง PostgreSQL จาก https://www.postgresql.org/download/windows/
2. ระหว่างติดตั้ง ตั้ง password ให้ user `postgres` (จำไว้ใช้ใน `.env`)
3. เปิด **pgAdmin** หรือ **psql** แล้วสร้าง database:

```sql
CREATE DATABASE volleyball_rag;
```

---

### Step 2 — Setup Backend

```bash
# 1. เข้าไปที่โฟลเดอร์ backend
cd miniRag/backend

# 2. (แนะนำ) สร้าง virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux

# 3. ติดตั้ง dependencies
pip install -r requirements.txt

# 4. สร้างไฟล์ .env จาก template
copy .env.example .env
```

แก้ไขไฟล์ `.env` ให้ครบ:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
CHATPDF_API_KEY=sec_xxxxxxxxxxxxxxxxxxxx
CHATPDF_SOURCE_ID=          # เว้นไว้ก่อน ระบบจะใส่ให้อัตโนมัติ

DB_HOST=localhost
DB_PORT=5432
DB_NAME=volleyball_rag
DB_USER=postgres
DB_PASSWORD=รหัสผ่านที่ตั้งตอนติดตั้ง PostgreSQL
```

```bash
# 5. ตรวจสอบว่ามีไฟล์ PDF อยู่ที่ backend/volleyball_rules.pdf
#    ถ้ายังไม่มี ให้วางไฟล์ PDF กติกาวอลเลย์บอลไว้ที่นี่

# 6. รัน backend
uvicorn main:app --reload --port 8000
```

Backend จะรันที่ http://localhost:8000  
API docs: http://localhost:8000/docs

---

### Step 3 — Setup Frontend

```bash
# 1. เข้าไปที่โฟลเดอร์ frontend
cd miniRag/frontend

# 2. ติดตั้ง dependencies
npm install

# 3. รัน development server
npm start
```

เปิดเบราว์เซอร์ไปที่ **http://localhost:4200**

---

## 🌐 Ports ที่ใช้

| Service | URL |
|---|---|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

---

## ❓ Troubleshooting

**`ModuleNotFoundError`** — ลืม activate virtual environment หรือ `pip install -r requirements.txt` ยังไม่เสร็จ

**`psycopg2` connection error** — ตรวจสอบว่า PostgreSQL รันอยู่ และ `DB_PASSWORD` ใน `.env` ถูกต้อง

**`CORS error` บน frontend** — ตรวจสอบว่า Backend รันที่ port 8000 และ `proxy.conf.json` ถูกต้อง

**ChatPDF ไม่ตอบ** — ตรวจสอบ `CHATPDF_API_KEY` และอินเทอร์เน็ต (`CHATPDF_SOURCE_ID` จะถูกสร้างอัตโนมัติครั้งแรก)
