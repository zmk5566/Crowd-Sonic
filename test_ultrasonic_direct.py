#!/usr/bin/env python3
"""
直接测试UltraMic384K设备，使用正确的参数
"""
import sounddevice as sd
import numpy as np

def test_ultrasonic_correct_params():
    """使用设备要求的正确参数测试"""
    
    print("=" * 60)
    print("UltraMic384K 正确参数测试")
    print("=" * 60)
    print("设备要求:")
    print("  采样率: 384000 Hz")
    print("  格式: 16位整数 (S16_LE)")
    print("  通道: 1 (单声道)")
    print("=" * 60)
    
    device_name = "hw:3,0"  # 直接ALSA硬件访问
    
    try:
        # 测试1: 使用设备的确切要求
        print("测试1: 384kHz + 16bit int + 单声道")
        
        with sd.InputStream(
            device=device_name,
            channels=1,
            samplerate=384000,
            dtype=np.int16,  # 关键！使用16位整数而不是float32
            blocksize=3840,  # 10ms的数据 (384000 / 100)
        ) as stream:
            print("  ✓ 流创建成功！")
            
            # 读取一些数据验证
            for i in range(5):
                data = stream.read(3840)  # 读取10ms
                if data is not None and len(data) > 0:
                    # 转换为float计算RMS
                    float_data = data.astype(np.float32) / 32768.0  # 16bit转float
                    rms = np.sqrt(np.mean(float_data ** 2))
                    max_val = np.max(np.abs(float_data))
                    print(f"  第{i+1}次读取: RMS={rms:.6f}, 峰值={max_val:.6f}")
                else:
                    print(f"  第{i+1}次读取: 无数据")
                    
        print("  ✓ 测试完成 - 设备工作正常！")
                    
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        
    # 测试2: 验证其他参数会失败
    print(f"\n测试2: 验证其他参数确实不支持")
    
    bad_params = [
        (192000, np.int16, "192kHz + 16bit"),
        (384000, np.float32, "384kHz + float32"),
        (384000, np.int32, "384kHz + 32bit int"),
    ]
    
    for sample_rate, dtype, desc in bad_params:
        print(f"  测试 {desc}...", end="")
        try:
            sd.check_input_settings(
                device=device_name,
                channels=1,
                samplerate=sample_rate,
                dtype=dtype
            )
            print(" ✗ 意外成功（但应该失败）")
        except:
            print(" ✓ 正确失败")

if __name__ == "__main__":
    test_ultrasonic_correct_params()