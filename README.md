# AI Holding OS — Nền Tảng Điều Hành Tập Đoàn Đa Tác Tử (Company-as-Code)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)

**AI Holding OS** là hệ điều hành doanh nghiệp tự hành (Company-as-Code), mô phỏng một **Tập đoàn AI** đa cấp bậc với triết lý quản trị:
* **Hệ thống tệp là Nguồn Chân lý (Unix Filesystem-First)**: Mọi công ty, phòng ban, nhân sự (`CEO`, `Dept Lead`, `Worker`) đều được quản trị dưới dạng thư mục và các tệp định danh (`agent_soul.md`, `agent_memory.md`).
* **Tiết kiệm tài nguyên (0 MB Idle RAM)**: Vận hành theo mô hình **Actor Model hướng sự kiện** qua SQLite WAL. Agent chỉ được nạp vào RAM khi có tin nhắn cần xử lý và giải phóng ngay khi hoàn tất.
* **Bảo mật tuyệt đối (Zero-Trust Security)**: Toàn bộ API token, mật khẩu, cơ sở dữ liệu được mã hóa trong Két sắt (`vault/`), chỉ cụm **DevOps Ministry** được quyền truy xuất và cấp phát credential đã che giấu (`masked connection string`).
* **Tường lửa giao tiếp (RBAC & B2B Bridge)**: Chặn liên lạc ngoài thẩm quyền; CEO các công ty thành viên chỉ có thể hợp tác khi Chủ tịch (Chairman) phê duyệt Hợp đồng B2B.
* **Bảng điều khiển trực quan (Studio Control Plane)**: Giao diện Web tương tác hiển thị Sơ đồ tổ chức theo thời gian thực, Trình chỉnh sửa nóng (Hot-Editor), Cảnh báo Bán kính ảnh hưởng (Blast Radius), và Time-Travel Rollback.

---

## 🏛️ Sơ Đồ Kiến Trúc Hệ Thống

```
ai-holding/
├── shared_core/                      # Trục xương sống của tập đoàn
│   ├── resources.db                  # Quản lý tài nguyên (Supabase, Vercel, GCloud, LLM Keys)
│   ├── messages.db                   # Hàng đợi tin nhắn đa kênh & Lịch sử bước thực thi
│   ├── b2b_contracts.json            # Danh bạ hợp đồng liên doanh B2B có hiệu lực
│   ├── global_limits.json            # Giới hạn định biên (Max Depts, Max Workers, Max Ping-Pong)
│   ├── vault/                        # Két sắt mã hóa đối xứng Fernet (Master Key)
│   ├── vault_manager.py              # Zero-Trust Vault Access Controller
│   ├── rbac_router.py                # Bộ lọc tường lửa quyền giao tiếp giữa các cấp
│   ├── dispatcher_daemon.py          # Daemon điều phối Event-driven Actor Loop
│   └── devops_ministry/              # Cụm chỉ huy hạ tầng tự động
│       ├── My_credential_devops_hermes/  # Tổng chỉ huy & Cổng gác Zero-Trust
│       └── specialists/              # 5 Chuyên gia (DNS, Database, Cloud, OTP, KeyPool)
├── agent_registry/                   # Kho khuôn mẫu nhân sự gốc (Archetypes)
│   ├── CEO_Archetype/
│   ├── Dept_Lead_Archetype/
│   ├── Worker_Coding_Archetype/
│   └── DevOps_Specialist_Archetype/
├── companies/                        # Các công ty thành viên thực tế (Dynamic)
│   └── <Tên_Công_Ty>/
│       ├── CEO/
│       ├── departments/
│       └── workspace/
└── studio_control_plane/             # Trung tâm điều khiển Studio (Web UI)
    ├── backend/                      # FastAPI + WebSockets + REST APIs
    └── frontend/                     # React + Vite + Tailwind CSS Dashboard
```

---

## 🚀 Hướng Dẫn Cài Đặt Nhanh

