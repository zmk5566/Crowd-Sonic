#!/usr/bin/env python3
"""
高性能UltraMic384K超声波可视化器
使用PyQt + pyqtgraph实现高帧率实时渲染
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
        # 可以通过多个名字匹配设备
        self.device_names = ["UltraMic384K", "UltraMic", "384K"]  
        self.fallback_device_id = 10  # 如果名字匹配失败，使用这个索引
        self.device = None  # 将在find_device中设置
        self.sample_rate = 384000
        self.channels = 1
        self.dtype = np.int16
        self.blocksize = 3840  # 10ms @ 384kHz - 更小的块提高响应速度
        self.running = False
        
    def find_device(self):
        """通过名字查找UltraMic384K设备，支持回退机制"""
        devices = sd.query_devices()
        
        # 首先尝试通过名字匹配
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                for name in self.device_names:
                    if name in device['name']:
                        print(f"找到设备: {i} - {device['name']} (通过名字 '{name}')")
                        return i
        
        # 如果名字匹配失败，尝试回退设备
        if self.fallback_device_id < len(devices):
            device = devices[self.fallback_device_id]
            if device['max_input_channels'] > 0:
                print(f"使用回退设备: {self.fallback_device_id} - {device['name']}")
                return self.fallback_device_id
        
        print(f"错误: 未找到匹配的设备")
        print("尝试匹配的名字:", self.device_names)
        print(f"回退设备索引: {self.fallback_device_id}")
        print("可用输入设备:")
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"  {i}: {device['name']}")
        return None
        
    def run(self):
        """音频采集主循环"""
        self.running = True
        
        # 查找设备
        self.device = self.find_device()
        if self.device is None:
            return
        
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

class FastUltrasonicVisualizer(QMainWindow):
    """高性能超声波可视化器"""
    
    def __init__(self):
        super().__init__()
        
        # 音频参数
        self.sample_rate = 384000
        self.fft_size = 8192  # 增大FFT提高频率分辨率
        self.overlap = 0.75   # 增加重叠提高时间分辨率
        self.window = get_window('hann', self.fft_size)
        
        # 数据缓冲区
        self.audio_buffer = deque(maxlen=self.fft_size * 2)
        self.spl_history = deque(maxlen=30)  # SPL历史用于平滑
        
        # 频率轴
        self.freqs = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
        self.freq_khz = self.freqs / 1000
        
        # 性能统计
        self.frame_times = deque(maxlen=60)
        self.last_update = time.time()
        
        self.setup_ui()
        self.setup_audio()
        
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("UltraMic384K 高性能超声波可视化器")
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
        
        # 第一行：全频谱图（满行）
        self.spectrum_widget = pg.PlotWidget(title="实时频谱 (0-192kHz)")
        self.spectrum_widget.setLabel('left', '幅度 (dB)')
        self.spectrum_widget.setLabel('bottom', '频率 (kHz)')
        self.spectrum_widget.setXRange(0, 192)
        self.spectrum_widget.setYRange(-80, 0)
        self.spectrum_curve = self.spectrum_widget.plot(pen=pg.mkPen('cyan', width=1.5))
        layout.addWidget(self.spectrum_widget)
        
        # 第二行：分频段显示
        freq_bands_layout = QHBoxLayout()
        
        # 20-100kHz频段
        self.low_ultrasonic_widget = pg.PlotWidget(title="低频超声波 (20-100kHz)")
        self.low_ultrasonic_widget.setLabel('left', '幅度 (dB)')
        self.low_ultrasonic_widget.setLabel('bottom', '频率 (kHz)')
        self.low_ultrasonic_widget.setXRange(20, 100)
        self.low_ultrasonic_widget.setYRange(-80, 0)
        self.low_ultrasonic_curve = self.low_ultrasonic_widget.plot(pen=pg.mkPen('yellow', width=2))
        freq_bands_layout.addWidget(self.low_ultrasonic_widget)
        
        # 100-180kHz频段
        self.high_ultrasonic_widget = pg.PlotWidget(title="高频超声波 (100-180kHz)")
        self.high_ultrasonic_widget.setLabel('left', '幅度 (dB)')
        self.high_ultrasonic_widget.setLabel('bottom', '频率 (kHz)')
        self.high_ultrasonic_widget.setXRange(100, 180)
        self.high_ultrasonic_widget.setYRange(-80, 0)
        self.high_ultrasonic_curve = self.high_ultrasonic_widget.plot(pen=pg.mkPen('orange', width=2))
        freq_bands_layout.addWidget(self.high_ultrasonic_widget)
        
        layout.addLayout(freq_bands_layout)
        
        # 第三行：瀑布图（满行）
        # 创建瀑布图布局，包含图和颜色条
        waterfall_layout = QHBoxLayout()
        
        # 瀑布图
        self.waterfall_widget = pg.PlotWidget(title="频谱瀑布图")
        self.waterfall_widget.setLabel('left', '频率 (kHz)')     # Y轴是频率
        self.waterfall_widget.setLabel('bottom', '时间 (新→老)') # X轴是时间
        
        # 初始化瀑布图数据 (时间 x 频率)
        self.waterfall_data = np.zeros((200, len(self.freq_khz)))  # 时间x频率
        self.waterfall_img = pg.ImageItem(self.waterfall_data)  # 先设置数据
        self.waterfall_widget.addItem(self.waterfall_img)
        
        # 设置频率轴范围
        self.waterfall_widget.setXRange(0, 192)
        
        # 设置颜色映射
        colormap = pg.colormap.get('viridis')
        self.waterfall_img.setColorMap(colormap)
        
        # 设置图像位置和比例 (频率x时间)
        self.waterfall_img.setRect(pg.QtCore.QRectF(0, 0, 192, 200))  # x,y,width,height
        
        waterfall_layout.addWidget(self.waterfall_widget)
        
        # TODO: 添加颜色条
        
        layout.addLayout(waterfall_layout)
        
    def setup_audio(self):
        """设置音频采集"""
        self.audio_thread = AudioThread()
        self.audio_thread.audio_data_ready.connect(self.process_audio)
        self.audio_thread.start()
        
        print("UltraMic384K 高性能超声波可视化器")
        print("=" * 50)
        print(f"目标设备: {' 或 '.join(self.audio_thread.device_names)}")
        print(f"采样率: {self.sample_rate} Hz")
        print(f"FFT大小: {self.fft_size}")
        print(f"频率分辨率: {self.sample_rate/self.fft_size:.2f} Hz")
        print(f"Nyquist频率: {self.sample_rate/2/1000:.1f} kHz")
        print(f"频率范围: 0 - {self.freq_khz[-1]:.1f} kHz")
        print(f"频率点数: {len(self.freq_khz)}")
        print("=" * 50)
        
    def process_audio(self, audio_data):
        """处理音频数据"""
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
        """计算声压级 (SPL)"""
        # 计算RMS值
        rms = np.sqrt(np.mean(audio_data**2))
        
        # 转换为dB SPL (参考值设为满量程的某个比例)
        # 对于16bit音频，满量程为1.0 (归一化后)
        # 这里使用一个简化的转换公式
        if rms > 0:
            spl_db = 20 * np.log10(rms) + 94  # 94dB是一个常用的参考偏移
        else:
            spl_db = 0
        
        return max(0, spl_db)  # 确保不为负值
    
    def update_displays(self, magnitude_db, audio_data, magnitude):
        """更新所有显示"""
        # 更新全频谱曲线
        self.spectrum_curve.setData(self.freq_khz, magnitude_db)
        
        # 更新低频超声波频段 (20-100kHz)
        low_mask = (self.freq_khz >= 20) & (self.freq_khz <= 100)
        self.low_ultrasonic_curve.setData(
            self.freq_khz[low_mask], 
            magnitude_db[low_mask]
        )
        
        # 更新高频超声波频段 (100-180kHz)
        high_mask = (self.freq_khz >= 100) & (self.freq_khz <= 180)
        self.high_ultrasonic_curve.setData(
            self.freq_khz[high_mask], 
            magnitude_db[high_mask]
        )
        
        # 更新瀑布图 (时间在Y轴，频率在X轴)
        # 标准瀑布图：下面是现在，上面是过去
        self.waterfall_data[1:, :] = self.waterfall_data[:-1, :]  # 老数据向上滚动
        self.waterfall_data[0, :] = magnitude_db  # 新数据在底部
        
        # 设置图像数据
        self.waterfall_img.setImage(self.waterfall_data, autoLevels=False, levels=[-80, 0])
        
        # 计算并更新SPL
        spl = self.calculate_spl(audio_data)
        self.spl_history.append(spl)
        
        # 平滑的SPL值
        if self.spl_history:
            avg_spl = np.mean(list(self.spl_history))
            self.spl_label.setText(f"SPL: {avg_spl:.1f} dB")
        
        # 更新峰值信息
        peak_freq_idx = np.argmax(magnitude_db)
        peak_freq = self.freq_khz[peak_freq_idx]
        peak_magnitude = magnitude_db[peak_freq_idx]
        self.peak_label.setText(f"峰值: {peak_freq:.1f}kHz ({peak_magnitude:.1f}dB)")
        
    def update_fps(self):
        """更新FPS显示"""
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
    
    visualizer = FastUltrasonicVisualizer()
    visualizer.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()