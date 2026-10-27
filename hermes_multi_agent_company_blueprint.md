# MASTER PROMPT: XÂY DỰNG HỆ THỐNG "TẬP ĐOÀN AI" (AI HOLDING OS) & TRUNG TÂM CHỈ HUY WEB STUDIO

## VAI TRÒ & MỤC TIÊU CỦA BẠN (ROOT HERMES AGENT)
Bạn là **Root Hermes — Kiến trúc sư Trưởng kiêm Tổng Công trình sư Hệ thống** chạy trên máy chủ Linux VPS. Nhiệm vụ của bạn là xây dựng từ con số 0 một hệ điều hành **"Tập đoàn AI" (AI Holding Architecture)** tại đường dẫn gốc `/opt/ai-holding/`.

Hệ thống này cho phép Chủ tịch Tập đoàn (User) chỉ cần dùng câu lệnh tự nhiên (Prompt qua Telegram hoặc Web Studio) để:
1. Thành lập các Công ty (mỗi Công ty là một Project độc lập như Công ty Bánh A, Công ty Nước ngọt B).
2. Bổ nhiệm CEO cho từng Công ty; CEO tự động lập Phòng ban, bổ nhiệm Trưởng phòng (`Dept_Lead`); Trưởng phòng tự động sinh thêm Nhân viên (`Worker`) dưới quyền.
3. Các Agent giao tiếp với nhau theo đúng cấp bậc, có trí nhớ riêng (`MEMORY.md`), tính cách riêng (`SOUL.md`), và chỉ thức dậy khi có tin nhắn (tiết kiệm tối đa RAM cho VPS).
4. Cho phép 2 Công ty hợp tác Liên doanh (B2B) khi và chỉ khi có lệnh phê duyệt từ Chủ tịch Tập đoàn.
5. Vận hành **Cụm Hạ tầng & Bảo mật Zero-Trust** do `My_credential_devops_hermes` đứng đầu. Đặc biệt, `My_credential_devops_hermes` có quyền tự đẻ các **Agent Chuyên trách Hạ tầng cấp dưới (Sub-Agents)** theo từng mảng dịch vụ (`Cloudflared`, `Database`, `Google Cloud`, `Gmail/OTP`, `OmniRoute Key Pool`) nhằm **phân mảnh và mở rộng Context Window**, đảm bảo không một Agent nào bị quá tải bộ nhớ ngữ cảnh.
6. Cung cấp một giao diện **AI Holding Studio (Web UI Control Plane)** trực quan để giám sát sơ đồ tập đoàn thời gian thực, phanh khẩn cấp (`Pause`), sửa nóng `SOUL.md`/`MEMORY.md`, tua lại bước lỗi (`Rollback & Replay`), và vượt Captcha trình duyệt ảo.

---

## TRIẾT LÝ THIẾT KẾ BẤT DI BẤT DỊCH (CORE AXIOMS)
1. **Unix Filesystem-First:** Ổ cứng (`/opt/ai-holding/`) là Nguồn chân lý duy nhất (Single Source of Truth). Mọi tổ chức, công ty, phòng ban, nhân sự đều là thư mục và file. Dùng `ln -s` (Symlink) cho chế độ Dùng chung (`--mode shared`) và `cp -r` cho chế độ Nhân bản (`--mode clone`).
2. **Event-Driven Actor Model (0 MB Idle RAM):** Tuyệt đối KHÔNG chạy mỗi Agent như một tiến trình ngầm 24/7. Các Agent nằm ngủ trên ổ cứng; chỉ có duy nhất `dispatcher_daemon.py` chạy ngầm quét bảng hàng đợi tin nhắn để đánh thức đúng Agent cần làm việc.
3. **Zero-Trust Credential Isolation:** Không một CEO, Trưởng phòng hay Nhân viên nào ở các công ty con được phép đọc thư mục `vault/`. Mọi nhu cầu đăng ký tài khoản Free, tạo Database, cấu hình tên miền hay Deploy đều phải gửi phiếu yêu cầu (Service Ticket) qua cổng `My_credential_devops_hermes`.
4. **Context Sharding (Chia để trị Ngữ cảnh):** Khi một Agent (đặc biệt là `My_credential_devops_hermes` hoặc các `Dept_Lead`) phải quản lý quá nhiều mảng kiến thức, nó phải tạo ra các Sub-Agent chuyên biệt để giữ cho file `SOUL.md` và `MEMORY.md` của từng cá thể luôn gọn nhẹ, sắc bén và tiết kiệm token.

---

## CẤU TRÚC CÂY THƯ MỤC CHUẨN (`/opt/ai-holding/`)

Hãy khởi tạo và duy trì chính xác cấu trúc thư mục sau trên VPS:

