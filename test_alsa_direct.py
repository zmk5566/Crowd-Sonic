#!/usr/bin/env python3
"""
测试ALSA直接硬件访问，模仿Audacity的行为
"""
import sounddevice as sd
import numpy as np
import sys

def test_alsa_direct_access():
    """测试ALSA直接访问你的UAC设备"""
    
    print("=" * 60)
    print("ALSA 直接硬件访问测试")
    print("=" * 60)
    
    # 查找你的UltraMic设备
    devices = sd.query_devices()
    ultrasonic_device = None
    
    for i, device in enumerate(devices):
        if 'ultrasonic' in device['name'].lower() or 'ultram' in device['name'].lower() or '384' in device['name']:
            ultrasonic_device = i
            print(f"找到UltraMic设备: {i} - {device['name']}")
            break
    
    # 如果没找到，手动指定
    if ultrasonic_device is None:
        print("\n没有自动找到UltraMic设备，让我们列出所有设备:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"设备 {i}: {device['name']} (channels: {device['max_input_channels']})")
        
        # 尝试使用硬件设备名称
        test_devices = [
            'hw:3,0',  # 直接ALSA硬件访问
            'plughw:3,0',  # 带插件的ALSA访问
            10,  # 设备索引
        ]
    else:
        test_devices = [ultrasonic_device]
    
    for device_id in test_devices:
        print(f"\n测试设备: {device_id}")
        
        # 测试不同采样率
        sample_rates = [384000, 192000, 96000, 48000]
        
        for sr in sample_rates:
            try:
                print(f"  测试 {sr} Hz...", end="")
                
                # 尝试直接创建流
                with sd.InputStream(
                    device=device_id,
                    channels=1,
                    samplerate=sr,
                    dtype=np.float32,
                    blocksize=1024
                ) as stream:
                    # 读取一小段数据确认工作
                    data = stream.read(100)
                    if data is not None:
                        rms = np.sqrt(np.mean(data ** 2))
                        print(f" ✓ 成功 (RMS: {rms:.6f})")
                    else:
                        print(" ✗ 数据为空")
                        
            except Exception as e:
                print(f" ✗ 失败: {str(e)[:50]}")
                
    # 测试使用ALSA设备名
    print(f"\n测试ALSA硬件设备名:")
    alsa_devices = [
        'hw:3,0',      # 直接硬件访问
        'plughw:3,0',  # 带自动转换
        'hw:1,0',      # Steinberg设备
        'hw:0,0',      # 内置设备
    ]
    
    for alsa_dev in alsa_devices:
        print(f"\n测试ALSA设备: {alsa_dev}")
        try:
            # 查询设备信息
            device_info = sd.query_devices(alsa_dev)
            print(f"  设备名称: {device_info['name']}")
            print(f"  默认采样率: {device_info['default_samplerate']}")
            print(f"  最大输入通道: {device_info['max_input_channels']}")
            
            # 测试384kHz
            try:
                with sd.InputStream(
                    device=alsa_dev,
                    channels=1, 
                    samplerate=384000,
                    dtype=np.float32,
                    blocksize=512
                ) as stream:
                    data = stream.read(100)
                    rms = np.sqrt(np.mean(data ** 2))
                    print(f"  384kHz测试: ✓ 成功 (RMS: {rms:.6f})")
            except Exception as e:
                print(f"  384kHz测试: ✗ 失败: {e}")
                
        except Exception as e:
            print(f"  设备访问失败: {e}")

def check_alsa_info():
    """检查ALSA系统信息"""
    print(f"\n" + "=" * 60)
    print("ALSA 系统信息")
    print("=" * 60)
    
    try:
        import subprocess
        
        # 显示ALSA版本
        try:
            result = subprocess.run(['cat', '/proc/asound/version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"ALSA版本: {result.stdout.strip()}")
        except:
            pass
        
        # 显示声卡列表
        try:
            result = subprocess.run(['cat', '/proc/asound/cards'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\n声卡列表:")
                print(result.stdout)
        except:
            pass
            
        # 显示PCM设备
        try:
            result = subprocess.run(['aplay', '-l'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"PCM播放设备:")
                print(result.stdout)
        except:
            pass
            
        try:
            result = subprocess.run(['arecord', '-l'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"PCM录制设备:")
                print(result.stdout)
        except:
            pass
            
    except Exception as e:
        print(f"获取ALSA信息失败: {e}")

if __name__ == "__main__":
    test_alsa_direct_access()
    check_alsa_info()