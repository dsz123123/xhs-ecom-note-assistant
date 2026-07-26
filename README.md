# 薯店种草助手

面向小红书电商运营的轻量桌面工具，完成：

**商品录入 → AI 生成多个带货笔记版本 → 人工编辑 → 自动挂商品 → 立即或定时发布**

项目用于作品集和本地效率工具，刻意控制范围，不包含库存、订单、复杂数据复盘或多平台分发。

## 已实现功能

### 商品库

- 商品名称
- 本地主图
- 店内商品 ID
- 卖点
- 标签
- 新增、编辑、删除

### AI 文案

- 一次生成种草、测评、促销三个版本
- 可单独生成场景风格
- OpenAI 兼容接口
- 未配置 API Key 时使用离线演示生成器
- 标题、正文、标签可人工修改
- 提示词约束不虚构参数、价格、功效和销量

### 发布

- Playwright 上传图文
- 商品 ID 优先精确匹配
- 商品名称搜索兜底
- 挂商品失败默认停止发布
- 可选“挂商品失败仍发布普通笔记”
- 登录态失效检测
- 发布结果与作品管理页二次确认
- 错误信息写入任务记录和日志文件

### 任务

- 立即发布
- 定时发布
- 待发布、发布中、已发布、失败、已取消状态
- 重试、取消和删除
- 程序异常退出后自动恢复卡住的发布中任务
- 每次仅执行一个任务，避免并发误发

### 多账号

- 每个账号绑定独立的 Playwright `storage_state.json`
- 任务明确关联账号
- 删除账号时同步删除该账号的任务

## 页面

1. 首页生成
2. 商品库
3. 发布任务
4. 设置

## Windows 安装

建议安装 64 位 Python 3.11 或 3.12。

直接双击：

```text
install.bat
```

安装完成后双击：

```text
start.bat
```

## macOS / Linux 安装

```bash
chmod +x install.sh start.sh
./install.sh
./start.sh
```

## 保存小红书登录态

先完成安装，然后运行：

```bash
.venv/Scripts/python scripts/save_login_state.py
```

macOS / Linux：

```bash
.venv/bin/python scripts/save_login_state.py
```

浏览器打开后手动登录小红书创作者中心，回到终端按回车。项目目录会生成：

```text
storage_state.json
```

在程序的“设置”页添加账号并选择该文件。

## AI 配置

设置页填写：

- API Base：例如 `https://api.openai.com/v1`
- API Key
- 模型名称

也可使用提供 OpenAI 兼容接口的其他模型服务。

不填写 API Key 仍可体验商品库、文案生成、任务管理和 UI，但离线文案只用于流程演示。

## 真实发布前检查

1. 使用测试账号。
2. 账号已开通店铺，并有已上架商品。
3. 商品库中的店内商品 ID 填写准确。
4. 商品主图为本地存在的 JPG、PNG、JPEG 或 WEBP。
5. 先关闭无头模式，观察一次完整发布。
6. 默认保持“挂商品失败则停止”。

## 数据位置

运行数据默认保存在：

```text
~/.xhs_ecom_note_assistant/
├── config.json
├── data/xhs_ecom.db
└── logs/application.log
```

API Key 当前保存在本机配置文件中。不要上传该配置文件或登录态文件。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖：

- 商品、账号、发布任务数据闭环
- 任务取消与重试
- 离线三版本生成

## 项目结构

```text
xhs-ecom-note-assistant/
├── app/
│   ├── config.py
│   ├── database.py
│   ├── logging_setup.py
│   ├── services/
│   │   ├── content_service.py
│   │   └── publisher.py
│   └── ui/
│       ├── dialogs.py
│       └── main_window.py
├── scripts/
│   └── save_login_state.py
├── tests/
│   └── test_core.py
├── install.bat
├── install.sh
├── start.bat
├── start.sh
├── main.py
└── requirements.txt
```

## 技术栈

- Python
- PyQt5
- SQLite
- Playwright
- OpenAI 兼容接口

## 来源和许可证

项目架构与桌面端思路参考：

- `BetaStreetOmnis/xhs_ai_publisher`，其项目标注为 Apache License 2.0

本项目的挂商品模块根据公开可观察的小红书创作者中心操作流程独立实现，没有复制未明确提供许可证的仓库源代码。

本仓库新增代码由 5255fgh 发布，许可证为：

```text
AGPL-3.0-or-later
```

## 已知限制

- 小红书创作者中心页面结构变化后，元素定位可能需要更新。
- 当前无法绕过验证码、滑块或平台风控。
- 定时发布要求程序持续运行。
- 当前不采集点赞、收藏、评论、浏览或成交数据。
- 未经真实店铺账号测试前，不应声称挂商品功能已通过所有账号环境验证。
