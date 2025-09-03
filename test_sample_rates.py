#!/usr/bin/env python3
"""
测试设备支持的采样率检测功能
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from audio_capture import AudioCapture

def test_all_devices():
    """测试所有设备支持的采样率"""
    capture = AudioCapture()
    devices = capture.list_audio_devices()
    
    print("设备采样率支持情况:")
    print("=" * 80)
    
    for device in devices:
        print(f"\n设备 {device['index']}: {device['name']}")
        print(f"默认采样率: {device['sample_rate']} Hz")
        print(f"通道数: {device['channels']}")
        print(f"音频API: {device['hostapi']}")
        
        try:
            supported_rates = capture.get_supported_sample_rates(device['index'])
            if supported_rates:
                print(f"支持的采样率: {supported_rates}")
                
                # 检查是否支持常见的高频率
                high_freq_rates = [rate for rate in supported_rates if rate >= 96000]
                if high_freq_rates:
                    print(f"  ★ 支持高频采样: {high_freq_rates}")
                    
                # 检查是否支持超高频率（超声波）
                ultrasonic_rates = [rate for rate in supported_rates if rate >= 192000]
                if ultrasonic_rates:
                    print(f"  ★★ 支持超声波频率: {ultrasonic_rates}")
                    
            else:
                print("支持的采样率: 检测失败")
                
        except Exception as e:
            print(f"检测采样率时出错: {e}")
            
        print("-" * 60)
    
    # 重点测试UAC设备
    print(f"\n重点测试UAC设备:")
    uac_device = capture.find_uac_device()
    if uac_device is not None:
        print(f"UAC设备ID: {uac_device}")
        
        device_info = capture.get_device_info(uac_device)
        print(f"设备名称: {device_info['name']}")
        
        supported_rates = capture.get_supported_sample_rates(uac_device)
        print(f"支持的采样率: {supported_rates}")
        
        # 测试不同采样率下的设置
        print(f"\n测试不同采样率的兼容性:")
        test_rates = [48000, 96000, 192000, 384000]
        
        for rate in test_rates:
            try:
                import sounddevice as sd
                sd.check_input_settings(
                    device=uac_device,
                    channels=1,
                    samplerate=rate
                )
                status = "✓ 支持"
            except:
                status = "✗ 不支持"
            
            print(f"  {rate:6d} Hz: {status}")
    else:
        print("未找到UAC设备")

if __name__ == "__main__":
    test_all_devices()