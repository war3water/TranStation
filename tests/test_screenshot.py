
# tests/test_screenshot.py
import os
import time
import pytest
from src.config_loader import ConfigLoader
from src.capture.screenshot import take_screenshot

@pytest.fixture(scope="module")
def config():
    """
    提供一个测试用的配置加载器实例。
    """
    return ConfigLoader().get_config()

def test_take_screenshot(config):
    """
    测试截图功能是否能成功创建文件。
    注意：此测试是交互式的，需要手动选择一个区域。
    """
    output_dir = config['testing']['screenshot_output_path']
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    save_path = os.path.join(output_dir, f"test_screenshot_{timestamp}.png")
    
    print("\n[INFO] 准备进行交互式截图测试...")
    print("[INFO] 请在 3 秒后出现的覆盖层中拖动鼠标选择一个区域。")
    print("[INFO] 如果不选择或者选择区域过小，测试将失败。")
    time.sleep(3)

    # 调用截图函数，并传入保存路径
    screenshot_data = take_screenshot(save_path=save_path)

    # 断言1: 函数应返回数据
    assert screenshot_data is not None, "截图操作被取消或失败，未返回数据。"
    assert screenshot_data['type'] == 'image'
    assert 'data' in screenshot_data
    assert len(screenshot_data['data']) > 100 # Base64字符串不应为空

    # 断言2: 文件应被创建
    assert os.path.exists(save_path), f"截图文件未在 '{save_path}' 创建。"
    
    # 断言3: 文件不应为空
    assert os.path.getsize(save_path) > 0, "截图文件为空。"

    print(f"\n[SUCCESS] 截图测试成功，文件已保存至: {save_path}")

    # 清理测试文件（可选）
    # os.remove(save_path)
