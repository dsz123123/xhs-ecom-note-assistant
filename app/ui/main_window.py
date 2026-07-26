from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QDateTime, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateTimeEdit, QFormLayout,
    QHeaderView, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.config import AppConfig
from app.database import Database
from app.logging_setup import configure_logging
from app.services.content_service import ContentService
from app.services.publisher import PublishResult, TaskRunner
from app.ui.dialogs import AccountDialog, ProductDialog

STATUS_TEXT = {
    "draft": "草稿", "pending": "待发布", "publishing": "发布中",
    "published": "已发布", "failed": "失败", "cancelled": "已取消",
}
HANG_TEXT = {
    "pending": "待处理", "success": "成功", "failed": "失败",
    "not_required": "无需挂载", "not_attempted": "未尝试",
}


class Worker(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    def run(self):
        try:
            self.succeeded.emit(self.function())
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        configure_logging()
        self.database = Database()
        self.config = AppConfig.load()
        self.variants = []
        self.current_product = None
        self.worker = None
        self.schedule_busy = False

        self.setWindowTitle("薯店种草助手")
        self.resize(1220, 790)
        self.setMinimumSize(1000, 680)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_home(), "首页生成")
        self.tabs.addTab(self._build_products(), "商品库")
        self.tabs.addTab(self._build_tasks(), "发布任务")
        self.tabs.addTab(self._build_settings(), "设置")
        self._apply_style()
        self.refresh_all()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_due_task)
        self.timer.start(max(10, self.config.schedule_check_seconds) * 1000)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f6f7f9; color: #202124; }
            QTabWidget::pane { border: 1px solid #dfe3e8; background: white; }
            QTabBar::tab { padding: 10px 24px; }
            QTabBar::tab:selected { font-weight: 600; }
            QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
                background: white; border: 1px solid #cfd5dc;
                border-radius: 5px; padding: 6px;
            }
            QPushButton { background: #c92d47; color: white; border: none;
                border-radius: 5px; padding: 8px 14px; }
            QPushButton:disabled { background: #b8bdc4; }
            QTableWidget { background: white; gridline-color: #e4e7eb; }
        """)

    @staticmethod
    def _prepare_table(table):
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)

    def _build_home(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left = QVBoxLayout()
        form = QFormLayout()
        self.product_combo = QComboBox()
        self.account_combo = QComboBox()
        self.style_combo = QComboBox()
        self.style_combo.addItems(["一次生成三版", "种草", "测评", "促销", "场景"])
        form.addRow("商品", self.product_combo)
        form.addRow("账号", self.account_combo)
        form.addRow("生成方式", self.style_combo)
        left.addLayout(form)
        self.generate_button = QPushButton("生成带货笔记")
        self.generate_button.clicked.connect(self.generate_content)
        left.addWidget(self.generate_button)
        self.variant_list = QListWidget()
        self.variant_list.currentRowChanged.connect(self.display_variant)
        left.addWidget(QLabel("生成结果"))
        left.addWidget(self.variant_list)
        layout.addLayout(left, 1)

        right = QVBoxLayout()
        self.title_edit = QLineEdit()
        self.title_count = QLabel("0 / 20")
        self.title_edit.textChanged.connect(
            lambda text: self.title_count.setText(f"{len(text)} / 20")
        )
        self.content_edit = QTextEdit()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("好物分享, 实用推荐")
        right.addWidget(QLabel("标题"))
        right.addWidget(self.title_edit)
        right.addWidget(self.title_count)
        right.addWidget(QLabel("正文"))
        right.addWidget(self.content_edit, 1)
        right.addWidget(QLabel("标签（逗号分隔）"))
        right.addWidget(self.tags_edit)

        row = QHBoxLayout()
        self.schedule_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(600))
        self.schedule_edit.setCalendarPopup(True)
        self.schedule_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        pending = QPushButton("加入待发布")
        scheduled = QPushButton("加入定时任务")
        pending.clicked.connect(lambda: self.save_task(False))
        scheduled.clicked.connect(lambda: self.save_task(True))
        row.addWidget(self.schedule_edit)
        row.addWidget(pending)
        row.addWidget(scheduled)
        right.addLayout(row)
        layout.addLayout(right, 2)
        return page

    def _build_products(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        actions = QHBoxLayout()
        for text, callback in [
            ("新增", self.add_product), ("编辑", self.edit_product),
            ("删除", self.delete_product),
        ]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.product_table = QTableWidget(0, 6)
        self.product_table.setHorizontalHeaderLabels(
            ["ID", "名称", "商品 ID", "主图", "卖点", "标签"]
        )
        self._prepare_table(self.product_table)
        self.product_table.doubleClicked.connect(self.edit_product)
        layout.addWidget(self.product_table)
        return page

    def _build_tasks(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        actions = QHBoxLayout()
        for text, callback in [
            ("刷新", self.refresh_tasks), ("立即执行", self.publish_selected_task),
            ("重试", self.retry_task), ("取消", self.cancel_task),
            ("删除", self.delete_task),
        ]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        self.task_table = QTableWidget(0, 9)
        self.task_table.setHorizontalHeaderLabels(
            ["ID", "商品", "账号", "标题", "状态", "挂商品", "定时时间", "发布时间", "说明"]
        )
        self._prepare_table(self.task_table)
        layout.addWidget(self.task_table)
        return page

    def _build_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.api_base_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.model_edit = QLineEdit()
        self.headless_checkbox = QCheckBox("发布时不显示浏览器")
        self.failure_policy_combo = QComboBox()
        self.failure_policy_combo.addItem("挂商品失败则停止", "stop")
        self.failure_policy_combo.addItem("挂商品失败仍发布普通笔记", "publish_plain")
        form.addRow("API Base", self.api_base_edit)
        form.addRow("API Key", self.api_key_edit)
        form.addRow("模型", self.model_edit)
        form.addRow("浏览器", self.headless_checkbox)
        form.addRow("挂载失败策略", self.failure_policy_combo)
        layout.addLayout(form)
        save = QPushButton("保存设置")
        save.clicked.connect(self.save_settings)
        layout.addWidget(save)
        layout.addWidget(QLabel("账号登录态"))
        actions = QHBoxLayout()
        add = QPushButton("添加账号")
        delete = QPushButton("删除账号")
        add.clicked.connect(self.add_account)
        delete.clicked.connect(self.delete_account)
        actions.addWidget(add)
        actions.addWidget(delete)
        actions.addStretch()
        layout.addLayout(actions)
        self.account_table = QTableWidget(0, 3)
        self.account_table.setHorizontalHeaderLabels(["ID", "名称", "登录态文件"])
        self._prepare_table(self.account_table)
        layout.addWidget(self.account_table)
        return page

    def refresh_all(self):
        self.api_base_edit.setText(self.config.api_base)
        self.api_key_edit.setText(self.config.api_key)
        self.model_edit.setText(self.config.model)
        self.headless_checkbox.setChecked(self.config.headless)
        index = self.failure_policy_combo.findData(self.config.attach_failure_policy)
        self.failure_policy_combo.setCurrentIndex(max(0, index))
        self.refresh_products()
        self.refresh_accounts()
        self.refresh_tasks()

    def refresh_products(self):
        rows = self.database.list_products()
        current = self.product_combo.currentData()
        self.product_combo.clear()
        self.product_table.setRowCount(len(rows))
        for row_index, product in enumerate(rows):
            values = [product["id"], product["name"], product["product_id"],
                      product["main_image"], product["selling_points"], product["tags"]]
            for column, value in enumerate(values):
                self.product_table.setItem(row_index, column, QTableWidgetItem(str(value or "")))
            self.product_combo.addItem(product["name"], product["id"])
        index = self.product_combo.findData(current)
        if index >= 0:
            self.product_combo.setCurrentIndex(index)

    def refresh_accounts(self):
        rows = self.database.list_accounts()
        current = self.account_combo.currentData()
        self.account_combo.clear()
        self.account_table.setRowCount(len(rows))
        for row_index, account in enumerate(rows):
            for column, value in enumerate([account["id"], account["name"], account["storage_state"]]):
                self.account_table.setItem(row_index, column, QTableWidgetItem(str(value or "")))
            self.account_combo.addItem(account["name"], account["id"])
        index = self.account_combo.findData(current)
        if index >= 0:
            self.account_combo.setCurrentIndex(index)

    def refresh_tasks(self):
        rows = self.database.list_tasks()
        self.task_table.setRowCount(len(rows))
        for row_index, task in enumerate(rows):
            values = [
                task["id"], task.get("product_name") or "", task.get("account_name") or "",
                task["title"], STATUS_TEXT.get(task["status"], task["status"]),
                HANG_TEXT.get(task["hang_status"], task["hang_status"]),
                task.get("scheduled_at") or "", task.get("published_at") or "",
                task.get("error_message") or "",
            ]
            for column, value in enumerate(values):
                self.task_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    @staticmethod
    def selected_id(table):
        row = table.currentRow()
        if row < 0 or table.item(row, 0) is None:
            return None
        return int(table.item(row, 0).text())

    def add_product(self):
        dialog = ProductDialog(self)
        if dialog.exec_():
            values = dialog.values()
            if self._validate_product(values):
                self.database.save_product(values)
                self.refresh_products()

    def edit_product(self):
        product_id = self.selected_id(self.product_table)
        if product_id is None:
            QMessageBox.information(self, "提示", "请先选择商品")
            return
        product = self.database.get_product(product_id)
        if product is None:
            return
        dialog = ProductDialog(self, product)
        if dialog.exec_():
            values = dialog.values()
            if self._validate_product(values):
                self.database.save_product(values, product_id)
                self.refresh_products()

    def _validate_product(self, values):
        if not values["name"].strip():
            QMessageBox.warning(self, "缺少信息", "商品名称不能为空")
            return False
        if not Path(values["main_image"]).expanduser().is_file():
            QMessageBox.warning(self, "图片无效", "请选择存在的本地商品图片")
            return False
        if not values["selling_points"].strip():
            QMessageBox.warning(self, "缺少信息", "商品卖点不能为空")
            return False
        return True

    def delete_product(self):
        product_id = self.selected_id(self.product_table)
        if product_id is not None and QMessageBox.question(
            self, "确认删除", "确定删除选中商品？"
        ) == QMessageBox.Yes:
            self.database.delete_product(product_id)
            self.refresh_products()

    def add_account(self):
        dialog = AccountDialog(self)
        if dialog.exec_():
            name, storage_state = dialog.values()
            if not name:
                QMessageBox.warning(self, "缺少信息", "账号名称不能为空")
                return
            if not Path(storage_state).expanduser().is_file():
                QMessageBox.warning(self, "文件无效", "登录态 JSON 文件不存在")
                return
            self.database.save_account(name, storage_state)
            self.refresh_accounts()

    def delete_account(self):
        account_id = self.selected_id(self.account_table)
        if account_id is not None and QMessageBox.question(
            self, "确认删除", "删除账号会同时删除其发布任务，是否继续？"
        ) == QMessageBox.Yes:
            self.database.delete_account(account_id)
            self.refresh_accounts()
            self.refresh_tasks()

    def generate_content(self):
        product_id = self.product_combo.currentData()
        if product_id is None:
            QMessageBox.warning(self, "缺少商品", "请先在商品库添加商品")
            return
        product = self.database.get_product(int(product_id))
        if product is None:
            return
        self.current_product = product
        selection = self.style_combo.currentText()
        styles = ["种草", "测评", "促销"] if selection == "一次生成三版" else [selection]
        self.generate_button.setEnabled(False)
        self.worker = Worker(lambda: ContentService(self.config).generate_variants(product, styles))
        self.worker.succeeded.connect(self.content_generated)
        self.worker.failed.connect(self.operation_failed)
        self.worker.finished.connect(lambda: self.generate_button.setEnabled(True))
        self.worker.start()

    def content_generated(self, variants):
        self.variants = list(variants)
        self.variant_list.clear()
        for variant in self.variants:
            self.variant_list.addItem(f"{variant.style}｜{variant.title}")
        if self.variants:
            self.variant_list.setCurrentRow(0)

    def display_variant(self, index):
        if 0 <= index < len(self.variants):
            variant = self.variants[index]
            self.title_edit.setText(variant.title)
            self.content_edit.setPlainText(variant.content)
            self.tags_edit.setText(", ".join(variant.tags))

    def save_task(self, scheduled):
        if self.current_product is None:
            QMessageBox.warning(self, "没有内容", "请先选择商品并生成内容")
            return
        account_id = self.account_combo.currentData()
        if account_id is None:
            QMessageBox.warning(self, "没有账号", "请先在设置页添加账号")
            return
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        if not title or not content:
            QMessageBox.warning(self, "内容不完整", "标题和正文不能为空")
            return
        if len(title) > 20:
            QMessageBox.warning(self, "标题过长", "标题不能超过20个汉字")
            return
        scheduled_at = None
        if scheduled:
            date_time = self.schedule_edit.dateTime().toPyDateTime()
            if date_time <= datetime.now():
                QMessageBox.warning(self, "时间无效", "定时时间必须晚于当前时间")
                return
            scheduled_at = date_time.isoformat(timespec="seconds")
        style = ""
        index = self.variant_list.currentRow()
        if 0 <= index < len(self.variants):
            style = self.variants[index].style
        self.database.create_task({
            "product_id": self.current_product["id"], "account_id": int(account_id),
            "title": title, "content": content,
            "tags": [tag.strip().lstrip("#") for tag in self.tags_edit.text().replace("，", ",").split(",") if tag.strip()],
            "images": [self.current_product["main_image"]], "style": style,
            "is_product_note": True, "status": "pending", "scheduled_at": scheduled_at,
        })
        self.refresh_tasks()
        QMessageBox.information(self, "已保存", "任务已加入发布列表")

    def publish_selected_task(self):
        task_id = self.selected_id(self.task_table)
        if task_id is None:
            QMessageBox.information(self, "提示", "请先选择任务")
            return
        self.run_task(task_id, True)

    def run_task(self, task_id, show_result):
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "任务进行中", "当前已有任务正在执行")
            return
        self.worker = Worker(lambda: TaskRunner(self.database, self.config).run(task_id))
        if show_result:
            self.worker.succeeded.connect(self.publish_completed)
        else:
            self.worker.succeeded.connect(lambda _: self.refresh_tasks())
        self.worker.failed.connect(self.operation_failed)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _worker_finished(self):
        self.schedule_busy = False
        self.refresh_tasks()

    def publish_completed(self, result: PublishResult):
        self.refresh_tasks()
        QMessageBox.information(self, "执行结果", ("成功：" if result.success else "失败：") + result.message)

    def run_due_task(self):
        if self.schedule_busy or (self.worker is not None and self.worker.isRunning()):
            return
        due_ids = self.database.due_task_ids()
        if due_ids:
            self.schedule_busy = True
            self.run_task(due_ids[0], False)

    def retry_task(self):
        task_id = self.selected_id(self.task_table)
        if task_id is not None:
            self.database.retry_task(task_id)
            self.refresh_tasks()

    def cancel_task(self):
        task_id = self.selected_id(self.task_table)
        if task_id is not None:
            self.database.cancel_task(task_id)
            self.refresh_tasks()

    def delete_task(self):
        task_id = self.selected_id(self.task_table)
        if task_id is not None and QMessageBox.question(
            self, "确认删除", "确定删除选中任务？"
        ) == QMessageBox.Yes:
            self.database.delete_task(task_id)
            self.refresh_tasks()

    def save_settings(self):
        self.config.api_base = self.api_base_edit.text().strip()
        self.config.api_key = self.api_key_edit.text().strip()
        self.config.model = self.model_edit.text().strip()
        self.config.headless = self.headless_checkbox.isChecked()
        self.config.attach_failure_policy = self.failure_policy_combo.currentData()
        self.config.save()
        self.timer.setInterval(max(10, self.config.schedule_check_seconds) * 1000)
        QMessageBox.information(self, "已保存", "设置已保存")

    def operation_failed(self, message):
        self.schedule_busy = False
        self.refresh_tasks()
        QMessageBox.critical(self, "操作失败", message)


def run_app():
    application = QApplication(sys.argv)
    application.setApplicationName("薯店种草助手")
    window = MainWindow()
    window.show()
    sys.exit(application.exec_())