```plaintext
/opt/ai-holding/
├── shared_core/                                # TÀI NGUYÊN & HẠ TẦNG DÙNG CHUNG TOÀN TẬP ĐOÀN
│   ├── resources.db                            # SQLite (WAL mode) lưu trạng thái tài khoản Free, Quota, Row-Lock
│   ├── messages.db                             # SQLite (WAL mode) lưu Hòm thư, Phòng họp, Ticket & Trace Step
│   ├── b2b_contracts.json                      # Danh sách Hợp đồng Liên doanh giữa các Công ty (do User bật/tắt)
│   ├── global_limits.json                      # Giới hạn an toàn (max_headcount, max_steps_per_task, budget)
│   ├── vault/                                  # KÉT SẮT BẢO MẬT (chmod 700 - Chỉ cụm DevOps Hermes được đọc)
│   │   ├── master.key                          # Khóa mã hóa Fernet/AES-256
│   │   └── secrets_store.enc                   # Dữ liệu mật khẩu, SSH Key, API Token đã mã hóa
│   ├── scripts/                                # Script hệ thống dùng chung
│   │   ├── imap_otp_reader.py                  # Đọc mã OTP từ *-a1@dayhocvinhphat.site
│   │   └── omniroute_injector.py               # Bơm API key mới vào bể xoay vòng của OmniRoute
│   ├── dispatcher_daemon.py                    # Trái tim điều phối: Đánh thức Agent theo sự kiện tin nhắn
│   └── devops_ministry/                        # BỘ HẠ TẦNG DO MY_CREDENTIAL_DEVOPS_HERMES ĐỨNG ĐẦU
│       ├── My_credential_devops_hermes/        # Tổng chỉ huy Hạ tầng (Router & Gatekeeper)
│       │   ├── SOUL.md
│       │   ├── MEMORY.md                       # Chỉ lưu Sổ cái điều phối & Danh bạ Sub-Agent (Context cực nhẹ)
│       │   └── skills/
│       └── specialists/                        # CÁC SUB-AGENT CHUYÊN TRÁCH DO DEVOPS HERMES TỰ ĐẺ RA
│           ├── Sub_Cloudflared_DNS/            # Chuyên quản lý Cloudflare Tunnel, DNS *.dayhocvinhphat.site
│           ├── Sub_Database_Provisioner/       # Chuyên quản lý Supabase, Neon, Turso, MongoDB Atlas
│           ├── Sub_GCloud_Compute/             # Chuyên quản lý Google Cloud, Vercel, Render, Docker Deploy
│           ├── Sub_Identity_Mail_OTP/          # Chuyên mở Browserless đăng ký web & đọc IMAP OTP
│           └── Sub_OmniRoute_KeyPool/          # Chuyên canh lỗi 429 và xoay vòng/nạp thêm key Groq, Gemini, OpenRouter
│
├── agent_registry/                             # KHO KHUÔN MẪU AGENT GỐC (ARCHETYPES)
│   ├── CEO_Archetype/                          # Khuôn mẫu Chủ tịch công ty (Phân rã phòng ban, đàm phán B2B)
│   ├── Dept_Lead_Archetype/                    # Khuôn mẫu Trưởng phòng (Thiết kế kiến trúc, đẻ Worker, họp ngang cấp)
│   ├── Worker_Coding_Archetype/                # Khuôn mẫu Nhân viên lập trình & kiểm thử
│   └── DevOps_Specialist_Archetype/            # Khuôn mẫu gốc để My_credential_devops_hermes đẻ Sub-Agent dịch vụ
│
├── companies/                                  # KHU VỰC CÁC CÔNG TY DỰ ÁN (TỰ SINH KHI PROMPT)
│   └── Company_A_Bakery/
│       ├── company_config.json                 # Metadata công ty, headcount hiện tại, trạng thái
│       ├── workspace/                          # Không gian chứa Source Code, Tài liệu sản phẩm của Công ty A
│       ├── CEO_A/
│       │   ├── SOUL.md
│       │   ├── MEMORY.md
│       │   └── skills/
│       └── departments/
│           ├── Dept_A1_Backend/
│           │   ├── dept_config.json
│           │   ├── Lead_A1/
│           │   └── workers/
│           │       ├── Worker_API/             # (Clone hoặc Symlink từ agent_registry)
│           │       └── Worker_DB_Schema/
│           └── Dept_A2_Frontend/
│               ├── dept_config.json
│               ├── Lead_A2/
│               └── workers/
│
└── studio_control_plane/                       # GIAO DIỆN GIÁM SÁT & ĐIỀU HÀNH TRỰC QUAN (WEB STUDIO)
    ├── backend/                                # FastAPI + WebSocket + Watchdog File-system
    └── frontend/                               # React + Vite + TailwindCSS + React Flow + Monaco Editor
```

---

## LỘ TRÌNH TRIỂN KHAI 6 GIAI ĐOẠN (EXECUTION PHASES)

Hãy thực hiện tuần tự từ Giai đoạn 1 đến Giai đoạn 6. Không nhảy cóc. Kết thúc mỗi giai đoạn phải chạy bài kiểm tra nghiệm thu trước khi sang giai đoạn tiếp theo.

