# Boss Hiring — 招聘数据收集与处理系统 (Phase 1)

这是一个基于 Telegram Bot 的招聘数据自动化收集与处理系统，专为 **Boss Hiring** 猎头机构定制开发。系统能够自动收集求职者的简历和企业雇主的招聘需求，利用 Gemini AI 提取及总结信息，并将结构化数据存入 Google Sheets 电子表格，将简历等文件归档至 Google Drive 文件夹，最后向内部 Telegram 协作群组发送通知。

---

## 🚀 核心功能与技术栈

### 核心功能
* **求职者登记流程 (Candidate Flow)**: 支持手动一步步填写，或者直接上传简历文件（PDF/Word/图片）通过 Gemini AI 自动解析并回填表单，提供每一项的行内编辑修改功能。
* **企业招聘登记流程 (Company Flow)**: 收集企业基本信息、职位需求、福利及到岗时间，要求企业确认服务条款（80%月薪服务费），并支持上传执照或企业资料。
* **《Boss来了》合作申请 (Boss Show Flow)**: 专为招聘访谈节目定制的合作申请入口。
* **联系客服与静态看板 (Contact)**: 提供多渠道联系方式展示。
* **i18n 国际化支持**: 动态支持 **中文 (zh)**、**英文 (en)** 和 **高棉语 (km)**，遵循零用户界面硬编码原则。
* **本地容灾保障**: 当 Google Sheets 等云端 API 出现写入异常时，自动将数据落盘备份至本地 JSONL 格式，防止数据丢失。

### 技术栈
* **开发语言**: Python 3.11+
* **Telegram 框架**: `python-telegram-bot` v21 (支持异步协程、对话状态机 `ConversationHandler` 和 `PicklePersistence` 持久化)
* **人工智能**: `google-genai` (使用 `gemini-2.5-flash` 模型进行精准文档解析与多语言摘要生成)
* **数据存储**: `gspread` + Google Sheets API v4
* **文件存储**: `google-api-python-client` (Drive API v3)
* **配置管理**: `python-dotenv`

---

## ⚠️ 终极开发铁律 (Ultimate Architecture Constraints)

> [!IMPORTANT]
> 任何对本项目的后续开发和修改都必须遵循以下三条核心设计原则：

1. **绝对零硬编码 (Absolute Zero Hardcoding)**:
   * 严禁在 `bot/handlers/` 目录下的任何处理器中出现中、英、高棉语的任何字面量（例如 `"确定"`, `"Age"`, `"សូមទោស"`）。
   * 唯一的特外情况是 `start.py` 中的 `BOOTSTRAP_PROMPT` 全语种拼接常量，仅用于首次 /start 时的语言选择提示。
   * 所有的提示语、按键文本和通知内容均需使用翻译助手 `t("key.path", lang, var=value)` 动态查表获取。

2. **智能上下文返回机制 (Smart Inline Edit Routing)**:
   * 用户在最后一步 Review 确认界面点击某项数据旁的 `[✏️]` 重新填写按钮时，系统设置 `context.user_data["edit_return_target"] = CURRENT_REVIEW_STATE`。
   * 当用户在该状态重新输入/选择完毕后，系统必须检测该标记。如果存在，则直接用 `edit_message_text` 弹回 Review 界面，**严禁**让用户继续向下线性走完剩余步骤。

3. **输入容错防死锁 (Input Validation & Anti-deadlock)**:
   * 当系统进入需要点击 Inline 键盘按钮选择的状态时（如性别、学历），如果用户执意在输入框内打字输入，系统必须拦截输入，并重新发送当前界面的 Inline 键盘，同时附带 `t("common.or_type", lang)` 的提示，确保会话绝不中断或卡死。

4. **状态历史回退导航 (Back Navigation)**:
   * 每个输入步骤的 Inline 键盘都需包含 `t("common.back", lang)`（◀ 返回）按钮。
   * 在 `context.user_data["state_history"]` 中维护状态栈，点击返回时弹出上一个状态并跳转，实现流畅的退回修改体验。

---

## 📂 项目目录结构

