import sys
import os

# Add NumPy version compatibility handling before other imports
try:
    # Set environment variables for NumPy compatibility before importing NumPy
    os.environ['NPY_COMPATIBILITY_MODE'] = '1'
    
    # Now import NumPy and check version
    import numpy as np
    numpy_version = np.__version__
    print(f"Using NumPy version: {numpy_version}")
    
    # Additional compatibility settings for NumPy 2.x
    if numpy_version.startswith('2.'):
        # These settings help with NumPy 1.x compiled modules
        os.environ['NPY_RELAXED_STRIDES_CHECKING'] = '1'
        print("Applied NumPy 2.x compatibility settings")
        
except ImportError as e:
    print(f"NumPy import error: {e}")
    print("Attempting to continue without NumPy. Some functionality may be limited.")

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from config.config_manager import ConfigManager

def main():
    # 创建应用程序实例
    app = QApplication(sys.argv)
    app.setApplicationName("EasyDesktopAgent")
    app.setStyle("Fusion")  # 使用Fusion风格，跨平台一致性好
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 创建并显示主窗口
    window = MainWindow(config_manager)
    window.show()
    
    # 运行应用程序事件循环
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()