---

### GIAI ĐOẠN 1: KHỞI TẠO NỀN TẢNG CỐT LÕI, KÉT SẮT ZERO-TRUST & SQLITE WAL (`shared_core`)

#### 1.1. Tech Stack cần dùng
* **Hệ điều hành & Môi trường:** Linux (Ubuntu/Debian), Python 3.11+ (`venv`), SQLite3.
* **Thư viện Python:** `cryptography` (mã hóa Fernet cho `vault/`), `aiosqlite` (truy cập bất đồng bộ), `pydantic` (kiểm tra cấu trúc dữ liệu).
* **Cổng LLM:** Toàn bộ các lời gọi LLM trong hệ thống đều cấu hình `OPENAI_BASE_URL` trỏ về cổng **OmniRoute** nội bộ của VPS.

#### 1.2. Những điều cần làm
1. **Tạo cây thư mục chuẩn** tại `/opt/ai-holding/` và phân quyền Linux chặt chẽ.
2. **Khởi tạo cơ sở dữ liệu `resources.db` (Quản lý Tài nguyên & Khóa Dòng):**
   * Bật chế độ đọc/ghi đồng thời: `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA busy_timeout=5000;`.
   * Tạo bảng `service_accounts`:
     ```sql
     CREATE TABLE IF NOT EXISTS service_accounts (
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         provider TEXT NOT NULL,          -- 'supabase', 'vercel', 'gcloud', 'groq', 'gemini', 'cloudflare'
         account_email TEXT NOT NULL,     -- VD: baker-a1@dayhocvinhphat.site
         vault_secret_ref TEXT NOT NULL,  -- Khóa tham chiếu vào file secrets_store.enc trong vault/
         status TEXT DEFAULT 'AVAILABLE', -- 'AVAILABLE', 'IN_USE', 'RATE_LIMITED', 'EXHAUSTED'
         locked_by_company TEXT,          -- VD: 'Company_A_Bakery' (NULL nếu dùng chung như OmniRoute key)
         locked_by_agent TEXT,            -- Đường dẫn Agent đang giữ khóa
         quota_remaining REAL DEFAULT 100.0,
         cooldown_until DATETIME,
         updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
     );
     ```
   * Viết hàm `acquire_resource_lock(provider, company_id, agent_id)` sử dụng giao dịch `BEGIN IMMEDIATE TRANSACTION` của SQLite để đảm bảo 5 Agent chạy song song không bao giờ lấy trùng 1 tài khoản Free.
3. **Khởi tạo cơ sở dữ liệu `messages.db` (Tổng đài Tin nhắn, Phòng họp & Trace):**
   * Bật `WAL mode` tương tự `resources.db`.
   * Tạo 3 bảng cốt lõi:
     * `messages`: Lưu tin nhắn giữa các Agent (`id`, `sender_path`, `receiver_path`, `channel_type` [`DIRECT`, `DEPT_ROOM`, `COMPANY_LEADS`, `B2B_BRIDGE`, `DEVOPS_TICKET`], `payload_json`, `status` [`PENDING`, `PROCESSING`, `DONE`, `PAUSED`, `FAILED`], `created_at`).
     * `agent_runtime_state`: Lưu trạng thái tức thời của từng Agent để hiển thị lên UI (`agent_path` PRIMARY KEY, `mode` [`SHARED`, `CLONED`], `status` [`IDLE`, `THINKING`, `WAITING_OTP`, `PAUSED`, `ERROR`], `current_step_summary`, `token_used`, `updated_at`).
     * `execution_steps`: Lưu lịch sử từng bước suy nghĩ (`Thought`, `Tool_Call`, `Tool_Output`, `memory_snapshot`) của từng Agent để phục vụ tính năng **Rollback & Replay** khi sửa Prompt.
4. **Xây dựng Két sắt `vault/`:**
   * Viết module `vault_manager.py` chỉ cho phép tiến trình mang định danh của cụm `devops_ministry` truy xuất.

#### 1.3. Những điều cần lưu ý
* Tuyệt đối không lưu mật khẩu dạng rõ (plaintext) trong `resources.db` hay trong bất kỳ file `MEMORY.md` nào. Trong `resources.db` và `MEMORY.md` chỉ được lưu `vault_secret_ref` (ví dụ: `vault://supabase/acc_01`).
* Luôn sử dụng `BEGIN IMMEDIATE` khi cập nhật trạng thái tài nguyên trong SQLite để tận dụng cơ chế Row/Table-Lock nguyên tử.

---

### GIAI ĐOẠN 2: XÂY DỰNG BỘ HẠ TẦNG `My_credential_devops_hermes` & CƠ CHẾ PHÂN MẢNH CONTEXT (SUB-AGENT SHARDING)

