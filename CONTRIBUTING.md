# 贡献指南

感谢关注薯店种草助手。

## 可以参与的内容

- 修复界面或数据处理问题
- 优化 Playwright 页面定位与等待逻辑
- 增加测试用例
- 改进安装脚本和运行说明
- 完善文档
- 提出适合轻量电商运营场景的功能建议

## 提交问题

提交 Issue 时建议提供：

1. 操作系统和 Python 版本
2. 问题出现前的操作步骤
3. 实际结果与预期结果
4. 错误日志或截图
5. 是否使用真实 AI 接口和真实账号环境

请勿上传以下敏感内容：

- API Key
- `storage_state.json`
- Cookie 或登录凭据
- 包含个人信息的商品、账号和任务数据库

## 本地开发

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py
```

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 提交规范

建议使用清晰的提交信息：

```text
feat: add image material management
fix: prevent duplicate scheduled publishing
docs: improve installation guide
test: cover invalid AI response
```

一次提交尽量只处理一个明确问题。涉及自动发布流程时，应说明是否经过测试账号验证。

## Pull Request

提交 Pull Request 前请确认：

- 程序能够正常启动
- 已运行现有测试
- 未提交 API Key、登录态或本地数据库
- 新增功能已经补充必要说明
- 自动发布相关改动保留人工确认和失败保护逻辑
