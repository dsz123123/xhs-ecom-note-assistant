from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import AppConfig
from app.database import Database


PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"
MANAGE_URL = "https://creator.xiaohongshu.com/publish/manage"
logger = logging.getLogger("xhs_ecom.publisher")


@dataclass(frozen=True)
class PublishResult:
    success: bool
    hang_status: str
    message: str


class XHSPublisher:
    """根据公开页面操作流程独立实现的小红书发布器。"""

    def __init__(self, config: AppConfig):
        self.config = config

    async def publish_task(self, task: dict) -> PublishResult:
        from playwright.async_api import async_playwright

        state_path = Path(task["storage_state"]).expanduser().resolve()
        if not state_path.is_file():
            return PublishResult(False, "not_attempted", f"登录态文件不存在：{state_path}")

        images = self._decode_list(task.get("images"))
        tags = self._decode_list(task.get("tags"))
        valid_images = [
            str(Path(image).expanduser().resolve())
            for image in images
            if Path(image).expanduser().is_file()
        ]
        if not valid_images:
            return PublishResult(False, "not_attempted", "没有可用图片")

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.config.headless)
            context = await browser.new_context(storage_state=str(state_path))
            page = await context.new_page()
            try:
                logger.info("开始执行任务 %s：%s", task["id"], task["title"])
                await page.goto(
                    PUBLISH_URL,
                    wait_until="domcontentloaded",
                    timeout=self.config.publish_timeout_ms,
                )
                await page.wait_for_timeout(3500)
                await self._verify_login(page)
                await self._select_image_tab(page)
                await self._upload_images(page, valid_images)
                await self._fill_note(page, task["title"], task["content"], tags)

                hang_status = "not_required"
                if bool(task.get("is_product_note")) and task.get("product_name"):
                    attached = await self._attach_product(
                        page,
                        str(task.get("platform_product_id") or ""),
                        str(task.get("product_name") or ""),
                    )
                    hang_status = "success" if attached else "failed"
                    if not attached and self.config.attach_failure_policy == "stop":
                        logger.warning("任务 %s 商品挂载失败，停止发布", task["id"])
                        return PublishResult(False, hang_status, "商品挂载失败，已停止发布")

                await self._click_publish(page)
                confirmed = await self._confirm_publish(page, str(task["title"]))
                message = "发布成功并完成作品确认" if confirmed else "发布已提交，请在作品管理中人工确认"
                logger.info("任务 %s 执行完成：%s", task["id"], message)
                return PublishResult(True, hang_status, message)
            except Exception as exc:
                logger.exception("任务 %s 发布异常", task["id"])
                return PublishResult(False, "failed", str(exc))
            finally:
                await context.close()
                await browser.close()

    @staticmethod
    def _decode_list(value) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        try:
            parsed = json.loads(value or "[]")
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    async def _verify_login(self, page) -> None:
        if "login" in page.url.lower():
            raise RuntimeError("登录态已失效，请重新保存账号登录态")
        login_markers = [
            page.get_by_text("登录", exact=True),
            page.locator('input[placeholder*="手机号"]'),
        ]
        for marker in login_markers:
            if await marker.count() and await marker.first.is_visible():
                raise RuntimeError("登录态已失效，请重新保存账号登录态")

    async def _select_image_tab(self, page) -> None:
        for locator in (
            page.get_by_text("上传图文", exact=True),
            page.locator(".creator-tab").filter(has_text="上传图文"),
        ):
            if await locator.count():
                await locator.first.click()
                await page.wait_for_timeout(1000)
                return

    async def _upload_images(self, page, images: list[str]) -> None:
        file_input = page.locator('input[type="file"]').first
        if not await file_input.count():
            raise RuntimeError("未找到图片上传控件")
        await file_input.set_input_files(images)
        await page.wait_for_timeout(max(5000, len(images) * 2500))

    async def _fill_note(self, page, title: str, content: str, tags: list[str]) -> None:
        title_input = page.locator('input[placeholder*="标题"]').first
        if not await title_input.count():
            title_input = page.locator('[class*="title"] [contenteditable="true"]').first
        if not await title_input.count():
            raise RuntimeError("未找到标题输入框")
        await title_input.click()
        await title_input.fill(title[:20])

        editor = page.locator('.ProseMirror[contenteditable="true"]').first
        if not await editor.count():
            editor = page.locator('[contenteditable="true"]').last
        if not await editor.count():
            raise RuntimeError("未找到正文编辑器")

        body = content.strip()
        clean_tags = [tag.strip().lstrip("#") for tag in tags if tag.strip()]
        if clean_tags:
            body += "\n\n" + " ".join(f"#{tag}" for tag in clean_tags[:8])
        await editor.click()
        await editor.fill(body)

    async def _attach_product(self, page, product_id: str, product_name: str) -> bool:
        try:
            add_button = await self._first_existing(
                page.get_by_role("button", name="添加商品"),
                page.locator('button:has-text("添加商品")'),
                page.locator(".multi-good-select-empty-btn button"),
            )
            if add_button is None:
                return False
            await add_button.scroll_into_view_if_needed()
            await add_button.click()
            await page.wait_for_timeout(1800)

            search = await self._first_existing(
                page.locator('input[placeholder*="搜索商品"]'),
                page.locator('.multi-goods-selector-modal input[type="text"]'),
            )
            if search is None:
                return False

            keyword = product_id.strip() or product_name.strip()
            if not keyword:
                return False
            await search.fill(keyword)
            await search.press("Enter")
            await page.wait_for_timeout(2200)

            selected = False
            if product_id:
                exact_text = page.get_by_text(product_id, exact=False).first
                if await exact_text.count():
                    row = exact_text.locator(
                        "xpath=ancestor::*[.//input[@type='checkbox']][1]"
                    )
                    if await row.count():
                        checkbox = row.locator('input[type="checkbox"]').first
                        if await checkbox.count():
                            await checkbox.click(force=True)
                            selected = True

            if not selected:
                wrapper = page.locator(".good-card-container .d-checkbox").first
                if await wrapper.count():
                    await wrapper.click()
                    selected = True

            if not selected:
                result_card = page.locator(".good-card-container").first
                if await result_card.count():
                    await result_card.click()
                    selected = True

            if not selected:
                return False

            save_button = await self._first_existing(
                page.get_by_role("button", name="保存"),
                page.locator('button:has-text("保存")'),
            )
            if save_button is None:
                return False
            await save_button.click()
            await page.wait_for_timeout(1200)
            return True
        except Exception:
            logger.exception("挂载商品时发生异常")
            return False

    async def _click_publish(self, page) -> None:
        button = await self._first_existing(
            page.get_by_role("button", name="发布"),
            page.locator('button:has-text("发布")'),
        )
        if button is None:
            raise RuntimeError("未找到发布按钮")
        await button.click()
        await page.wait_for_timeout(4500)

        error_tip = page.locator(
            '[class*="error"], [class*="toast"]:has-text("失败"), text="发布失败"'
        ).first
        if await error_tip.count() and await error_tip.is_visible():
            raise RuntimeError((await error_tip.inner_text()).strip() or "平台提示发布失败")

    async def _confirm_publish(self, page, title: str) -> bool:
        success_marker = page.locator(
            'text="发布成功", text="发布完成", [class*="success"]'
        ).first
        if await success_marker.count() and await success_marker.is_visible():
            return True

        try:
            await page.goto(
                MANAGE_URL,
                wait_until="domcontentloaded",
                timeout=min(self.config.publish_timeout_ms, 30_000),
            )
            await page.wait_for_timeout(2500)
            return title[:10] in (await page.content())
        except Exception:
            return False

    @staticmethod
    async def _first_existing(*locators):
        for locator in locators:
            if await locator.count():
                return locator.first
        return None


class TaskRunner:
    def __init__(self, database: Database, config: AppConfig):
        self.database = database
        self.publisher = XHSPublisher(config)

    def run(self, task_id: int) -> PublishResult:
        task = self.database.get_task(task_id)
        if task is None:
            return PublishResult(False, "not_attempted", "任务不存在")
        if task["status"] == "published":
            return PublishResult(False, task["hang_status"], "该任务已经发布")
        if task["status"] == "cancelled":
            return PublishResult(False, task["hang_status"], "该任务已取消")

        self.database.update_task_status(task_id, "publishing", error_message="")
        result = asyncio.run(self.publisher.publish_task(task))
        if result.success:
            self.database.update_task_status(
                task_id,
                "published",
                hang_status=result.hang_status,
                error_message=result.message,
                published_at=datetime.now().isoformat(timespec="seconds"),
            )
        else:
            self.database.update_task_status(
                task_id,
                "failed",
                hang_status=result.hang_status,
                error_message=result.message,
            )
        return result
