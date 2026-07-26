from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.config import AppConfig


@dataclass(frozen=True)
class NoteVariant:
    style: str
    title: str
    content: str
    tags: list[str]


STYLE_GUIDES = {
    "种草": "以真实使用体验切入，表达自然，突出适用场景和核心卖点，避免夸张承诺。",
    "测评": "用简洁测评结构描述特点、适合人群和使用感受，保持客观。",
    "促销": "突出购买理由和行动提示，但避免虚假紧迫感、绝对化用语和低质硬广。",
    "场景": "围绕具体生活或工作场景展开，让商品自然出现并解决明确问题。",
}


class ContentService:
    def __init__(self, config: AppConfig):
        self.config = config

    def generate_variants(
        self,
        product: dict,
        styles: list[str] | None = None,
    ) -> list[NoteVariant]:
        styles = styles or ["种草", "测评", "促销"]
        unknown = [style for style in styles if style not in STYLE_GUIDES]
        if unknown:
            raise ValueError(f"不支持的文案风格：{', '.join(unknown)}")

        if not self.config.api_key:
            return [self._fallback(product, style) for style in styles]

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是小红书电商内容编辑。只输出合法 JSON，不输出 Markdown。"
                        "不得虚构商品参数、功效、认证、销量或用户反馈。"
                    ),
                },
                {"role": "user", "content": self._build_prompt(product, styles)},
            ],
            "temperature": 0.75,
        }
        request = urllib.request.Request(
            self.config.api_base.rstrip("/") + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.config.request_timeout,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AI 接口返回 HTTP {exc.code}：{details[:300]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"无法连接 AI 接口：{exc.reason}") from exc

        try:
            text = body["choices"][0]["message"]["content"]
            parsed = self._parse_json(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("AI 返回格式不符合 OpenAI 兼容接口规范") from exc

        variants: list[NoteVariant] = []
        for item in parsed.get("versions", []):
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            tags = [str(tag).strip().lstrip("#") for tag in item.get("tags", [])]
            if title and content:
                variants.append(
                    NoteVariant(
                        style=str(item.get("style", "")).strip(),
                        title=title[:20],
                        content=content,
                        tags=[tag for tag in tags if tag][:8],
                    )
                )

        if len(variants) != len(styles):
            raise RuntimeError("AI 未返回完整版本，请重试或更换模型")
        return variants

    def _build_prompt(self, product: dict, styles: list[str]) -> str:
        style_text = "\n".join(
            f"- {style}：{STYLE_GUIDES[style]}" for style in styles
        )
        return f"""
商品名称：{product.get("name", "")}
商品卖点：{product.get("selling_points", "")}
商品标签：{product.get("tags", "")}

生成 {len(styles)} 个小红书带货笔记版本：
{style_text}

约束：
1. 标题不超过20个汉字。
2. 正文自然、可编辑，不虚构未提供的信息。
3. 每个版本提供3至6个标签。
4. 不使用“全网第一”“百分百有效”等绝对化表达。
5. 不承诺未提供的价格、优惠或功效。
6. 输出严格符合以下 JSON：
{{
  "versions": [
    {{"style":"种草","title":"...","content":"...","tags":["..."]}}
  ]
}}
""".strip()

    @staticmethod
    def _parse_json(text: str) -> dict:
        match = re.search(r"\{.*\}", text.strip(), re.DOTALL)
        if match is None:
            raise json.JSONDecodeError("未找到 JSON", text, 0)
        return json.loads(match.group(0))

    @staticmethod
    def _fallback(product: dict, style: str) -> NoteVariant:
        name = str(product.get("name") or "这件商品")
        selling_points = str(
            product.get("selling_points") or "使用方便，适合日常场景"
        ).strip()
        tags = [
            value.strip().lstrip("#")
            for value in str(product.get("tags") or "").replace("，", ",").split(",")
            if value.strip()
        ] or ["好物分享", "日常好物", "实用推荐"]

        titles = {
            "种草": f"{name}真实使用感",
            "测评": f"{name}值不值得入",
            "促销": f"{name}入手理由",
            "场景": f"这个场景很需要{name}",
        }
        bodies = {
            "种草": (
                f"最近在日常使用里试了{name}。\n\n"
                f"我比较在意的是：{selling_points}。\n\n"
                "适合确实有这类需求的人，先看自己的使用场景再决定。"
            ),
            "测评": (
                f"简单看一下{name}。\n\n"
                f"主要特点：{selling_points}。\n\n"
                "它的定位比较明确，是否适合主要取决于实际需求。"
            ),
            "促销": (
                f"正在考虑{name}的话，可以先看这几点：\n\n"
                f"{selling_points}。\n\n"
                "建议按需求购买，不盲目囤货。"
            ),
            "场景": (
                f"在需要高效处理日常需求的场景里，{name}会更方便。\n\n"
                f"它的重点是：{selling_points}。\n\n"
                "适合重视实用性的人。"
            ),
        }
        return NoteVariant(style, titles[style][:20], bodies[style], tags[:6])
