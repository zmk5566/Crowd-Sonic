#!/usr/bin/env python3
"""
性能基准测试
测试实时音频处理的性能表现
"""
import time
import numpy as np
import sys
import os
import statistics

# 添加src路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from signal_processor import SignalProcessor
from audio_capture import AudioCapture


def benchmark_fft_processing():
    """基准测试FFT处理性能"""
    print("FFT处理性能测试")
    print("-" * 50)
    
    processor = SignalProcessor()
    sample_rate = processor.sample_rate
    fft_size = processor.fft_size
    
    # 生成测试信号
    duration = 0.1
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = (np.sin(2 * np.pi * 1000 * t) +
                  0.5 * np.sin(2 * np.pi * 25000 * t) +
                  0.3 * np.sin(2 * np.pi * 50000 * t))
    
    # 性能测试
    num_iterations = 1000
    processing_times = []
    
    print(f"处理 {num_iterations} 次，每次 {fft_size} 个样本...")
    
    for i in range(num_iterations):
        start_time = time.perf_counter()
        frequencies, magnitude = processor.process_audio_chunk(test_signal[:fft_size])
        end_time = time.perf_counter()
        
        processing_times.append((end_time - start_time) * 1000)  # 转换为毫秒
        
        if (i + 1) % 100 == 0:
            print(f"完成 {i + 1} 次处理...")
    
    # 统计结果
    avg_time = statistics.mean(processing_times)
    min_time = min(processing_times)
    max_time = max(processing_times)
    std_time = statistics.stdev(processing_times)
    
    print(f"\nFFT处理性能结果:")
    print(f"  平均处理时间: {avg_time:.3f} ms")
    print(f"  最小处理时间: {min_time:.3f} ms")
    print(f"  最大处理时间: {max_time:.3f} ms")
    print(f"  标准差: {std_time:.3f} ms")
    
    # 计算实时性能指标
    buffer_duration = fft_size / sample_rate * 1000  # 缓冲区时长（毫秒）
    real_time_ratio = avg_time / buffer_duration
    
    print(f"  缓冲区时长: {buffer_duration:.3f} ms")
    print(f"  实时比率: {real_time_ratio:.3f} (< 1.0 为实时)")
    
    if real_time_ratio < 0.5:
        print("  性能评级: 优秀 ✓")
    elif real_time_ratio < 1.0:
        print("  性能评级: 良好 ✓")
    else:
        print("  性能评级: 需要优化 ⚠️")
    
    return avg_time, real_time_ratio


def benchmark_overlapped_processing():
    """基准测试重叠处理性能"""
    print("\n重叠处理性能测试")
    print("-" * 50)
    
    processor = SignalProcessor()
    sample_rate = processor.sample_rate
    hop_size = processor.hop_size
    
    # 生成长测试信号
    duration = 5.0  # 5秒
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 10000 * t) + 0.3 * np.random.randn(len(t))
    
    print(f"处理 {duration} 秒音频数据，hop size = {hop_size}")
    
    start_time = time.perf_counter()
    processed_frames = 0
    
    # 模拟实时处理
    for i in range(0, len(test_signal) - hop_size, hop_size):
        chunk = test_signal[i:i + hop_size]
        result = processor.process_overlapped_chunk(chunk)
        if result is not None:
            processed_frames += 1
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    
    print(f"  总处理时间: {total_time:.3f} 秒")
    print(f"  处理帧数: {processed_frames}")
    print(f"  平均每帧时间: {total_time/processed_frames*1000:.3f} ms")
    print(f"  实时比率: {total_time/duration:.3f}")
    
    if total_time < duration:
        print("  实时处理: 成功 ✓")
    else:
        print("  实时处理: 失败 ⚠️")


