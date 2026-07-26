from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    output = Path("storage_state.json").resolve()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://creator.xiaohongshu.com/", wait_until="domcontentloaded")
        input("请在浏览器中完成登录，确认进入创作者中心后按回车：")
        context.storage_state(path=str(output))
        browser.close()
    print(f"登录态已保存：{output}")


if __name__ == "__main__":
    main()