```
boss-hiring-bot/
├── main.py                     # 程序入口，初始化并启动 Telegram Bot，注册 Handler
├── config.py                   # 配置管理，加载环境变量与全局静态配置
├── install.sh                  # 一键式环境部署安装脚本
├── requirements.txt            # Python 依赖包列表
├── credentials.json            # Google 服务账号授权凭证（Git忽略，需手动放置）
├── .env.example                # 环境变量配置模板
├── .env                        # 运行时环境变量文件（Git忽略，需手动创建）
├── locales/                    # 国际化语言包目录
│   ├── zh.json                 # 简体中文语言包
│   ├── en.json                 # 英文语言包
│   └── km.json                 # 高棉语（Khmer）语言包
├── bot/                        # 机器人的业务交互层
│   ├── states.py               # 定义全局对话状态机的 State 常量
│   ├── keyboards.py            # 全局键盘构建器（支持多语言与多选状态渲染）
│   ├── ui.py                   # 界面公共渲染组件（进度条、格式化 Review 确认卡片）
│   └── handlers/               # 对话流程控制器
│       ├── start.py            # /start 启动、语言选择与主菜单分流器
│       ├── candidate.py        # 求职者资料登记（支持手动和简历 AI 解析）对话状态机
│       ├── company.py          # 企业招聘登记（含福利多选与条款接受校验）对话状态机
│       ├── boss_show.py        # 《Boss来了》合作申请对话状态机
│       └── contact.py          # 静态客服联系方式名片展示
├── services/                   # 底层公共服务层
│   ├── i18n.py                 # 翻译加载与启动时三语 key-sets 一致性强校验
│   ├── gemini.py               # 简历文件解析与智能摘要生成（基于 gemini-2.5-flash）
│   ├── sheets.py               # Google Sheets 读写与每日顺序流水号（ID）生成，含重试容灾
│   ├── drive.py                # 简历等文件上传至 Google Drive 并设为公开只读共享
│   └── notifier.py             # 内部通知逻辑，统一格式化为中文发送至 HR 协作群
├── models/                     # 数据实体层
│   ├── candidate.py            # CandidateRecord 属性结构定义
│   └── company.py              # CompanyRecord 职位发布属性结构定义
├── prompts/                    # Gemini 提示词模板
│   ├── candidate_parse.txt     # 简历解析 JSON 提取提示词
│   ├── candidate_summary.txt   # 求职者信息中文总结提示词
│   └── company_summary.txt     # 招聘需求中文总结提示词
└── data/                       # 运行期持久化与备份数据（Git忽略）
    ├── persistence.pkl         # ptb 会话状态持久化文件
    └── failed_submissions.jsonl # 写入 Sheets 失败时的本地追加备份日志
```

---

## 🛠 部署与运行指南

