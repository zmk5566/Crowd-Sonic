#!/usr/bin/env python3
"""
默认麦克风可视化器
使用与fast_ultrasonic.py相同的坐标系布局
适配普通麦克风的采样率和频率范围
"""
import sys
import numpy as np
import sounddevice as sd
from collections import deque
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import pyqtgraph as pg
from scipy.signal import get_window

class AudioThread(QThread):
    """音频采集线程"""
    audio_data_ready = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        # 使用默认输入设备
        self.device = None  # None表示使用默认设备
        self.sample_rate = 48000  # 常见的高采样率
        self.channels = 1
        self.dtype = np.int16
        self.blocksize = 480  # 10ms @ 48kHz
        self.running = False
        
    def find_device(self):
        """查找默认输入设备"""
        try:
            # 获取默认输入设备信息
            default_device = sd.query_devices(kind='input')
            print(f"使用默认输入设备: {default_device['name']}")
            print(f"最大采样率: {default_device['default_samplerate']}")
            print(f"最大输入通道: {default_device['max_input_channels']}")
            
            # 如果设备支持更高采样率，尝试使用
            if default_device['default_samplerate'] >= 44100:
                self.sample_rate = min(48000, int(default_device['default_samplerate']))
            else:
                self.sample_rate = int(default_device['default_samplerate'])
            
            self.blocksize = int(self.sample_rate * 0.01)  # 10ms
            
            print(f"实际使用采样率: {self.sample_rate} Hz")
            return None  # None表示默认设备
            
        except Exception as e:
            print(f"错误: 获取默认设备信息失败: {e}")
            # 列出所有可用输入设备
            print("可用输入设备:")
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    print(f"  {i}: {device['name']}")
            return None
        
    def run(self):
        """音频采集主循环"""
        self.running = True
        
        # 查找设备
        self.device = self.find_device()
        
        def audio_callback(indata, frames, time_info, status):
            if self.running:
                # 转换为float并归一化
                audio_float = indata.flatten().astype(np.float32) / 32768.0
                self.audio_data_ready.emit(audio_float)
        
        try:
            with sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=audio_callback
            ):
                while self.running:
                    self.msleep(1)  # 1ms睡眠
        except Exception as e:
            print(f"音频流错误: {e}")
    
    def stop(self):
        self.running = False
        self.wait()

