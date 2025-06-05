"""
Pytest配置文件

提供测试夹具和配置，支持现有的unittest测试和新的pytest测试。
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_config_file(temp_dir):
    """创建临时配置文件"""
    config_file = temp_dir / "test_config.json"
    yield config_file
    # 清理会自动进行，因为使用了temp_dir fixture


@pytest.fixture
def sample_yml_content():
    """提供示例YML内容"""
    return """l_english:
 test_key_1:0 "Test Value 1"
 test_key_2:0 "Test Value 2"
 test_key_with_placeholder:0 "Hello $PLAYER_NAME$!"
 test_key_with_brackets:0 "Welcome to [COUNTRY_NAME]"
"""


@pytest.fixture
def sample_yml_file(temp_dir, sample_yml_content):
    """创建示例YML文件"""
    yml_file = temp_dir / "test_localisation.yml"
    yml_file.write_text(sample_yml_content, encoding='utf-8')
    return yml_file


@pytest.fixture(autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # 确保测试时不会创建实际的配置文件
    original_cwd = os.getcwd()
    
    yield
    
    # 恢复原始工作目录
    os.chdir(original_cwd)


@pytest.fixture
def mock_api_key():
    """提供模拟的API密钥"""
    return "AIzaSyDummyKeyForTesting123456789"


@pytest.fixture
def sample_config():
    """提供示例配置"""
    return {
        "api_keys": ["AIzaSyDummyKeyForTesting123456789"],
        "source_language": "english",
        "target_language": "simp_chinese",
        "max_concurrent_tasks": 3,
        "api_call_delay": 1.0,
        "placeholder_patterns": [
            "(\\$.*?\\$)",
            "(\\[.*?\\])",
            "(@\\w+!)",
            "(#\\w+(?:;\\w+)*.*?#!|\\S*#!)"
        ],
        "gemini_model": "gemini-1.5-flash-latest",
        "key_rotation_strategy": "round_robin",
        "log_level": "info"
    }


# 标记定义
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "slow: 标记测试为慢速测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "unit: 标记为单元测试"
    )
    config.addinivalue_line(
        "markers", "gui: 标记为GUI相关测试"
    )
    config.addinivalue_line(
        "markers", "api: 标记为API相关测试"
    )


# 收集测试时的配置
def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    # 为没有标记的测试添加unit标记
    for item in items:
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# 测试报告配置
def pytest_html_report_title(report):
    """自定义HTML报告标题"""
    report.title = "Paradox Mod Translator - 测试报告"


# 跳过条件
def pytest_runtest_setup(item):
    """测试运行前的设置"""
    # 如果是GUI测试且没有显示器，跳过
    if item.get_closest_marker("gui"):
        if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
            pytest.skip("需要显示器环境运行GUI测试")
    
    # 如果是API测试且没有网络连接，跳过
    if item.get_closest_marker("api"):
        # 这里可以添加网络连接检查
        pass
