# Smart Legal Platform

منصة محاماة ذكية ومنظمة تجمع بين:

- **البحث والتحليل القانوني الذكي** (استعلام طبيعي + ربط السوابق + تنبؤ نتائج).
- **أتمتة العقود والمستندات** (استخراج البنود + كشف المخاطر + توليد قوالب).
- **إدارة القضايا** (مهام، مواعيد، تتبع وقت، وفواتير).
- **التواصل الآمن والتوقيع الإلكتروني**.
- **لوحات وتحليلات تنبؤية**.
- **أمان وامتثال** (JWT، صلاحيات RBAC، تشفير، نسخ احتياطي مشفّر).

## Quick Start

### 1) تثبيت المتطلبات

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2) تشغيل الخادم

```bash
uvicorn smart_legal_platform.main:app --reload
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## بيانات دخول تجريبية

| Username | Password     | Role      |
|----------|--------------|-----------|
| admin    | Admin@12345  | admin     |
| nora     | Lawyer@123   | lawyer    |
| omar     | Lawyer@123   | lawyer    |
| layla    | Para@123     | paralegal |
| client1  | Client@123   | client    |

## أهم نقاط النهاية

- `POST /api/auth/token` : الحصول على JWT
- `POST /api/search/query` : بحث قانوني ذكي
- `GET /api/search/precedents/{case_id}/links` : الروابط الخفية بين القضايا
- `GET /api/search/outcome-prediction/{case_id}` : توقع نتيجة القضية
- `POST /api/contracts/analyze` : تحليل العقد واستخراج المخاطر
- `POST /api/contracts/generate-document` : توليد مستند من قالب
- `POST /api/cases` : إنشاء قضية
- `POST /api/cases/{case_id}/time-entries` + `POST /api/cases/{case_id}/invoices`
- `POST /api/communications/messages` : رسائل مشفرة
- `POST /api/communications/esignatures` : توقيع إلكتروني
- `GET /api/analytics/dashboard` : لوحة تحليلات
- `POST /api/security/backup` : نسخ احتياطي مشفر (للمدير)

## ملاحظات تصميمية

- النسخة الحالية **MVP قابلة للتوسعة** وتعتمد تخزينًا داخل الذاكرة (In-Memory).
- الخدمات معزولة داخل `smart_legal_platform/services` لسهولة استبدالها لاحقًا بمحرّكات ذكاء اصطناعي وقواعد بيانات إنتاجية.
- مجلد `cloud_backup/` مخصص لحفظ النسخ الاحتياطية المشفّرة.