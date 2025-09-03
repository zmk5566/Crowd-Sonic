#!/usr/bin/env python3
"""
工作版本的UltraMic384K测试 - 使用正确参数
"""
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import time

def test_ultrasonic_recording():
    """测试UltraMic384K录制并显示频谱"""
    
    print("=" * 60)
    print("UltraMic384K 录制和分析测试")
    print("=" * 60)
    
    # UltraMic384K的正确参数
    device = "hw:3,0"
    sample_rate = 384000
    channels = 1
    dtype = np.int16  # 关键！16位整数
    duration = 2.0    # 录制2秒
    
    print(f"设备: {device}")
    print(f"采样率: {sample_rate} Hz")
    print(f"格式: 16位整数")
    print(f"时长: {duration} 秒")
    
    try:
        print(f"\n开始录制...")
        
        # 录制音频
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            device=device,
            dtype=dtype
        )
        
        sd.wait()  # 等待录制完成
        print("✓ 录制完成！")
        
        # 转换为float进行分析
        audio_float = recording.astype(np.float32) / 32768.0
        
        print(f"录制数据统计:")
        print(f"  样本数: {len(audio_float)}")
        print(f"  RMS: {np.sqrt(np.mean(audio_float**2)):.6f}")
        print(f"  峰值: {np.max(np.abs(audio_float)):.6f}")
        print(f"  动态范围: {20*np.log10(np.max(np.abs(audio_float)) + 1e-10):.1f} dB")
        
        # FFT分析
        print(f"\n进行FFT分析...")
        
        # 使用较大的窗口进行高分辨率频谱分析
        nperseg = 8192  # 8K窗口
        frequencies, times, Sxx = signal.spectrogram(
            audio_float.flatten(),
            fs=sample_rate,
            window='hann',
            nperseg=nperseg,
            noverlap=nperseg//2
        )
        
        # 转换为dB
        Sxx_dB = 10 * np.log10(Sxx + 1e-10)
        
        print(f"频谱分析结果:")
        print(f"  频率范围: 0 - {frequencies[-1]/1000:.1f} kHz")
        print(f"  时间段数: {len(times)}")
        print(f"  频率分辨率: {frequencies[1]:.1f} Hz")
        
        # 找出最强的频率成分
        avg_spectrum = np.mean(Sxx_dB, axis=1)
        peak_indices = signal.find_peaks(avg_spectrum, height=-40)[0]  # 找出-40dB以上的峰值
        
        if len(peak_indices) > 0:
            print(f"\n检测到的频率峰值:")
            for i, peak_idx in enumerate(peak_indices[:10]):  # 显示前10个峰值
                freq = frequencies[peak_idx]
                magnitude = avg_spectrum[peak_idx]
                if freq > 1000:
                    print(f"  {freq/1000:.2f} kHz: {magnitude:.1f} dB")
                else:
                    print(f"  {freq:.0f} Hz: {magnitude:.1f} dB")
        
        # 超声波频段分析
        ultrasonic_mask = frequencies >= 20000
        if np.any(ultrasonic_mask):
            ultrasonic_power = np.mean(Sxx[ultrasonic_mask])
            total_power = np.mean(Sxx)
            ultrasonic_ratio = ultrasonic_power / total_power
            print(f"\n超声波分析 (>20kHz):")
            print(f"  超声波功率比: {ultrasonic_ratio:.3f}")
            print(f"  超声波频段: {20}kHz - {frequencies[-1]/1000:.1f}kHz")
            
        return True
            
    except Exception as e:
        print(f"✗ 录制失败: {e}")
        return False

def quick_realtime_test():
    """快速实时测试"""
    print(f"\n" + "=" * 60)
    print("实时流测试")
    print("=" * 60)
    
    device = "hw:3,0"
    
    try:
        with sd.InputStream(
            device=device,
            channels=1,
            samplerate=384000,
            dtype=np.int16,
            blocksize=3840  # 10ms块
        ) as stream:
            print("实时流已启动，读取5个数据块...")
            
            for i in range(5):
                data, overflowed = stream.read(3840)
                if data is not None:
                    # 转换为float
                    float_data = data.astype(np.float32) / 32768.0
                    rms = np.sqrt(np.mean(float_data**2))
                    print(f"  块 {i+1}: RMS={rms:.6f}, 溢出={overflowed}")
                    time.sleep(0.1)
                    
        print("✓ 实时流测试成功！")
        return True
        
    except Exception as e:
        print(f"✗ 实时流测试失败: {e}")
        return False

if __name__ == "__main__":
    print("UltraMic384K 综合测试")
    print("请确保设备已连接并且没有被其他程序占用")
    print("开始自动测试...")
    
    # 测试1: 录制和分析
    success1 = test_ultrasonic_recording()
    
    if success1:
        # 测试2: 实时流
        success2 = quick_realtime_test()
        
        if success1 and success2:
            print(f"\n🎉 所有测试通过！")
            print("你的UltraMic384K设备工作正常，")
            print("现在可以集成到主程序中了。")
        else:
            print(f"\n⚠️ 部分测试失败")
    else:
        print(f"\n❌ 录制测试失败，请检查设备连接")