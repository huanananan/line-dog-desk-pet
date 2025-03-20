import sys
import os
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QCursor, QImage, QContextMenuEvent
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QMenu, QAction
from PIL import Image, ImageSequence


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        self.target_size = (200, 200)
        self.frames = []
        self.current_frame = 0
        self.gif_files = []
        self.current_index = 0
        self.initUI()
        self.load_file_list()
        self.load_animation()
        self.oldPos = None
        self.dragging = False
        self.left_click = False
        self.refresh_file_menu()  # 手动刷新菜单

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(*self.target_size)

        # 初始化右键菜单
        self.menu = QMenu(self)
        self.create_file_menu()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        self.menu.addAction(exit_action)

        # 动画显示组件
        self.label = QLabel(self)
        self.label.setFixedSize(*self.target_size)
        self.label.setAlignment(Qt.AlignCenter)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateFrame)

    def load_file_list(self):
        """加载并排序GIF文件列表"""
        gif_dir = self.resource_path('emojis')
        print(f"Directory being checked: {gif_dir}")  # 调试信息
        if os.path.exists(gif_dir):
            all_files = os.listdir(gif_dir)
            print(f"All files in directory: {all_files}")  # 打印目录中的所有文件
            self.gif_files = sorted([f for f in all_files if f.lower().endswith('.gif')])
            print(f"GIF files found: {self.gif_files}")  # 打印识别出的GIF文件
        else:
            print("表情包目录不存在！")
            sys.exit()

    def create_file_menu(self):
        """创建文件选择子菜单"""
        self.file_menu = QMenu("选择表情", self)
        self.menu.addMenu(self.file_menu)
        self.refresh_file_menu()

    def refresh_file_menu(self):
        """刷新文件菜单项"""
        print("Refreshing file menu...")  # 调试信息
        self.file_menu.clear()
        if not self.gif_files:
            print("No GIF files found!")  # 如果列表为空，打印提示信息
        for filename in self.gif_files:
            print(f"Adding GIF: {filename}")  # 打印正在处理的文件名
            action = QAction(filename, self)
            action.triggered.connect(
                lambda checked, f=filename: (print(f"Loading selected GIF: {f}"), self.load_selected_gif(f)))
            self.file_menu.addAction(action)

    def load_selected_gif(self, filename):
        """加载用户选择的GIF"""
        try:
            index = self.gif_files.index(filename)
            self.current_index = index
            self.load_animation()
        except ValueError:
            print(f"文件 {filename} 不存在！")

    def load_animation(self):
        """加载当前索引对应的动画"""
        if not self.gif_files:
            return

        gif_dir = self.resource_path('emojis')
        selected = self.gif_files[self.current_index]
        file_path = os.path.join(gif_dir, selected)

        if self.process_gif(file_path):
            self.current_frame = 0
            self.timer.start(self.frame_delay)
            # 更新索引（下次加载下一个）
            self.current_index = (self.current_index + 1) % len(self.gif_files)
        else:
            print("加载失败，尝试下一个...")
            self.current_index = (self.current_index + 1) % len(self.gif_files)
            QTimer.singleShot(0, self.load_animation)

    def process_gif(self, file_path):
        """处理GIF文件"""
        self.frames.clear()
        try:
            with Image.open(file_path) as img:
                for frame in ImageSequence.Iterator(img):
                    processed = self.process_frame(frame)
                    self.frames.append(self.pil2pixmap(processed))
                # 标准化帧延迟时间，比如统一设置为100ms
                self.frame_delay = min(max(img.info.get('duration', 100), 50), 200)  # 设置最小和最大值
            return True
        except Exception as e:
            print(f"处理失败: {str(e)}")
            return False

    def process_frame(self, img):
        """单帧处理流程"""
        resized = self.resize_with_aspect(img)
        # 移除了居中裁剪的步骤
        return resized

    def resize_with_aspect(self, img):
        """保持宽高比调整宽度"""
        w, h = img.size
        target_width = self.target_size[0]
        ratio = target_width / w
        new_height = int(h * ratio)
        # 仅调整宽度，并按比例调整高度
        return img.resize((target_width, new_height), Image.Resampling.LANCZOS)

    def center_crop(self, img):
        """居中裁剪高度"""
        w, h = img.size
        if h == self.target_size[1]:
            return img
        if h < self.target_size[1]:
            return img.resize((w, self.target_size[1]), Image.Resampling.LANCZOS)
        top = (h - self.target_size[1]) // 2
        return img.crop((0, top, w, top + self.target_size[1]))

    def pil2pixmap(self, img):
        """PIL转QPixmap"""
        img = img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.size[0], img.size[1], QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)

    def updateFrame(self):
        """更新动画帧"""
        if self.frames:
            self.label.setPixmap(self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
        self.dragging = False
        self.left_click = event.button() == Qt.LeftButton

    def mouseMoveEvent(self, event):
        if self.oldPos:
            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPos()
            self.dragging = True

    def mouseReleaseEvent(self, event):
        if self.left_click and not self.dragging:
            # 仅当左键释放且没有进行拖动时，切换图片
            self.load_animation()
        self.left_click = False
        self.dragging = False

    def contextMenuEvent(self, event: QContextMenuEvent):
        # 右键点击显示菜单
        if event.reason() == QContextMenuEvent.Mouse:
            self.menu.exec_(QCursor.pos())


    @staticmethod
    def resource_path(relative_path):
        """获取资源路径"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller会创建一个临时文件夹，并将该文件夹存储在_MEIPASS中
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())