# **划词截图翻译助手 \- 后端服务**

## **1\. 项目概述**

本项目是一个高效、无侵入的桌面信息捕获工具的后端服务。它旨在为上层翻译应用提供稳定、精准的屏幕文本及图像源数据。其核心功能是：通过全局快捷键触发的跨屏截图，以及通过监听鼠标划选操作自动捕获屏幕上任意可选文本。

项目严格遵循非侵入式设计原则，不依赖模拟键盘输入（如模拟Ctrl+C），确保在后台运行时不会干扰用户的正常操作。

## **2\. 核心功能**

- **精准划词捕获**:
  - 静默监听用户在各类应用（浏览器、文档编辑器、IDE等）中的鼠标划选操作。
  - 仅在用户释放鼠标左键且确实存在有效文本选区时进行捕获。
  - 对于单击、取消划选等无实际选区的操作保持静默，避免无效触发。
  - 能够优雅地处理与特殊系统组件（如Windows文件管理器）的兼容性问题，防止程序崩溃。
- **跨屏截图**:
  - 用户可通过自定义的全局快捷键（默认为 Alt+Q）激活截图模式。
  - 截图模式启动后，会显示一个覆盖所有显示器的半透明蒙版。
  - 用户可拖动鼠标在任意屏幕、任意位置进行选区，选区会以红色矩形高亮显示。
  - 截图完成后，图像数据将以Base64编码格式进行回调。
- **实时数据推送**:
  - 捕获到的文本或图像数据，会通过一个统一的回调函数进行处理。
  - 项目内置一个WebSocket服务器，可将捕获到的数据实时推送给前端或其他客户端应用。

## **3\. 技术栈与实现路线**

本项目采用了一系列业界领先的Python库和技术，以实现稳定、高效、跨平台的目标。

| 功能模块 | 核心技术/库 | 实现细节与优势 |
| --- | --- | --- |
| **划词捕获 (Windows)** | **UI Automation (UIA) TextPattern** | \- 精准定位: 采用GetFocusedElement定位当前活动窗口，并结合RawViewWalker进行深度UI树遍历，以查找真实的文本选区。 \- 非侵入式: 直接与Windows辅助功能API交互，不模拟任何键盘或鼠标事件。 \- 鲁棒性: 对与文件管理器等系统组件交互时可能发生的特定COMError进行捕获和豁免处理，确保了程序的稳定性。 |
| **划词捕获 (macOS/Linux)** | pyobjc, python-xlib | 预留了对macOS和Linux平台的支持。通过调用相应系统的原生辅助功能API或查询X11选择区来实现划词捕获。 |
| **截图捕获** | mss, Pillow, tkinter | \- 高性能: mss库直接调用原生系统接口，实现极速截图。 \- 跨屏支持: 能够正确计算所有显示器组成的虚拟桌面边界，实现无缝跨屏截图。 \- 用户交互: 使用tkinter创建一个无边框的半透明窗口作为截图蒙版，并实时绘制选区矩形。 |
| **全局快捷键监听** | pynput | 跨平台的全局键盘事件监听库，用于在后台线程中稳定地监听用户按下的截图快捷键。 |
| **并发模型** | threading, queue | \- **UI/操作解耦**: 采用“生产者-消费者”模型。pynput监听线程（生产者）只负责在检测到鼠标释放时将一个轻量级任务放入队列。一个独立的划词工作线程（消费者）负责从队列中取出任务并执行耗时的UIA调用。**此架构从根本上保证了鼠标操作的流畅性，不会被划词逻辑所阻塞。** |
| **配置管理** | PyYAML | 所有关键参数，如服务器地址、端口、快捷键组合等，均通过config.yaml文件进行配置，便于修改和部署。 |
| **环境管理** | conda | 使用environment.yml文件来管理项目依赖，确保了环境的一致性和可复现性。 |

## **4\. 文件结构树**

.  
├── .vscode/  
│ ├── launch.json \# VS Code 调试启动配置  
│ └── settings.json \# VS Code 工作区设置，指定Python解释器  
├── src/  
│ ├── capture/  
│ │ ├── \_\_init\_\_.py  
│ │ ├── screenshot.py \# 截图核心逻辑  
│ │ └── text\_selection/  
│ │ ├── \_\_init\_\_.py  
│ │ ├── linux.py \# Linux 划词实现 (预留)  
│ │ ├── macos.py \# macOS 划词实现 (预留)  
│ │ └── windows.py \# Windows 划词核心实现  
│ ├── listeners/  
│ │ ├── \_\_init\_\_.py  
│ │ ├── hotkey\_listener.py \# 快捷键监听器  
│ │ └── selection\_listener.py \# 划词监听器  
│ ├── server/  
│ │ ├── \_\_init\_\_.py  
│ │ └── websocket\_server.py \# WebSocket 服务器  
│ └── config\_loader.py \# YAML 配置文件加载器  
├── tests/  
│ ├── \_\_init\_\_.py  
│ └── test\_screenshot.py \# 截图功能单元测试  
├── utils/  
│ ├── \_\_init\_\_.py  
│ └── platform\_utils.py \# 平台检测工具  
├── config.yaml \# 项目主配置文件  
├── environment.yml \# Conda 环境依赖文件  
├── main.py \# 主程序入口  
└── readme.md \# 项目说明文档