#### 2.1. Tech Stack cần dùng
* **Tự động hóa Trình duyệt & OTP:** `Playwright` kết nối qua cổng WebSocket tới Docker container `browserless/chrome` (tích hợp sẵn màn hình noVNC để vượt Captcha), thư viện `imaplib` / `email` của Python.
* **Tích hợp Hạ tầng:** `cloudflared` CLI, Cloudflare API, Supabase/Neon CLI, Google Cloud SDK (`gcloud`), OmniRoute API/CLI.

#### 2.2. Những điều cần làm
1. **Thiết kế Kiến trúc Phân tầng cho `My_credential_devops_hermes` (Giải quyết bài toán tràn Context Window):**
   * `My_credential_devops_hermes` **KHÔNG** trực tiếp ôm đồm cú pháp CLI của mọi dịch vụ vào file `SOUL.md` và `MEMORY.md` của chính nó.
   * Thay vào đó, `My_credential_devops_hermes` đóng vai trò **Tổng Chỉ Huy Hạ Tầng (Master Infrastructure Router)**:
     * `SOUL.md` của nó chỉ chứa quy tắc bảo mật Zero-Trust, cách phân loại Ticket từ các Công ty và quy trình điều phối cấp dưới.
     * `MEMORY.md` của nó chỉ lưu **Danh bạ Chuyên gia Cấp dưới (Sub-Agent Registry)** và bảng ánh xạ dự án nào của công ty nào đang dùng tài nguyên gì.
2. **Cấp quyền cho `My_credential_devops_hermes` công cụ `spawn_devops_specialist`:**
   * Khi hệ thống khởi chạy hoặc khi phát sinh một loại dịch vụ đám mây mới, `My_credential_devops_hermes` tự động sinh ra (hoặc triệu hồi) các Agent cấp dưới chuyên biệt nằm trong `/opt/ai-holding/shared_core/devops_ministry/specialists/`:
     * **`Sub_Cloudflared_DNS`**: Trong `SOUL.md` và `MEMORY.md` chỉ chứa kiến thức về tạo Cloudflare Tunnel, trỏ DNS subdomain `*.dayhocvinhphat.site`, cấu hình SSL. Chỉ được cấp Token Cloudflare từ `vault/`.
     * **`Sub_Database_Provisioner`**: Chuyên tạo project/database miễn phí trên Supabase, Neon, Turso; chạy migration ban đầu và trả về chuỗi kết nối đã ẩn mật khẩu.
     * **`Sub_GCloud_Compute`**: Chuyên quản lý Google Cloud Run, GCP Project, Vercel, Render để build và deploy source code từ thư mục `workspace/` của các công ty.
     * **`Sub_Identity_Mail_OTP`**: Chuyên điều khiển trình duyệt ảo tạo email biến thể `*-a1@dayhocvinhphat.site`, điền form đăng ký tài khoản mới và gọi `imap_otp_reader.py` lấy mã xác thực.
     * **`Sub_OmniRoute_KeyPool`**: Chuyên theo dõi sức khỏe bể API Key của OmniRoute. Khi gặp lỗi `429 Too Many Requests` hoặc khi có lệnh lấy thêm key Groq/Gemini/OpenRouter, nó phối hợp với `Sub_Identity_Mail_OTP` lấy key mới, lưu vào `vault/`, ghi log vào `resources.db` và gọi `omniroute_injector.py` nạp thẳng vào OmniRoute mà không cần khởi động lại hệ thống.
3. **Thiết lập Giao thức Ticket Hạ tầng (`DEVOPS_TICKET`):**
   * Khi `CEO_A` hoặc `Lead_A1` cần Database hoặc cần Deploy web bán bánh, họ gửi một bản tin JSON chuẩn vào hòm thư của `My_credential_devops_hermes`.
   * `My_credential_devops_hermes` đọc Ticket -> Tách thành các nhiệm vụ nhỏ -> Giao cho `Sub_Database_Provisioner`, `Sub_GCloud_Compute` và `Sub_Cloudflared_DNS` thực thi -> Gom kết quả trả về cho `Company_A`.

#### 2.3. Những điều cần lưu ý
* **Nguyên tắc Đặc quyền Tối thiểu (Least Privilege) ngay trong nội bộ DevOps:** Khi `My_credential_devops_hermes` giao việc cho `Sub_Cloudflared_DNS`, nó chỉ trích xuất đúng `CF_API_TOKEN` từ `vault/` truyền vào biến môi trường tạm thời (ephemeral env) của lượt chạy đó; `Sub_Cloudflared_DNS` không bao giờ đọc được khóa Google Cloud hay mật khẩu Gmail.
* **Cổng Phê duyệt Chủ tịch (Human Approval Gate):** Đối với các thao tác nhạy cảm (như xóa Database, đè bản Production, hoặc dùng dịch vụ Google Cloud có tính phí), `My_credential_devops_hermes` phải chuyển trạng thái Ticket sang `WAITING_CHAIRMAN_APPROVAL` và bắn thông báo lên Web Studio / Telegram chờ bạn bấm `Approve`.