class FastMicrophoneVisualizer(QMainWindow):
    """高性能麦克风可视化器"""
    
    def __init__(self):
        super().__init__()
        
        # 初始音频参数（会在音频线程启动后更新）
        self.sample_rate = 48000
        self.fft_size = 4096  # 适合普通音频的FFT大小
        self.overlap = 0.75
        self.window = get_window('hann', self.fft_size)
        
        # 数据缓冲区
        self.audio_buffer = deque(maxlen=self.fft_size * 2)
        self.spl_history = deque(maxlen=30)
        
        # 实际的频率轴（基于麦克风采样率）
        self.actual_freqs = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
        self.actual_freq_khz = self.actual_freqs / 1000
        
        # 扩展的频率轴（与ultrasonic相同，到200kHz）
        self.extended_freq_khz = np.linspace(0, 200, 4097)  # 与ultrasonic的频率点数保持一致
        
        # 性能统计
        self.frame_times = deque(maxlen=60)
        self.last_update = time.time()
        
        self.setup_ui()
        self.setup_audio()
        
    def setup_ui(self):
        """设置用户界面 - 使用与fast_ultrasonic.py相同的布局"""
        self.setWindowTitle("默认麦克风 高性能可视化器")
        self.setGeometry(100, 100, 1400, 900)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 状态信息
        info_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS: --")
        self.peak_label = QLabel("峰值: --")
        self.spl_label = QLabel("SPL: -- dB")
        info_layout.addWidget(self.fps_label)
        info_layout.addWidget(self.peak_label)
        info_layout.addWidget(self.spl_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 第一行：全频谱图（满行）- 使用与ultrasonic相同的200kHz坐标系
        self.spectrum_widget = pg.PlotWidget(title="实时频谱 (0-200kHz)")
        self.spectrum_widget.setLabel('left', '幅度 (dB)')
        self.spectrum_widget.setLabel('bottom', '频率 (kHz)')
        self.spectrum_widget.setXRange(0, 200)  # 与ultrasonic相同的200kHz范围
        self.spectrum_widget.setYRange(-80, 0)
        self.spectrum_curve = self.spectrum_widget.plot(pen=pg.mkPen('cyan', width=1.5))
        layout.addWidget(self.spectrum_widget)
        
        # 第二行：分频段显示 - 使用与ultrasonic相同的频段范围
        freq_bands_layout = QHBoxLayout()
        
        # 20-100kHz频段 - 与ultrasonic保持一致
        self.low_ultrasonic_widget = pg.PlotWidget(title="低频超声波 (20-100kHz)")
        self.low_ultrasonic_widget.setLabel('left', '幅度 (dB)')
        self.low_ultrasonic_widget.setLabel('bottom', '频率 (kHz)')
        self.low_ultrasonic_widget.setXRange(20, 100)
        self.low_ultrasonic_widget.setYRange(-80, 0)
        self.low_ultrasonic_curve = self.low_ultrasonic_widget.plot(pen=pg.mkPen('yellow', width=2))
        freq_bands_layout.addWidget(self.low_ultrasonic_widget)
        
        # 100-180kHz频段 - 与ultrasonic保持一致
        self.high_ultrasonic_widget = pg.PlotWidget(title="高频超声波 (100-180kHz)")
        self.high_ultrasonic_widget.setLabel('left', '幅度 (dB)')
        self.high_ultrasonic_widget.setLabel('bottom', '频率 (kHz)')
        self.high_ultrasonic_widget.setXRange(100, 180)
        self.high_ultrasonic_widget.setYRange(-80, 0)
        self.high_ultrasonic_curve = self.high_ultrasonic_widget.plot(pen=pg.mkPen('orange', width=2))
        freq_bands_layout.addWidget(self.high_ultrasonic_widget)
        
        layout.addLayout(freq_bands_layout)
        
        # 第三行：瀑布图（满行）- 保持相同的布局和结构
        waterfall_layout = QHBoxLayout()
        
        # 瀑布图
        self.waterfall_widget = pg.PlotWidget(title="频谱瀑布图")
        self.waterfall_widget.setLabel('left', '频率 (kHz)')     # Y轴是频率
        self.waterfall_widget.setLabel('bottom', '时间 (新→老)') # X轴是时间
        
        # 初始化瀑布图数据 (时间 x 频率) - 使用扩展频率轴
        self.waterfall_data = np.zeros((200, len(self.extended_freq_khz)))  # 时间x频率
        self.waterfall_img = pg.ImageItem(self.waterfall_data)
        self.waterfall_widget.addItem(self.waterfall_img)
        
        # 设置频率轴范围 - 与ultrasonic相同的200kHz
        self.waterfall_widget.setXRange(0, 200)
        
        # 设置颜色映射
        colormap = pg.colormap.get('viridis')
        self.waterfall_img.setColorMap(colormap)
        
        # 设置图像位置和比例 (频率x时间) - 使用200kHz范围
        self.waterfall_img.setRect(pg.QtCore.QRectF(0, 0, 200, 200))  # x,y,width,height
        
        waterfall_layout.addWidget(self.waterfall_widget)
        
        layout.addLayout(waterfall_layout)
        
    def setup_audio(self):
        """设置音频采集"""
        self.audio_thread = AudioThread()
        
        # 等待线程初始化设备信息
        self.audio_thread.find_device()
        
        # 更新采样率相关参数
        self.sample_rate = self.audio_thread.sample_rate
        self.actual_freqs = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
        self.actual_freq_khz = self.actual_freqs / 1000
        
        # 保持200kHz的扩展频率轴不变
        # self.extended_freq_khz 已经在__init__中定义为0-200kHz
        
        # 更新瀑布图数据结构
        self.waterfall_data = np.zeros((200, len(self.extended_freq_khz)))
        self.waterfall_img.setImage(self.waterfall_data)
        
        # 启动音频线程
        self.audio_thread.audio_data_ready.connect(self.process_audio)
        self.audio_thread.start()
        
        print("默认麦克风 高性能可视化器")
        print("=" * 50)
        print(f"采样率: {self.sample_rate} Hz")
        print(f"FFT大小: {self.fft_size}")
        print(f"频率分辨率: {self.sample_rate/self.fft_size:.2f} Hz")
        print(f"Nyquist频率: {self.sample_rate/2/1000:.1f} kHz")
        print(f"实际频率范围: 0 - {self.actual_freq_khz[-1]:.1f} kHz")
        print(f"显示频率范围: 0 - 200.0 kHz (与ultrasonic相同)")
        print(f"实际频率点数: {len(self.actual_freq_khz)}")
        print(f"显示频率点数: {len(self.extended_freq_khz)}")
        print("=" * 50)
        
    def process_audio(self, audio_data):
        """处理音频数据 - 使用与fast_ultrasonic.py相同的处理流程"""
        # 添加到缓冲区
        self.audio_buffer.extend(audio_data)
        
        # 检查是否有足够数据进行FFT
        if len(self.audio_buffer) >= self.fft_size:
            # 获取最新的FFT大小的数据
            data = np.array(list(self.audio_buffer)[-self.fft_size:])
            
            # 应用窗函数
            windowed_data = data * self.window
            
            # FFT
            fft_result = np.fft.rfft(windowed_data)
            
            # 正确的FFT缩放和功率谱计算
            magnitude = np.abs(fft_result) / self.fft_size  # FFT归一化
            
            # Hann窗能量补偿（约1.5倍）
            magnitude *= 2.0
            
            # 计算功率谱密度
            power_spectrum = magnitude ** 2
            
            # 转换为dB（功率用10*log10，幅度用20*log10）
            magnitude_db = 10 * np.log10(np.maximum(power_spectrum, 1e-20))
            
            # 更新显示
            self.update_displays(magnitude_db, data, magnitude)
            
            # 更新FPS
            self.update_fps()
    
    def calculate_spl(self, audio_data):
        """计算声压级 (SPL) - 与fast_ultrasonic.py相同的算法"""
        # 计算RMS值
        rms = np.sqrt(np.mean(audio_data**2))
        
        # 转换为dB SPL
        if rms > 0:
            spl_db = 20 * np.log10(rms) + 94  # 94dB是一个常用的参考偏移
        else:
            spl_db = 0
        
        return max(0, spl_db)  # 确保不为负值
    
    def update_displays(self, magnitude_db, audio_data, magnitude):
        """更新所有显示 - 扩展到200kHz坐标系"""
        # 创建扩展的幅度数据，将实际数据映射到200kHz坐标系
        extended_magnitude_db = np.full(len(self.extended_freq_khz), -100.0)  # 默认值-100dB，确保无数据区域完全平坦
        
        # 将实际数据插值到扩展的频率轴上
        # 只在有效频率范围内插值
        valid_mask = self.extended_freq_khz <= self.actual_freq_khz[-1]
        if np.any(valid_mask):
            extended_magnitude_db[valid_mask] = np.interp(
                self.extended_freq_khz[valid_mask],
                self.actual_freq_khz,
                magnitude_db
            )
        
        # 更新全频谱曲线 - 使用扩展数据
        self.spectrum_curve.setData(self.extended_freq_khz, extended_magnitude_db)
        
        # 更新低频超声波频段 (20-100kHz) - 与ultrasonic保持一致
        low_mask = (self.extended_freq_khz >= 20) & (self.extended_freq_khz <= 100)
        self.low_ultrasonic_curve.setData(
            self.extended_freq_khz[low_mask], 
            extended_magnitude_db[low_mask]
        )
        
        # 更新高频超声波频段 (100-180kHz) - 与ultrasonic保持一致
        high_mask = (self.extended_freq_khz >= 100) & (self.extended_freq_khz <= 180)
        self.high_ultrasonic_curve.setData(
            self.extended_freq_khz[high_mask], 
            extended_magnitude_db[high_mask]
        )
        
        # 更新瀑布图 - 使用扩展数据
        self.waterfall_data[1:, :] = self.waterfall_data[:-1, :]  # 老数据向上滚动
        self.waterfall_data[0, :] = extended_magnitude_db  # 新数据在底部
        
        # 设置图像数据
        self.waterfall_img.setImage(self.waterfall_data, autoLevels=False, levels=[-80, 0])
        
        # 计算并更新SPL
        spl = self.calculate_spl(audio_data)
        self.spl_history.append(spl)
        
        # 平滑的SPL值
        if self.spl_history:
            avg_spl = np.mean(list(self.spl_history))
            self.spl_label.setText(f"SPL: {avg_spl:.1f} dB")
        
        # 更新峰值信息 - 基于实际数据
        peak_freq_idx = np.argmax(magnitude_db)
        peak_freq = self.actual_freq_khz[peak_freq_idx]
        peak_magnitude = magnitude_db[peak_freq_idx]
        self.peak_label.setText(f"峰值: {peak_freq:.1f}kHz ({peak_magnitude:.1f}dB)")
        
    def update_fps(self):
        """更新FPS显示 - 与fast_ultrasonic.py相同的FPS计算"""
        current_time = time.time()
        self.frame_times.append(current_time)
        
        if len(self.frame_times) > 1:
            fps = len(self.frame_times) / (self.frame_times[-1] - self.frame_times[0])
            self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if hasattr(self, 'audio_thread'):
            self.audio_thread.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    visualizer = FastMicrophoneVisualizer()
    visualizer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()