### 1. 准备工作
1. **申请 Telegram Bot**: 通过 `@BotFather` 创建机器人并获取 `TELEGRAM_BOT_TOKEN`。
2. **获取内部群组 ID**: 将机器人加入您的内部 HR 管理群组，获取群组的 Chat ID（例如 `-100XXXXXXXXXX`），作为 `TELEGRAM_INTERNAL_GROUP_ID`。
3. **启用 Google API & 创建 Service Account**:
   * 在 [Google Cloud Console](https://console.cloud.google.com/) 创建项目。
   * 启用 **Google Sheets API** 和 **Google Drive API**。
   * 创建服务账号 (Service Account)，生成 JSON 格式的私钥密钥，并将其下载并命名为 `credentials.json`，放入 `boss-hiring-bot/` 根目录。
4. **共享文件夹与表格**:
   * 在云盘创建一个用作归档的文件夹，将该文件夹的权限分享给您的服务账号邮箱，复制其 `Folder ID`。
   * 创建一个 Google Sheets 电子表格，包含 `candidates`、`companies` 和 `boss_show` 三个工作表（若不存在，程序启动后会自动创建），同样将表格编辑权限分享给服务账号邮箱，复制其 `Spreadsheet ID`。
5. **申请 Gemini API Key**: 在 [Google AI Studio](https://aistudio.google.com/) 申请免费或付费的 API 密钥。

### 2. 配置环境变量
复制 `.env.example` 并重命名为 `.env`，填入对应的值：

```bash
TELEGRAM_BOT_TOKEN="你的Telegram_Bot_Token"
TELEGRAM_INTERNAL_GROUP_ID=-100XXXXXXXXXX
GEMINI_API_KEY="你的Gemini_API_Key"
GOOGLE_SERVICE_ACCOUNT_JSON="credentials.json"
GOOGLE_SHEET_ID="你的Google_Sheets_Spreadsheet_ID"
GOOGLE_DRIVE_FOLDER_ID="你的Google_Drive_Folder_ID"
```

### 3. 安装依赖与启动
在 macOS / Linux 上，您可以使用内置的脚本进行快速配置：

```bash
# 赋予安装脚本执行权限
chmod +x install.sh

# 运行脚本安装虚拟环境及依赖
./install.sh

# 激活虚拟环境
source .venv/bin/activate

# 启动 Bot
python main.py
```

或者使用手动安装步骤：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## ✅ 自动化测试

每次修改代码后运行：

```bash
scripts/run_tests.sh
```

该脚本会执行 Python 编译检查、语言包一致性校验、Telegram 对话 handler 回归测试，以及 `CallbackQueryHandler` 路由守卫，防止按钮事件再次误入文本处理函数。

---

## 🧩 系统模块详述

### 1. i18n 国际化模块 (`services/i18n.py`)
* **启动校验**: 在 Bot 启动时，`main.py` 会调用 `validate_locales()` 遍历 `locales/` 下的 `zh.json`、`en.json` 和 `km.json`。系统通过递归比对 dot-notation 键值集，确保三语的配置项完全一致。如果有任何键缺失或多余，将会在启动时抛出 `KeyError` 阻断运行，避免运行时由于翻译缺失导致白屏或崩溃。
* **翻译查表**: 使用 `t("menu.title", lang)` 获取值，支持 `{name}` 等占位符插值。

### 2. Gemini AI 解析与摘要 (`services/gemini.py`)
* **简历解析**: 接收用户上传的简历文件（通过 `types.Part.from_bytes(...)` 传入 Gemini），并根据 [prompts/candidate_parse.txt](file:///Users/mark/VSCode/Bosshiring/BossHring528/boss-hiring-bot/prompts/candidate_parse.txt) 引导 `gemini-2.5-flash` 输出纯 JSON，包含姓名、性别、年龄、国籍、城市、电话、语言、学历、工作年限、期望岗位等。
* **智能总结**: 根据配置，不管求职者使用什么语言输入，Gemini 都会使用用户指定的当前语言生成一段简练的背景总结与标签，同时还会对敏感风险点进行批注。

### 3. 数据层存储规范
数据分别写入 Google Sheets 的三个 Tab 页中：
* **`candidates` (求职者表)**: 包含流水号 (ID)、提交时间、语言、状态（默认为“新提交”）、解析 JSON 以及 HR 备注列。
* **`companies` (企业表)**: 包含企业名称、招聘岗位、福利清单（支持多选）、到岗要求、服务条款接受状态（是/否）等。
* **`boss_show` (合作表)**: 包含企业名称、联系人信息、采访主题和合作类型。

#### 🔢 唯一流水分账 ID 生成规则
每一条新纪录都会自动计算当天的流水号：
* 求职者前缀为 `C-` (如 `C-20260529-0001`)
* 企业前缀为 `J-` (如 `J-20260529-0001`)
* 合作申请前缀为 `B-` (如 `B-20260529-0001`)

#### 🛡️ 云端异常降级机制
当向 Google Sheets 写入失败时（例如配额超限或网络异常）：
1. 系统会等待 3 秒钟并自动重试一次。
2. 若重试仍然失败，数据将不会被丢弃，而是自动序列化为 JSON 追加写入到本地 `data/failed_submissions.jsonl` 中，同时通过 Telegram 向上报，由运维人员进行后续人工干预或脚本重录。

### 4. 内部协作群消息格式 (`services/notifier.py`)
当用户提交完成后，系统将向内部 Telegram 群组发送排版精美的卡片消息。为方便 HR 快速阅读，群组消息**统一固定为简体中文 (zh)** 发送，但会在卡片底部附带标记用户的原始使用语言。

求职者通知示例：
```
🆕 【新求职者】#C-20260529-0001

👤 张伟 | 中国 | 28岁
📍 金边
🗣 中文、英语
💼 期望岗位：客服、销售
💰 期望薪资：$800–$1200
📎 简历：查看文件(https://drive.google.com/...)

🏷 中文客服 / 销售 / 金边 / 立即可入职
📝 候选人具有3年客服经验，中英双语流利，有意向在金边从事销售或客服类工作。

🌐 用户语言：中文
⚡️ 请 HR 跟进
```

---

## 🔁 错误处理对照表

| 触发场景 | 降级容错机制 |
| :--- | :--- |
| **发送 `/cancel` 指令** | 清空当前会话数据，发送已取消提示，注销 ConversationHandler。 |
| **发送 `/lang` 指令** | 重置用户当前的对话阶段，弹回语言选择界面。 |
| **会话无操作超时** | 30 分钟无反应后，由 PTB JobQueue 自动终止对话并发送会话超时提示。 |
| **简历 AI 解析异常** | 自动跳过解析步骤，将 summary 等字段置为 “AI解析失败”，无缝切换到纯手动填写流程。 |
| **Google Drive 上传失败** | 忽略文件链接，留空 Sheets 中的链接列，不中断用户的注册流程。 |
| **按钮选择态下误打字输入** | 拒绝文本输入，重发 Inline 按钮并追加“或点击以下按钮：”提示。 |