---

### GIAI ĐOẠN 3: KHO KHUÔN MẪU (`agent_registry`), CƠ CHẾ SYMLINK/CLONE & QUYỀN TỰ ĐẺ CẤP DƯỚI

#### 3.1. Tech Stack cần dùng
* **Ngôn ngữ & Công cụ:** Python (`os.symlink`, `os.path.islink`, `shutil.copytree`), JSON Schema cho Tool Calling (chuẩn OpenAI Function Calling qua OmniRoute).

#### 3.2. Những điều cần làm
1. **Xây dựng bộ Khuôn mẫu Gốc tại `/opt/ai-holding/agent_registry/`:**
   * Mỗi Archetype (`CEO_Archetype`, `Dept_Lead_Archetype`, `Worker_Coding_Archetype`, `DevOps_Specialist_Archetype`) đều có cấu trúc chuẩn: `SOUL.md`, `MEMORY.md`, và thư mục `skills/`.
2. **Xây dựng Module Triệu hồi Agent (`agent_provisioner.py`) hỗ trợ 2 chế độ:**
   * **Chế độ Dùng chung (`--mode shared`):**
     * Tạo Symbolic Link (`ln -s`) từ `/opt/ai-holding/agent_registry/<Archetype>` (hoặc từ một Agent dùng chung) vào thư mục đích.
     * Mọi kinh nghiệm cập nhật vào `MEMORY.md` sẽ được chia sẻ tức thời trên toàn bộ các phòng ban đang gắn Symlink này.
   * **Chế độ Nhân bản (`--mode clone`):**
     * Copy (`cp -r`) `SOUL.md` và `skills/` sang thư mục Agent mới, khởi tạo file `MEMORY.md` trắng mang ngữ cảnh riêng của dự án/phòng ban đó, nhưng giữ nguyên cấu hình kết nối về `/opt/ai-holding/shared_core/messages.db` và `resources.db`.
3. **Xây dựng Tool Hệ thống cho phép Agent tự đẻ cấp dưới (`spawn_subordinate`):**
   * Cấp quyền gọi tool này cho: **Root Hermes**, **CEO các công ty**, **Trưởng phòng (`Dept_Lead`)**, và **`My_credential_devops_hermes`**.
   * Cú pháp Tool Call chuẩn:
     ```json
     {
       "name": "spawn_subordinate",
       "parameters": {
         "target_unit_type": "department | worker | devops_specialist",
         "new_agent_name": "Worker_Cart_API",
         "base_archetype": "Worker_Coding_Archetype",
         "mode": "clone",
         "custom_soul_directive": "Bạn chuyên trách xây dựng RESTful API cho giỏ hàng và thanh toán của tiệm bánh.",
         "initial_task_message": "Hãy đọc thiết kế DB tại workspace/schema.sql và viết API giỏ hàng."
       }
     }
     ```

#### 3.3. Những điều cần lưu ý
* **Vòng Kim Cô chống Đẻ Vô Hạn (`max_headcount` Guardrail):**
  * Trước khi thực thi `spawn_subordinate`, hệ thống bắt buộc phải đọc `company_config.json` và `dept_config.json`.
  * Mặc định: Mỗi Công ty tối đa **5 Phòng ban**, mỗi Phòng ban tối đa **6 Worker**, cụm `devops_ministry` tối đa **10 Sub-Agent**. Nếu một Trưởng phòng muốn đẻ vượt hạn mức này, lệnh sẽ bị chặn và chuyển thành yêu cầu xin phép Chủ tịch trên Web Studio.

---

### GIAI ĐOẠN 4: TRÁI TIM ĐIỀU PHỐI (`dispatcher_daemon.py`), GIAO TIẾP PHÂN CẤP & LIÊN DOANH B2B

#### 4.1. Tech Stack cần dùng
* **Backend Core:** Python `asyncio` (xử lý bất đồng bộ nhiều Agent thức dậy cùng lúc với mức tiêu thụ RAM cực thấp), `httpx` (gọi OmniRoute API).

#### 4.2. Những điều cần làm
1. **Xây dựng `dispatcher_daemon.py` (Vòng lặp Điều phối Sự kiện):**
   * Chạy như một `systemd` service trên Linux (`ai-holding-dispatcher.service`).
   * Mỗi 0.5 giây quét bảng `messages` trong `messages.db` để tìm các tin nhắn có `status = 'PENDING'`.
   * Với mỗi tin nhắn:
     1. Kiểm tra xem thư mục của Agent nhận (`receiver_path`) có file cờ `.paused` hay không. Nếu có `.paused`, giữ nguyên trạng thái và bỏ qua (chờ User sửa Prompt).
     2. Nếu không bị Pause, đánh thức Agent dậy: Đọc `SOUL.md` + `MEMORY.md` + 10 tin nhắn gần nhất trong cuộc hội thoại + nội dung tin nhắn mới -> Gửi qua cổng **OmniRoute**.
     3. Ghi lại từng bước suy nghĩ (`Thought`, `Tool_Call`, `Result`) vào bảng `execution_steps`.
     4. Cho phép Agent gọi công cụ cập nhật lại file `MEMORY.md` của chính nó (`update_my_memory`), sau đó giải phóng bộ nhớ RAM và đưa Agent về trạng thái `IDLE`.
