# 薯店种草助手

<p align="center">
  面向小红书电商运营场景的 AI 内容生成与发布任务管理桌面工具
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue">
  <img alt="PyQt5" src="https://img.shields.io/badge/UI-PyQt5-green">
  <img alt="SQLite" src="https://img.shields.io/badge/Database-SQLite-lightgrey">
  <img alt="Playwright" src="https://img.shields.io/badge/Automation-Playwright-orange">
  <img alt="License" src="https://img.shields.io/badge/License-AGPL--3.0-red">
</p>

## 项目简介

小红书电商运营需要持续处理商品资料、撰写不同风格的种草内容、安排发布时间并重复完成上传操作。薯店种草助手将这些环节整合到一个本地桌面应用中，形成从商品管理、AI 文案生成、人工编辑到发布任务执行的完整工作流。

项目以轻量、本地运行和人工可控为设计原则，适合作为内容运营、电商运营和桌面自动化方向的实践项目。

## 解决的问题

- 商品资料分散，重复整理成本较高
- 同一商品需要编写多种表达风格的内容
- 标题、正文、标签和图片需要频繁重复录入
- 多账号和定时任务不便统一管理
- 发布失败后缺少清晰的任务状态与错误记录

## 核心流程

```text
商品录入
   ↓
AI 生成多个文案版本
   ↓
人工选择与编辑
   ↓
创建立即或定时发布任务
   ↓
Playwright 执行上传与商品挂载
   ↓
记录发布结果与异常信息
```

## 已实现功能

### 商品管理

- 录入商品名称、本地主图、店内商品 ID、卖点和标签
- 支持商品新增、编辑和删除
- 商品资料可直接用于生成文案和创建发布任务

### AI 文案生成

- 一次生成种草、测评、促销三个版本
- 支持单独生成场景化文案
- 支持 OpenAI Compatible API
- 未配置 API Key 时自动使用离线演示生成器
- 标题、正文和标签均可人工修改
- 提示词限制虚构商品参数、价格、功效、销量和用户反馈

### 发布任务

- 支持立即发布和定时发布
- 支持待发布、发布中、已发布、失败和已取消状态
- 支持任务重试、取消和删除
- 程序异常退出后自动恢复卡住的发布中任务
- 单任务顺序执行，避免并发误发

### 自动发布

- 使用 Playwright 上传图文内容
- 优先使用商品 ID 匹配店铺商品
- 商品名称作为备用搜索方式
- 商品挂载失败时默认停止发布
- 可选继续发布为普通笔记
- 检测账号登录态是否失效
- 记录发布结果、错误信息和运行日志

### 多账号管理

- 每个账号绑定独立的 Playwright 登录态文件
- 发布任务明确关联指定账号
- 支持统一管理多个账号的任务

## 页面组成

| 页面 | 主要用途 |
|---|---|
| 首页生成 | 选择商品、生成文案、编辑内容并创建任务 |
| 商品库 | 管理商品资料和本地图片 |
| 发布任务 | 查看任务状态、重试、取消或删除任务 |
| 设置 | 配置 AI 接口、发布策略和账号登录态 |

## 技术架构

| 模块 | 技术 | 用途 |
|---|---|---|
| 桌面界面 | PyQt5 | 构建本地可视化操作界面 |
| 数据存储 | SQLite | 保存商品、账号和发布任务 |
| 浏览器自动化 | Playwright | 执行页面上传、填写和发布操作 |
| AI 接口 | OpenAI Compatible API | 生成不同风格的电商内容 |
| 日志 | Python logging | 记录运行状态和异常信息 |

## 项目结构

```text
xhs-ecom-note-assistant/
├── app/
│   ├── config.py              # 应用配置与数据目录
│   ├── database.py            # SQLite 数据访问层
│   ├── logging_setup.py       # 日志配置
│   ├── services/
│   │   ├── content_service.py # AI 文案生成服务
│   │   └── publisher.py       # Playwright 发布服务
│   └── ui/
│       ├── dialogs.py         # 商品与账号编辑窗口
│       └── main_window.py     # 主窗口与页面逻辑
├── scripts/
│   └── save_login_state.py    # 保存账号登录态
├── tests/
│   └── test_core.py           # 核心流程测试
├── CONTRIBUTING.md
├── CHANGELOG.md
├── ROADMAP.md
├── install.bat
├── install.sh
├── start.bat
├── start.sh
├── main.py
└── requirements.txt
```

## 快速开始

### Windows

建议安装 64 位 Python 3.11 或 3.12。

双击安装：

```text
install.bat
```

安装完成后双击启动：

```text
start.bat
```

### macOS / Linux

```bash
chmod +x install.sh start.sh
./install.sh
./start.sh
```

## 保存小红书登录态

完成安装后运行：

```bash
.venv/Scripts/python scripts/save_login_state.py
```

macOS / Linux：

```bash
.venv/bin/python scripts/save_login_state.py
```

浏览器打开后手动登录小红书创作者中心，回到终端按回车。项目目录会生成 `storage_state.json`。随后在程序的“设置”页添加账号并选择该文件。

登录态文件包含账号会话信息，请勿上传到公开仓库或发送给他人。

## AI 配置

在“设置”页填写：

- API Base，例如 `https://api.openai.com/v1`
- API Key
- 模型名称

项目兼容采用 OpenAI API 格式的模型服务。未填写 API Key 时仍可体验商品库、离线文案生成、任务管理和完整界面流程。

## 数据与隐私

运行数据默认保存在：

```text
~/.xhs_ecom_note_assistant/
├── config.json
├── data/xhs_ecom.db
└── logs/application.log
```

商品资料、任务和账号配置默认保存在本机。API Key 当前保存在本机配置文件中，提交代码前应确认配置文件和登录态文件未被加入版本控制。

## 测试

```bash
python -m unittest discover -s tests -v
```

当前测试覆盖：

- 商品、账号和发布任务的数据闭环
- 任务取消与重试
- 离线多版本文案生成

## 适用场景

- 小红书店铺日常内容运营
- 电商运营助理的内容整理与任务管理
- 个人卖家和小型团队的本地效率工具
- Python 桌面应用、SQLite 和浏览器自动化学习实践

## 项目亮点

- 将 AI 内容生成和浏览器自动化整合为完整桌面工作流
- 使用分层结构拆分界面、数据、内容生成和发布服务
- 支持无 API Key 的离线演示模式，便于展示完整流程
- 使用本地 SQLite 保存业务数据，无需部署服务器
- 支持任务状态恢复、失败日志和多账号隔离
- 对高风险的商品挂载失败采用默认停止策略

## 后续计划

后续优化方向统一记录在 [ROADMAP.md](ROADMAP.md)，包括素材批量管理、任务队列增强、内容合规检查和发布可靠性提升。

版本变化记录见 [CHANGELOG.md](CHANGELOG.md)。

## 使用说明

小红书创作者中心页面结构调整后，自动化元素定位可能需要同步更新。项目不会绕过验证码、滑块或平台风控。定时发布要求程序保持运行。

自动发布功能在不同账号、店铺权限和平台页面版本下可能存在差异，正式使用前应先通过测试账号验证完整流程。

## 许可证

本项目采用 [GNU Affero General Public License v3.0 or later](LICENSE)。

项目架构与桌面端实现思路参考了公开的开源项目 `BetaStreetOmnis/xhs_ai_publisher`。本项目的商品挂载与任务管理流程基于公开可观察的页面操作独立实现。