def benchmark_spectrum_features():
    """基准测试频谱特征计算性能"""
    print("\n频谱特征计算性能测试")
    print("-" * 50)
    
    processor = SignalProcessor()
    sample_rate = processor.sample_rate
    fft_size = processor.fft_size
    
    # 生成测试信号
    t = np.linspace(0, fft_size/sample_rate, fft_size)
    test_signal = (np.sin(2 * np.pi * 5000 * t) +
                  0.5 * np.sin(2 * np.pi * 30000 * t))
    
    # 获取频谱
    frequencies, magnitude = processor.process_audio_chunk(test_signal)
    
    # 测试特征计算性能
    num_iterations = 10000
    feature_times = []
    
    print(f"计算频谱特征 {num_iterations} 次...")
    
    for i in range(num_iterations):
        start_time = time.perf_counter()
        features = processor.calculate_spectrum_features(frequencies, magnitude)
        end_time = time.perf_counter()
        
        feature_times.append((end_time - start_time) * 1000)
        
        if (i + 1) % 1000 == 0:
            print(f"完成 {i + 1} 次计算...")
    
    avg_time = statistics.mean(feature_times)
    print(f"  平均特征计算时间: {avg_time:.4f} ms")
    
    # 测试频段分析性能
    band_times = []
    
    print(f"计算频段分析 {num_iterations} 次...")
    
    for i in range(num_iterations):
        start_time = time.perf_counter()
        bands = processor.get_frequency_bands(frequencies, magnitude)
        end_time = time.perf_counter()
        
        band_times.append((end_time - start_time) * 1000)
    
    avg_band_time = statistics.mean(band_times)
    print(f"  平均频段分析时间: {avg_band_time:.4f} ms")


def test_memory_usage():
    """测试内存使用情况"""
    print("\n内存使用测试")
    print("-" * 50)
    
    try:
        import psutil
        process = psutil.Process()
        
        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        print(f"初始内存使用: {initial_memory:.2f} MB")
        
        # 创建组件
        processor = SignalProcessor()
        capture = AudioCapture()
        
        component_memory = process.memory_info().rss / 1024 / 1024
        print(f"组件初始化后: {component_memory:.2f} MB")
        
        # 模拟长时间运行
        sample_rate = processor.sample_rate
        test_duration = 10.0  # 10秒数据
        t = np.linspace(0, test_duration, int(sample_rate * test_duration))
        test_signal = np.sin(2 * np.pi * 1000 * t)
        
        # 分块处理
        hop_size = processor.hop_size
        for i in range(0, len(test_signal) - hop_size, hop_size):
            chunk = test_signal[i:i + hop_size]
            result = processor.process_overlapped_chunk(chunk)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        print(f"处理完成后: {final_memory:.2f} MB")
        print(f"内存增长: {final_memory - initial_memory:.2f} MB")
        
        if final_memory - initial_memory < 10:
            print("内存使用: 良好 ✓")
        else:
            print("内存使用: 需要优化 ⚠️")
            
    except ImportError:
        print("psutil 未安装，跳过内存测试")


def main():
    """主函数"""
    print("Simple UAC Visualizer 性能基准测试")
    print("=" * 50)
    
    # CPU信息
    try:
        import platform
        print(f"系统: {platform.system()} {platform.release()}")
        print(f"处理器: {platform.processor()}")
        print(f"Python版本: {sys.version}")
        print()
    except:
        pass
    
    # 运行各项测试
    try:
        fft_time, real_time_ratio = benchmark_fft_processing()
        benchmark_overlapped_processing()
        benchmark_spectrum_features()
        test_memory_usage()
        
        print("\n" + "=" * 50)
        print("性能测试总结:")
        print(f"FFT处理平均时间: {fft_time:.3f} ms")
        print(f"实时处理能力: {'是' if real_time_ratio < 1.0 else '否'}")
        
        if real_time_ratio < 0.5:
            print("总体性能评级: 优秀，可支持高负载实时处理 ✓")
        elif real_time_ratio < 1.0:
            print("总体性能评级: 良好，可支持实时处理 ✓")
        else:
            print("总体性能评级: 需要优化以支持实时处理 ⚠️")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")


if __name__ == "__main__":
    main()