### 1. Yêu cầu hệ thống
* Hệ điều hành: Linux / macOS / Windows (WSL2)
* Python: 3.11 trở lên
* [uv](https://docs.astral.sh/uv/) (hoặc `python3 -m venv`)
* Node.js: v18+ (chỉ cần nếu bạn muốn sửa code frontend; bản build sẵn đã có trong repo)

### 2. Cài đặt môi trường Python
```bash
# Clone dự án về máy
git clone <URL_REPO_CUA_BAN>
cd AI_agent_company

# Tạo môi trường ảo và cài đặt thư viện
uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
```

### 3. Cấu hình Cổng LLM
Mặc định hệ thống kết nối tới OmniRoute tại `http://localhost:20128/v1` (tương thích hoàn toàn chuẩn OpenAI). Bạn có thể cấu hình trong file `.env`:
```env
OMNIROUTE_URL=http://localhost:20128/v1
OMNIROUTE_API_KEY=your_api_key_here
OMNIROUTE_MODEL=auto/best-coding
```

---

## 🖥️ Khởi Động & Sử Dụng

### Khởi động toàn bộ nền tảng (1 lệnh duy nhất):
```bash
./start_platform.sh
```
Lệnh này sẽ tự động khởi động:
1. **Studio Control Plane** (FastAPI backend + React Dashboard) tại cổng **8500**.
2. **Dispatcher Daemon** điều phối tin nhắn nền.

### Truy cập Giao diện Studio:
Mở trình duyệt và truy cập:
* Trên máy: **[http://localhost:8500](http://localhost:8500)**
* Qua mạng nội bộ (LAN): `http://<IP_MAY_BAN>:8500`

---

## 🎯 Hướng Dẫn Các Tính Năng Trên Studio Dashboard

### 1. Sơ đồ Tổ chức (Interactive Topology Canvas)
* Hiển thị toàn cảnh: Bộ chỉ huy DevOps, các công ty thành viên, phòng ban và nhân viên.
* **Nhãn trạng thái**:
  * `🔗 SHARED`: Nhân sự dùng chung khuôn mẫu (tiết kiệm ổ cứng qua Symlink).
  * `🧬 CLONED`: Nhân sự đã tách thành bản độc lập.
* **Cầu nối Vàng B2B**: Các công ty có hợp đồng liên doanh đang kích hoạt sẽ nối với nhau bằng đường viền vàng ánh kim chuyển động.

### 2. Phát lệnh của Chủ tịch (Chairman Command Bar)
Thanh nhập lệnh ở góc dưới màn hình cho phép bạn điều hành toàn bộ tập đoàn:
* **Tạo công ty mới**:
  ```text
  Tạo công ty Company_E_Commerce
  ```
* **Cấp phép hợp tác B2B**:
  ```text
  Cho phép Company_A_Bakery và Company_B_Soda hợp tác phát triển combo
  ```
* **Giao việc hoặc gửi thông điệp trực tiếp** tới bất kỳ Agent nào.

### 3. Trình chỉnh sửa nóng (Hot-Editor)
* Bấm vào bất kỳ thẻ Agent nào trên màn hình để mở bảng điều khiển bên phải.
* Sửa trực tiếp **Nhân cách / Nhiệm vụ** (`agent_soul.md`) và **Bộ nhớ** (`agent_memory.md`). Bấm **Lưu** để áp dụng ngay lập tức (Atomic Write an toàn).
* **Cảnh báo Bán kính ảnh hưởng (Blast Radius)**: Nếu Agent là bản `SHARED`, hệ thống cảnh báo số lượng Agent khác sẽ bị ảnh hưởng, kèm nút **"Unlink & Clone"** để tách riêng thành bản Clone độc lập an toàn chỉ với 1 click.

### 4. Dòng thời gian & Rollback (Time-Travel Debugging)
* Mỗi bước suy nghĩ (`thought`), gọi công cụ (`tool_call`), và kết quả thực thi đều được ghi lại.
* Nếu Agent đi sai hướng, bạn chỉ cần bấm **"Rollback về đây"** — hệ thống sẽ khôi phục lại trạng thái bộ nhớ chính xác tại bước đó và xóa các bước lỗi tiếp sau.

### 5. Quản trị Tài nguyên & Két sắt (Tab Tài nguyên)
* Theo dõi danh sách tài khoản dịch vụ (`service_accounts`): Database (Supabase, Neon), Hosting (Cloud Run, Vercel), Domains (Cloudflare), và API Key Pools.
* Xem công ty/agent nào đang giữ khóa (Lock) tài nguyên.

---

## 🧪 Chạy Kiểm Thử Tự Động (Pytest)

Dự án đi kèm bộ kiểm thử toàn diện xác minh tính bất biến của kiến trúc:
```bash
PYTHONPATH=ai-holding .venv/bin/pytest ai-holding/tests/test_architecture.py -v
```
Bộ test bao gồm:
1. `test_vault_zero_trust`: Xác nhận Zero-Trust chặn tuyệt đối các agent trái quyền truy cập Két sắt.
2. `test_resources_atomic_locking`: Xác nhận khóa nguyên tử chống tranh chấp tài nguyên (`BEGIN IMMEDIATE`).
3. `test_agent_provisioning_and_headcount`: Xác nhận tự động chặn vượt trần định biên nhân sự.
4. `test_unlink_and_clone`: Xác nhận cơ chế chuyển đổi từ Shared sang Cloned độc lập.
5. `test_rbac_firewall_and_b2b`: Xác nhận tường lửa giao tiếp và cơ chế cầu nối B2B.
6. `test_execution_steps_and_rollback`: Xác nhận tua ngược dòng thời gian và phục hồi bộ nhớ.

---

## 🛑 Dừng Hệ Thống

Khi không còn nhu cầu sử dụng, chạy lệnh:
```bash
./stop_platform.sh
```

---

## 📄 Bản Quyền & Tác Giả
* Phát triển theo thiết kế kiến trúc chuẩn trong tài liệu `hermes_multi_agent_company_blueprint.md`.
* Giấy phép: MIT License.