## **5\. 安装与部署**

### **5.1. 环境要求**

- Python (\>= 3.8, 推荐 3.11+)
- Conda 环境管理器

### **5.2. 安装步骤**

1. **克隆项目**:  
  git clone \<your-repository-url\>  
  cd \<project-directory\>
  
2. 创建并激活Conda环境:  
  在项目根目录下，运行以下命令。Conda会自动读取 environment.yml 文件，创建名为 selection\_translator 的虚拟环境，并安装所有必需的依赖库。  
  conda env create \-f environment.yml  
  conda activate selection\_translator
  
3. **配置VS Code解释器 (可选但推荐)**:
  
  - 打开VS Code命令面板 (Ctrl+Shift+P)。
  - 运行 Python: Select Interpreter 命令。
  - 从列表中选择包含 selection\_translator 的Conda环境。这将解决代码分析时的导入错误提示。

### **5.3. 运行程序**

在激活了 selection\_translator Conda环境的终端中，运行以下命令启动服务：

python main.py

程序启动后，将在后台持续运行。您可以通过终端日志查看实时状态和捕获到的数据。

## **6\. 配置说明**

所有配置均在 config.yaml 文件中进行修改。

\# 服务器配置  
server:  
 host: "127.0.0.1"  
 port: 8765

\# 快捷键配置 (使用 pynput.keyboard.Key 中的名称)  
hotkey:  
 screenshot: "\<alt\>+q"

\# 截图功能配置  
screenshot:  
 \# 单元测试时，截图的保存目录  
 test\_output\_dir: "tests/output"  
 \# 截图蒙版的透明度 (0.0 \- 1.0)  
 overlay\_alpha: 0.3  
 \# 选区边框的颜色  
 border\_color: "red"  
 \# 选区边框的宽度 (像素)  
 border\_width: 2

## **7\. 接口说明 (API Specification)**

本服务通过一个统一的回调函数来推送捕获到的数据。数据格式为JSON对象，具体结构如下：

### **7.1. 文本数据结构**

当捕获到划词文本时，回调函数将接收到以下格式的字典对象：

{  
 "type": "text",  
 "timestamp": "2025-10-16T12:00:00.123456Z",  
 "data": "这里是用户选中的文本内容。",  
 "metadata": {  
 "source\_app\_name": "WINWORD.EXE",  
 "source\_window\_title": "文档1 \- Microsoft Word",  
 "method": "UIA\_TextPattern\_Precise"  
 }  
}

- **type**: 数据类型，固定为 "text"。
- **timestamp**: ISO 8601格式的UTC时间戳。
- **data**: 用户划选的纯文本内容。
- **metadata**:
  - **source\_app\_name**: 来源应用程序的类名或进程名。
  - **source\_window\_title**: 来源应用程序的窗口标题。
  - **method**: 本次捕获所使用的具体技术，便于调试和分析。

### **7.2. 图像数据结构**

当完成截图时，回调函数将接收到以下格式的字典对象：

{  
 "type": "image",  
 "timestamp": "2025-10-16T12:01:05.654321Z",  
 "data": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",  
 "metadata": {  
 "format": "png",  
 "encoding": "base64",  
 "region": {  
 "x": 100,  
 "y": 150,  
 "width": 800,  
 "height": 600  
 }  
 }  
}

- **type**: 数据类型，固定为 "image"。
- **timestamp**: ISO 8601格式的UTC时间戳。
- **data**: 图像的Base64编码字符串。
- **metadata**:
  - **format**: 图像格式，当前固定为 "png"。
  - **encoding**: 编码方式，固定为 "base64"。
  - **region**: 描述截图区域在屏幕上的位置和尺寸。
    - x, y: 截图区域左上角的屏幕坐标。
    - width, height: 截图区域的宽度和高度。

## **8\. 单元测试**

项目包含对截图功能的单元测试。

运行测试:  
在激活了Conda环境的终端中，于项目根目录运行 pytest 命令：  
pytest

测试脚本会自动模拟按下截图快捷键，并验证截图文件是否成功生成在 config.yaml 中指定的 test\_output\_dir 目录下。