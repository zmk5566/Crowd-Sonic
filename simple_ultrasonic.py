#!/usr/bin/env python3
"""
简化的UltraMic384K超声波实时可视化器
专门针对你的设备优化，去除复杂GUI，专注核心功能
"""
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from scipy import signal
import time

# 设置matplotlib使用非交互后端
plt.ion()  # 交互模式

class UltrasonicVisualizer:
    """简单的超声波可视化器"""
    
    def __init__(self):
        # UltraMic384K固定参数
        self.device = 10  # UltraMic384K设备索引
        self.sample_rate = 384000
        self.channels = 1
        self.dtype = np.int16
        self.blocksize = 7680  # 20ms @ 384kHz
        
        # 处理参数
        self.fft_size = 4096
        self.window = np.hanning(self.fft_size)
        
        # 数据缓冲
        self.audio_buffer = []
        self.spectrogram_data = []
        self.max_spectrogram_length = 200  # 保持200帧
        
        # 统计
        self.frame_count = 0
        self.start_time = time.time()
        
        print("UltraMic384K 超声波可视化器")
        print("=" * 50)
        print(f"设备: 索引{self.device} (UltraMic384K)")
        print(f"采样率: {self.sample_rate} Hz")
        print(f"格式: 16位整数")
        print(f"块大小: {self.blocksize} 样本 ({self.blocksize/self.sample_rate*1000:.1f}ms)")
        print("=" * 50)
    
    def audio_callback(self, indata, frames, time_info, status):
        """音频回调函数"""
        if status:
            print(f"音频状态: {status}")
        
        # 转换为float32
        float_data = indata.astype(np.float32) / 32768.0
        self.audio_buffer.append(float_data.copy())
        
        # 限制缓冲区大小
        if len(self.audio_buffer) > 10:
            self.audio_buffer.pop(0)
    
    def process_audio(self):
        """处理音频数据"""
        if not self.audio_buffer:
            return None, None
            
        # 获取最新数据
        latest_data = self.audio_buffer[-1].flatten()
        
        if len(latest_data) < self.fft_size:
            return None, None
            
        # FFT分析
        windowed_data = latest_data[-self.fft_size:] * self.window
        fft_result = np.fft.rfft(windowed_data)
        frequencies = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
        
        # 转换为dB
        magnitude_db = 20 * np.log10(np.abs(fft_result) + 1e-10)
        
        return frequencies, magnitude_db
    
    def update_displays(self, frequencies, magnitude):
        """更新显示"""
        if frequencies is None or magnitude is None:
            return
            
        # 添加到声谱图数据
        self.spectrogram_data.append(magnitude)
        if len(self.spectrogram_data) > self.max_spectrogram_length:
            self.spectrogram_data.pop(0)
        
        # 每3帧更新一次显示（更频繁）
        self.frame_count += 1
        if self.frame_count % 3 == 0:
            self.plot_spectrum(frequencies, magnitude)
            
    def setup_plots(self):
        """设置固定的绘图窗口"""
        plt.style.use('dark_background')
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # 设置频谱图
        self.ax1.set_xlim(0, 192)
        self.ax1.set_ylim(-80, 0)
        self.ax1.set_xlabel('频率 (kHz)', color='white')
        self.ax1.set_ylabel('幅度 (dB)', color='white')
        self.ax1.set_title('UltraMic384K 实时频谱 (0-192kHz)', color='cyan', fontsize=14)
        self.ax1.grid(True, alpha=0.3)
        self.ax1.set_facecolor('black')
        
        # 标记超声波区域
        self.ax1.axvline(20, color='red', linestyle='--', alpha=0.7, label='超声波起始 (20kHz)')
        self.ax1.legend()
        
        # 创建频谱线条对象
        self.spectrum_line, = self.ax1.plot([], [], 'cyan', linewidth=1.2, alpha=0.8)
        
        # 设置声谱图
        self.ax2.set_xlabel('时间 (秒)', color='white')
        self.ax2.set_ylabel('频率 (kHz)', color='white')
        self.ax2.set_title('超声波声谱图 (实时滚动)', color='yellow', fontsize=14)
        
        # 创建声谱图图像对象
        dummy_data = np.zeros((100, 10))
        self.spectrogram_image = self.ax2.imshow(
            dummy_data, aspect='auto', origin='lower',
            cmap='viridis', vmin=-80, vmax=-20,
            extent=[0, 10, 0, 192]
        )
        
        plt.tight_layout()
        plt.show(block=False)
        plt.draw()
    
    def plot_spectrum(self, frequencies, magnitude):
        """更新频谱显示（在固定窗口上）"""
        # 更新频谱线条
        freq_khz = frequencies / 1000
        self.spectrum_line.set_data(freq_khz, magnitude)
        
        # 更新声谱图
        if len(self.spectrogram_data) > 10:
            spectrogram_array = np.array(self.spectrogram_data).T
            self.spectrogram_image.set_array(spectrogram_array)
            
            # 更新时间轴（转换为秒）
            time_span = len(self.spectrogram_data) * 0.033  # 假设30fps更新
            self.spectrogram_image.set_extent([0, time_span, 0, 192])
            self.ax2.set_xlim(0, time_span)
        
        # 刷新显示
        plt.draw()
        plt.pause(0.001)  # 很短的暂停
        
        # 打印统计信息
        peak_idx = np.argmax(magnitude)
        peak_freq = frequencies[peak_idx]
        peak_mag = magnitude[peak_idx]
        
        # 计算超声波功率
        ultrasonic_mask = frequencies >= 20000
        if np.any(ultrasonic_mask):
            linear_mag = 10 ** (magnitude / 20)
            total_power = np.sum(linear_mag ** 2)
            ultrasonic_power = np.sum(linear_mag[ultrasonic_mask] ** 2)
            ultrasonic_ratio = ultrasonic_power / total_power if total_power > 0 else 0
        else:
            ultrasonic_ratio = 0
        
        # 计算帧率
        current_time = time.time()
        elapsed = current_time - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        
        print(f"帧 {self.frame_count:4d} | "
              f"峰值: {peak_freq/1000:6.1f}kHz ({peak_mag:5.1f}dB) | "
              f"超声波: {ultrasonic_ratio*100:5.1f}% | "
              f"FPS: {fps:4.1f}")
    
    def run(self):
        """运行可视化器"""
        print("启动音频流...")
        
        try:
            with sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=self.audio_callback
            ) as stream:
                print("✓ 音频流已启动")
                print("✓ 开始实时超声波监测...")
                print("  (按Ctrl+C停止)")
                print()
                print("实时统计:")
                print("帧数   | 峰值频率/幅度    | 超声波% | FPS")
                print("-" * 50)
                
                # 设置matplotlib固定窗口
                self.setup_plots()
                
                try:
                    while True:
                        frequencies, magnitude = self.process_audio()
                        if frequencies is not None:
                            self.update_displays(frequencies, magnitude)
                        
                        time.sleep(0.01)  # 10ms间隔，~100fps处理
                        
                except KeyboardInterrupt:
                    print(f"\n\n✓ 监测停止")
                    print(f"总帧数: {self.frame_count}")
                    elapsed = time.time() - self.start_time
                    print(f"运行时间: {elapsed:.1f}秒")
                    print(f"平均FPS: {self.frame_count/elapsed:.1f}")
                    
        except Exception as e:
            print(f"✗ 错误: {e}")
            print("请检查:")
            print("1. UltraMic384K设备是否已连接")
            print("2. 设备是否被其他程序占用")
            print("3. 设备路径是否正确 (hw:3,0)")


def main():
    """主函数"""
    visualizer = UltrasonicVisualizer()
    visualizer.run()


if __name__ == "__main__":
    main()