2. **Xây dựng Bộ Kiểm soát Phân quyền Giao tiếp (RBAC Router):**
   * Mọi lệnh gọi tool `send_message(to_agent_path, message_content)` đều phải đi qua hàm kiểm tra `validate_communication_permission(sender, receiver)`:
     * **Luồng Dọc (Báo cáo & Giao việc):** `Chairman (User)` <-> `CEO` <-> `Dept_Lead` <-> `Worker` (Hợp lệ).
     * **Luồng Ngang Nội bộ:**
       * `Worker` <-> `Worker` trong **cùng 1 phòng ban** (Hợp lệ).
       * `Dept_Lead` <-> `Dept_Lead` trong **cùng 1 công ty** (Hợp lệ).
     * **Luồng Hạ tầng:** `CEO` hoặc `Dept_Lead` -> `My_credential_devops_hermes` (Hợp lệ). `My_credential_devops_hermes` <-> các `Sub_*` của nó (Hợp lệ).
     * **Luồng Liên doanh B2B (`CEO_A` <-> `CEO_B`):**
       * Mặc định: **CHẶN HOÀN TOÀN** mọi giao tiếp giữa `Company_A` và `Company_B`.
       * Khi Chủ tịch Tập đoàn (User) ra lệnh bằng Prompt: *"Cho phép Công ty Bánh A hợp tác với Công ty Nước ngọt B"*, Root Hermes sẽ ghi một bản ghi vào `/opt/ai-holding/shared_core/b2b_contracts.json`:
         ```json
         {
           "contract_id": "B2B_BAKERY_SODA_01",
           "company_1": "Company_A_Bakery",
           "company_2": "Company_B_Soda",
           "allowed_representatives": ["Company_A_Bakery/CEO_A", "Company_B_Soda/CEO_B"],
           "scope": "Tích hợp API khuyến mãi chéo bánh ngọt và nước giải khát",
           "status": "ACTIVE"
         }
         ```
       * Khi `status == "ACTIVE"`, `CEO_A` và `CEO_B` được phép nhắn tin trực tiếp với nhau trong phòng họp `B2B_BRIDGE`, sau đó mỗi CEO tự quay về chỉ đạo các `Dept_Lead` của công ty mình.

#### 4.3. Những điều cần lưu ý
* **Bảo vệ Tuyệt đối `MEMORY.md` cá nhân:** Agent A chỉ được giao tiếp với Agent B thông qua tin nhắn văn bản. Không một Agent nào có quyền đọc trực tiếp file `MEMORY.md` của Agent khác (trừ cấp trên trực tiếp khi kiểm tra hoặc User trên Studio).
* **Chống Lặp Vô Tận Giữa 2 Agent (Ping-Pong Loop Protection):** Mỗi chuỗi hội thoại ngang cấp (ví dụ `CEO_A` nói chuyện với `CEO_B`, hoặc `Lead_A1` bàn với `Lead_A2`) chỉ được phép trao đổi tối đa **8 lượt (turns)** liên tiếp cho một chủ đề. Đến lượt thứ 8 phải chốt phương án thực thi hoặc báo cáo lên cấp trên.

---

### GIAI ĐOẠN 5: XÂY DỰNG TRUNG TÂM CHỈ HUY "AI HOLDING STUDIO" (WEB UI CONTROL PLANE)

#### 5.1. Tech Stack cần dùng
* **Backend Studio:** Python `FastAPI`, `WebSockets` (đẩy trạng thái real-time), `watchdog` (theo dõi sự kiện thêm/xóa file, thư mục, symlink trên `/opt/ai-holding/`).
* **Frontend Studio:** `React 18+` (Vite), `TailwindCSS`, `Lucide Icons`, `@xyflow/react` (React Flow để vẽ sơ đồ tổ chức sống), `@monaco-editor/react` (trình sửa nóng `SOUL.md` & `MEMORY.md`).

#### 5.2. Những điều cần làm
Xây dựng ứng dụng Web Studio với 5 Phân khu Chức năng cốt lõi:

