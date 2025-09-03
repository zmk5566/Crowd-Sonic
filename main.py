#!/usr/bin/env python3
"""
Simple UAC Visualizer - 主程序入口
实时超声波数据可视化工具
"""
import os
import sys
import argparse

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gui import main as gui_main
from audio_capture import AudioCapture


def list_devices():
    """列出所有可用的音频设备"""
    print("可用音频设备:")
    print("-" * 80)
    
    capture = AudioCapture()
    devices = capture.list_audio_devices()
    
    if not devices:
        print("未找到可用的音频输入设备")
        return
    
    for device in devices:
        print(f"设备 {device['index']:2d}: {device['name']}")
        print(f"           通道数: {device['channels']}")
        print(f"           采样率: {device['sample_rate']:.0f} Hz")
        print(f"           音频API: {device['hostapi']}")
        print()
    
    # 查找UAC设备
    uac_device = capture.find_uac_device()
    if uac_device is not None:
        print(f"推荐UAC设备: {uac_device}")
    else:
        print("未找到合适的UAC设备")


def test_device(device_index: int, duration: float = 5.0):
    """测试指定设备的音频捕获"""
    print(f"测试设备 {device_index}，持续 {duration} 秒...")
    
    capture = AudioCapture()
    
    try:
        if capture.start_stream(device_index):
            print("音频流已启动，正在捕获数据...")
            
            import time
            import numpy as np
            
            start_time = time.time()
            data_count = 0
            
            while time.time() - start_time < duration:
                audio_data = capture.get_audio_data()
                if audio_data is not None:
                    data_count += 1
                    rms = np.sqrt(np.mean(audio_data ** 2))
                    print(f"\r数据包 {data_count}: RMS = {rms:.6f}", end="")
                
                time.sleep(0.01)
            
            print(f"\n测试完成，共接收到 {data_count} 个数据包")
            capture.stop_stream()
            
        else:
            print("启动音频流失败")
            
    except KeyboardInterrupt:
        print("\n用户中断测试")
        capture.stop_stream()
    except Exception as e:
        print(f"\n测试出错: {e}")
        capture.stop_stream()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Simple UAC Visualizer - 实时超声波数据可视化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py                    # 启动GUI界面
  python main.py --list-devices     # 列出所有音频设备
  python main.py --test-device 1    # 测试设备1的音频捕获
  python main.py --device 1         # 使用设备1启动GUI
        """
    )
    
    parser.add_argument(
        '--list-devices', '-l',
        action='store_true',
        help='列出所有可用的音频设备'
    )
    
    parser.add_argument(
        '--test-device', '-t',
        type=int,
        help='测试指定设备的音频捕获功能'
    )
    
    parser.add_argument(
        '--device', '-d',
        type=int,
        help='指定要使用的音频设备索引'
    )
    
    parser.add_argument(
        '--sample-rate', '-s',
        type=int,
        default=384000,
        help='音频采样率 (默认: 384000 Hz)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help='测试设备时的持续时间 (默认: 5.0 秒)'
    )
    
    args = parser.parse_args()
    
    # 处理命令行参数
    if args.list_devices:
        list_devices()
        return
    
    if args.test_device is not None:
        test_device(args.test_device, args.duration)
        return
    
    # 启动GUI
    print("启动 Simple UAC Visualizer...")
    print("支持的功能:")
    print("- 实时音频流捕获 (最高384kHz)")
    print("- FFT频谱分析")
    print("- 超声波频段可视化")
    print("- 跨平台兼容 (Windows/Linux/macOS)")
    print()
    
    if args.device is not None:
        print(f"将使用设备 {args.device}")
    
    if args.sample_rate != 384000:
        print(f"采样率设置为: {args.sample_rate} Hz")
    
    try:
        gui_main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()