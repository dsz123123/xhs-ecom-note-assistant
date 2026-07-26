from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ProductDialog(QDialog):
    def __init__(self, parent=None, product: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("商品信息")
        self.resize(560, 360)
        product = product or {}
        layout = QFormLayout(self)

        self.name = QLineEdit(str(product.get("name", "")))
        self.image = QLineEdit(str(product.get("main_image", "")))
        self.product_id = QLineEdit(str(product.get("product_id", "")))
        self.selling_points = QTextEdit(str(product.get("selling_points", "")))
        self.tags = QLineEdit(str(product.get("tags", "")))

        browse = QPushButton("选择本地图片")
        browse.clicked.connect(self.choose_image)

        layout.addRow("名称*", self.name)
        layout.addRow("主图路径*", self.image)
        layout.addRow("", browse)
        layout.addRow("店内商品 ID", self.product_id)
        layout.addRow("卖点*", self.selling_points)
        layout.addRow("标签", self.tags)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择商品主图",
            "",
            "图片 (*.png *.jpg *.jpeg *.webp)",
        )
        if filename:
            self.image.setText(filename)

    def values(self) -> dict:
        return {
            "name": self.name.text(),
            "main_image": self.image.text(),
            "product_id": self.product_id.text(),
            "selling_points": self.selling_points.toPlainText(),
            "tags": self.tags.text(),
        }


class AccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加账号")
        self.resize(520, 170)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit()
        self.storage_state = QLineEdit()
        browse = QPushButton("选择 storage_state.json")
        browse.clicked.connect(self.choose_state)

        form.addRow("账号名称*", self.name)
        form.addRow("登录态文件*", self.storage_state)
        form.addRow("", browse)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_state(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "选择登录态文件",
            "",
            "JSON (*.json)",
        )
        if filename:
            self.storage_state.setText(filename)

    def values(self) -> tuple[str, str]:
        return self.name.text().strip(), self.storage_state.text().strip()