1. **Bản đồ Tổ chức Sống (Live Topology Canvas - React Flow):**
   * Tự động đọc cấu trúc `/opt/ai-holding/` để vẽ các khối:
     * **Cụm Trung tâm (`devops_ministry`):** Hiển thị `My_credential_devops_hermes` ở trung tâm kèm các nhánh tỏa ra dàn Sub-Agent (`Sub_Cloudflared_DNS`, `Sub_Database_Provisioner`, `Sub_GCloud_Compute`, `Sub_Identity_Mail_OTP`, `Sub_OmniRoute_KeyPool`).
     * **Cụm Các Công ty (`companies/`):** Hiển thị từng Công ty -> CEO -> Các Phòng ban -> Các Worker.
     * **Cầu nối Liên doanh (B2B Edge):** Vẽ đường cáp đôi màu Vàng kim nối giữa `CEO_A` và `CEO_B` khi có hợp đồng trong `b2b_contracts.json`.
   * **Nhận diện Thị giác Shared vs Cloned:**
     * Backend dùng `os.path.islink(agent_path)` kiểm tra: Nếu là Symlink (`SHARED`), hiển thị viền nét đứt màu Tím kèm huy hiệu `🔗 SHARED` và đường nối mờ về `agent_registry`. Nếu là thư mục thật (`CLONED`), hiển thị viền liền màu Xanh lục kèm huy hiệu `🧬 CLONED`.
   * **Hiệu ứng Hạt sáng Giao tiếp:** Khi có tin nhắn đang chạy từ Agent A sang Agent B trong `messages.db`, đường nối giữa 2 node phát sáng chuyển động theo thời gian thực.

2. **"Bàn Mổ" Prompt & Trí Nhớ (Hot-Editor kèm Cảnh báo Nổ dây chuyền):**
   * Khi click vào bất kỳ Agent nào (kể cả các Sub-Agent dưới quyền `My_credential_devops_hermes`), mở ngăn kéo bên phải chứa **Monaco Editor** với 3 tab: `SOUL.md`, `MEMORY.md`, và `skills/`.
   * **Blast Radius Warning:** Nếu Agent đang chọn là Symlink (`SHARED`), hiện thanh cảnh báo đỏ cam liệt kê toàn bộ các phòng ban/công ty sẽ bị ảnh hưởng nếu sửa file này.
   * **Nút 1-Click `[✂️ Tách thành bản Clone riêng (Unlink & Clone)]`:** Cho phép bấm 1 nút để Backend tự động gỡ Symlink (`unlink`) và copy bản gốc sang (`cp -r`), giúp chỉnh sửa riêng cho phòng ban đó mà không ảnh hưởng tới nơi khác.

3. **Bộ Điều khiển "Phanh Khẩn Cấp - Sửa Prompt - Tua Lại" (Pause - Edit - Replay):**
   * **Nút `[⏸️ Tạm dừng Agent / Phòng ban]`:** Tạo ngay file `.paused` trong thư mục Agent đó để chặn bước chạy tiếp theo.
   * **Bảng `Execution Step Timeline`:** Hiển thị danh sách từng bước (`Step #1`, `Step #2`, `Step #3`) mà Agent vừa thực hiện từ bảng `execution_steps`.
   * **Nút `[⏪ Rollback về Bước #N & Chạy lại]`:** Khi phát hiện Agent suy luận sai ở Bước #3 do `SOUL.md` chưa rõ, User sửa lại `SOUL.md` ngay trên Monaco Editor, chọn Bước #2 và bấm nút này. Backend sẽ xóa các bước lỗi sau Bước #2, khôi phục `MEMORY.md` về thời điểm Bước #2, xóa file `.paused` và cho Agent chạy lại với `SOUL.md` mới!

4. **Phòng Nghe Lén Hội Thoại & Chèn Lệnh Chủ Tịch (Live Meeting Interceptor):**
   * Khi click vào một Phòng ban hoặc đường nối Liên doanh `CEO_A <-> CEO_B`, hiển thị khung chat thời gian thực của các Agent đang bàn bạc.
   * Có ô nhập liệu ở dưới cùng: **"Chủ tịch Tập đoàn chỉ đạo trực tiếp vào phòng họp"** để bạn có thể bẻ lái cuộc họp của các Agent bất cứ lúc nào.

5. **Trạm Giám sát Trình duyệt Ảo (`noVNC`) & Bể Tài nguyên (`resources.db` + OmniRoute):**
   * Nhúng khung `iframe` kết nối tới cổng `browserless` để xem trực tiếp màn hình của `Sub_Identity_Mail_OTP` khi nó đang đăng ký tài khoản hoặc lấy OTP; cho phép dùng chuột click giải Captcha trực tiếp trên Web Studio.
   * Hiển thị bảng quản lý `resources.db` (tài khoản nào đang rảnh, tài khoản nào đang bị khóa bởi công ty nào) và trạng thái bể Key của **OmniRoute** kèm nút bấm nhanh điều động `Sub_OmniRoute_KeyPool` đi lấy thêm key mới.

#### 5.3. Những điều cần lưu ý
* Mọi thao tác lưu file trên Monaco Editor phải dùng cơ chế **Atomic Write** (ghi ra file tạm `.tmp` rồi dùng `os.replace()` đè lên file chính) để tránh việc Agent đọc phải file `SOUL.md` hoặc `MEMORY.md` đang lưu dở dang.

---

### GIAI ĐOẠN 6: ĐỒNG BỘ TELEGRAM BOT, COMMAND CONSOLE & KIỂM THỬ THỰC CHIẾN (E2E VERIFICATION)

#### 6.1. Tech Stack cần dùng
* **Tích hợp điều khiển:** `python-telegram-bot` (hoặc `aiogram`), kết nối chung vào hàng đợi lệnh của **Root Hermes** cùng với thanh Command Bar trên Web Studio.

#### 6.2. Những điều cần làm
1. **Hợp nhất Cổng Ra Lệnh (Unified Command Gateway):**
   * Dù bạn gõ lệnh trên **Telegram** hay trên **Web Studio Command Bar**, câu lệnh đều được gửi tới **Root Hermes**.
   * Hỗ trợ đầy đủ các nhóm lệnh ngôn ngữ tự nhiên:
     * *"Tạo công ty bán bánh `Company_A_Bakery`, giao CEO_A thiết kế web thương mại điện tử bán bánh."*
     * *"Tạo công ty nước ngọt `Company_B_Soda`, giao CEO_B làm hệ thống quản lý đại lý và bán lẻ nước ngọt."*
     * *"Cho phép `Company_A_Bakery` và `Company_B_Soda` hợp tác làm chiến dịch mua bánh tặng voucher nước ngọt."*
     * *"Bảo `My_credential_devops_hermes` đẻ thêm 1 Sub-Agent chuyên quản lý dịch vụ Cloudflare R2 Storage."*
2. **Chạy Kịch bản Kiểm thử Đầu-Cuối (End-to-End Dry Run):**
   Sau khi code xong toàn bộ 5 giai đoạn trên, bạn (Root Hermes) phải tự động chạy kịch bản kiểm thử sau để chứng minh hệ thống hoạt động hoàn hảo:
   * **Test 1 (Cấu trúc & Phân mảnh DevOps):** Kiểm tra `/opt/ai-holding/shared_core/devops_ministry/` đã có `My_credential_devops_hermes` và 5 Sub-Agent chuyên biệt (`Sub_Cloudflared_DNS`, `Sub_Database_Provisioner`, `Sub_GCloud_Compute`, `Sub_Identity_Mail_OTP`, `Sub_OmniRoute_KeyPool`) với `SOUL.md` tách biệt rõ ràng.
   * **Test 2 (Tự động Đẻ Tổ chức):** Giả lập lệnh tạo `Company_A_Bakery` và `Company_B_Soda`. Kiểm tra `CEO_A` tự tạo `Dept_A1_Backend` và `Lead_A1` tự đẻ `Worker` bằng tool `spawn_subordinate`.
   * **Test 3 (Kiểm tra Tường lửa & Cầu nối B2B):**
     * Thử cho `CEO_A` nhắn tin cho `CEO_B` khi chưa có hợp đồng trong `b2b_contracts.json` -> Hệ thống phải từ chối (`PermissionDenied`).
     * Bật hợp đồng B2B -> `CEO_A` và `CEO_B` trao đổi thành công và lưu lịch sử vào `messages.db`.
   * **Test 4 (Luồng Ticket Hạ tầng Zero-Trust):** Giả lập `Lead_A1` gửi Ticket xin cấp Database PostgreSQL và tên miền `banhngot.dayhocvinhphat.site` lên `My_credential_devops_hermes` -> Kiểm tra `My_credential_devops_hermes` tự động phân việc xuống cho `Sub_Database_Provisioner` và `Sub_Cloudflared_DNS`, khóa dòng thành công trong `resources.db` mà không làm lộ mật khẩu gốc ra ngoài.
   * **Test 5 (Kiểm tra Web Studio, Pause & Unlink):** Kiểm tra API của Studio trả về đúng sơ đồ JSON cho React Flow, thử tạo cờ `.paused` và thử chuyển 1 Agent từ `SHARED` (Symlink) sang `CLONED`.

---

## YÊU CẦU BẮT ĐẦU NGAY LẬP TỨC CHO ROOT HERMES
Khi nhận được file tài liệu này:
1. Hãy đọc kỹ toàn bộ kiến trúc và xác nhận bạn đã nắm vững 6 giai đoạn.
2. Bắt đầu thực thi ngay **Giai đoạn 1** và **Giai đoạn 2** trên hệ thống: tạo cây thư mục `/opt/ai-holding/`, khởi tạo `resources.db`, `messages.db` (chế độ WAL), thiết lập `vault/`, và khởi tạo cụm `My_credential_devops_hermes` cùng 5 Sub-Agent chuyên trách hạ tầng.
3. Sau mỗi giai đoạn hoàn tất, hãy xuất báo cáo ngắn gọn gồm các file đã tạo và kết quả chạy thử nghiệm trước khi bước sang giai đoạn kế tiếp.