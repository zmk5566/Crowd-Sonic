#!/usr/bin/env python3
"""
专门的UltraMic384K超声波实时可视化器
针对384kHz采样率和16位整数格式优化
"""
import sys
import numpy as np
import sounddevice as sd
from scipy import signal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QPushButton, QLabel, QGroupBox, QGridLayout,
                            QStatusBar, QSlider, QSpinBox, QCheckBox)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.style as mplstyle
import threading
import queue
import time

# 使用快速绘制样式
mplstyle.use('fast')


class UltrasonicCaptureThread(threading.Thread):
    """UltraMic384K专用音频捕获线程"""
    
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        self.data_queue = queue.Queue(maxsize=10)  # 限制队列大小避免内存堆积
        
        # UltraMic384K 固定参数
        self.device = "hw:3,0"
        self.sample_rate = 384000
        self.channels = 1
        self.dtype = np.int16
        self.blocksize = 3840  # 10ms @ 384kHz
        
        self.stream = None
        
    def start_capture(self):
        """开始捕获"""
        try:
            self.stream = sd.InputStream(
                device=self.device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.blocksize,
                callback=self._audio_callback
            )
            self.stream.start()
            self.running = True
            self.start()
            return True
        except Exception as e:
            print(f"启动音频捕获失败: {e}")
            return False
    
    def stop_capture(self):
        """停止捕获"""
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
    
    def _audio_callback(self, indata, frames, time, status):
        """音频回调函数"""
        if status:
            print(f"音频状态: {status}")
            
        # 转换为float32进行处理
        float_data = indata.astype(np.float32) / 32768.0
        
        try:
            self.data_queue.put_nowait(float_data.copy())
        except queue.Full:
            # 队列满时丢弃最旧的数据
            try:
                self.data_queue.get_nowait()
                self.data_queue.put_nowait(float_data.copy())
            except queue.Empty:
                pass
    
    def get_data(self):
        """获取音频数据"""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None
    
    def run(self):
        """线程运行"""
        while self.running:
            threading.Event().wait(0.001)  # 1ms间隔


class UltrasonicSpectrumWidget(FigureCanvas):
    """超声波频谱显示组件"""
    
    def __init__(self, parent=None):
        self.figure = Figure(facecolor='black', figsize=(14, 10))
        super().__init__(self.figure)
        self.setParent(parent)
        
        # 创建三个子图
        self.time_ax = self.figure.add_subplot(311)      # 时域波形
        self.spectrum_ax = self.figure.add_subplot(312)   # 频谱
        self.spectrogram_ax = self.figure.add_subplot(313) # 声谱图
        
        self._setup_plots()
        
        # 数据缓冲
        self.spectrogram_data = []
        self.max_spectrogram_length = 300  # 5分钟@60fps
        self.time_buffer = []
        self.max_time_length = 3840 * 10  # 100ms的时域数据
        
        # 处理参数
        self.sample_rate = 384000
        self.fft_size = 4096  # 高分辨率FFT
        self.window = np.hanning(self.fft_size)
        
    def _setup_plots(self):
        """设置绘图样式"""
        # 时域波形
        self.time_ax.set_facecolor('black')
        self.time_ax.set_ylabel('振幅', color='white')
        self.time_ax.set_title('UltraMic384K 时域波形 (最近100ms)', color='white', fontsize=12)
        self.time_ax.tick_params(colors='white')
        self.time_ax.grid(True, alpha=0.3, color='white')
        
        # 频谱图
        self.spectrum_ax.set_facecolor('black')
        self.spectrum_ax.set_xlabel('频率 (kHz)', color='white')
        self.spectrum_ax.set_ylabel('幅度 (dB)', color='white')
        self.spectrum_ax.set_title('实时频谱 (0-192kHz)', color='white', fontsize=12)
        self.spectrum_ax.tick_params(colors='white')
        self.spectrum_ax.grid(True, alpha=0.3, color='white')
        self.spectrum_ax.set_xlim(0, 192)
        self.spectrum_ax.set_ylim(-80, 0)
        
        # 声谱图
        self.spectrogram_ax.set_facecolor('black')
        self.spectrogram_ax.set_xlabel('时间', color='white')
        self.spectrogram_ax.set_ylabel('频率 (kHz)', color='white')
        self.spectrogram_ax.set_title('超声波声谱图 (实时滚动)', color='white', fontsize=12)
        self.spectrogram_ax.tick_params(colors='white')
        
        # 初始化绘图线条
        self.time_line, = self.time_ax.plot([], [], 'cyan', linewidth=0.8)
        self.spectrum_line, = self.spectrum_ax.plot([], [], 'yellow', linewidth=1.0)
        
        # 声谱图图像对象
        dummy_data = np.zeros((100, 10))
        self.spectrogram_image = self.spectrogram_ax.imshow(
            dummy_data, aspect='auto', origin='lower',
            cmap='viridis', vmin=-80, vmax=-20,
            extent=[0, 10, 0, 192]
        )
        
        self.figure.tight_layout()
    
    def update_displays(self, audio_data):
        """更新所有显示"""
        if audio_data is None or len(audio_data) == 0:
            return
            
        # 1. 更新时域显示
        self.time_buffer.extend(audio_data.flatten())
        if len(self.time_buffer) > self.max_time_length:
            self.time_buffer = self.time_buffer[-self.max_time_length:]
            
        if len(self.time_buffer) > 100:
            time_axis = np.arange(len(self.time_buffer)) / self.sample_rate * 1000  # 转为ms
            self.time_line.set_data(time_axis, self.time_buffer)
            self.time_ax.set_xlim(time_axis[0], time_axis[-1])
            self.time_ax.set_ylim(-0.1, 0.1)
        
        # 2. FFT频谱分析
        if len(audio_data) >= self.fft_size:
            # 使用最新的数据进行FFT
            fft_data = audio_data.flatten()[-self.fft_size:] * self.window
            fft_result = np.fft.rfft(fft_data)
            frequencies = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
            
            # 转换为dB
            magnitude_db = 20 * np.log10(np.abs(fft_result) + 1e-10)
            
            # 更新频谱显示
            freq_khz = frequencies / 1000
            self.spectrum_line.set_data(freq_khz, magnitude_db)
            
            # 3. 更新声谱图
            self.spectrogram_data.append(magnitude_db)
            if len(self.spectrogram_data) > self.max_spectrogram_length:
                self.spectrogram_data.pop(0)
                
            if len(self.spectrogram_data) > 10:
                spectrogram_array = np.array(self.spectrogram_data).T
                self.spectrogram_image.set_array(spectrogram_array)
                self.spectrogram_image.set_extent([
                    0, len(self.spectrogram_data),
                    0, 192  # 0-192kHz
                ])
                self.spectrogram_ax.set_xlim(0, len(self.spectrogram_data))
        
        # 刷新显示
        self.draw_idle()
    
    def clear_displays(self):
        """清空显示"""
        self.spectrogram_data.clear()
        self.time_buffer.clear()
        
        # 清空图线
        self.time_line.set_data([], [])
        self.spectrum_line.set_data([], [])
        
        # 重置声谱图
        dummy_data = np.zeros((100, 10))
        self.spectrogram_image.set_array(dummy_data)
        
        self.draw()


class UltrasonicControlPanel(QWidget):
    """超声波控制面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 设备状态组
        status_group = QGroupBox("UltraMic384K 设备状态")
        status_layout = QGridLayout()
        
        self.device_label = QLabel("设备: hw:3,0")
        self.sample_rate_label = QLabel("采样率: 384000 Hz")
        self.format_label = QLabel("格式: 16bit 整数")
        self.status_label = QLabel("状态: 未连接")
        
        status_layout.addWidget(QLabel("设备:"), 0, 0)
        status_layout.addWidget(QLabel("hw:3,0"), 0, 1)
        status_layout.addWidget(QLabel("采样率:"), 1, 0)
        status_layout.addWidget(QLabel("384000 Hz"), 1, 1)
        status_layout.addWidget(QLabel("格式:"), 2, 0)
        status_layout.addWidget(QLabel("16bit整数"), 2, 1)
        status_layout.addWidget(QLabel("状态:"), 3, 0)
        status_layout.addWidget(self.status_label, 3, 1)
        
        status_group.setLayout(status_layout)
        
        # 控制按钮组
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout()
        
        self.start_button = QPushButton("开始超声波监测")
        self.start_button.setCheckable(True)
        self.start_button.setStyleSheet("QPushButton:checked { background-color: #4CAF50; }")
        
        self.clear_button = QPushButton("清空显示")
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.clear_button)
        
        control_group.setLayout(control_layout)
        
        # 显示设置组
        display_group = QGroupBox("显示设置")
        display_layout = QGridLayout()
        
        self.time_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_scale_slider.setRange(50, 500)  # 50-500ms
        self.time_scale_slider.setValue(100)
        self.time_scale_label = QLabel("100ms")
        
        self.freq_max_spinbox = QSpinBox()
        self.freq_max_spinbox.setRange(20, 192)
        self.freq_max_spinbox.setValue(192)
        self.freq_max_spinbox.setSuffix(" kHz")
        
        self.ultrasonic_highlight = QCheckBox("突出超声波频段 (>20kHz)")
        self.ultrasonic_highlight.setChecked(True)
        
        display_layout.addWidget(QLabel("时域窗口:"), 0, 0)
        display_layout.addWidget(self.time_scale_slider, 0, 1)
        display_layout.addWidget(self.time_scale_label, 0, 2)
        display_layout.addWidget(QLabel("最大频率:"), 1, 0)
        display_layout.addWidget(self.freq_max_spinbox, 1, 1)
        display_layout.addWidget(self.ultrasonic_highlight, 2, 0, 1, 3)
        
        display_group.setLayout(display_layout)
        
        # 实时统计组
        stats_group = QGroupBox("实时统计")
        stats_layout = QGridLayout()
        
        self.rms_label = QLabel("0.000")
        self.peak_freq_label = QLabel("0 Hz")
        self.ultrasonic_power_label = QLabel("0%")
        self.data_rate_label = QLabel("0 MB/s")
        
        stats_layout.addWidget(QLabel("RMS振幅:"), 0, 0)
        stats_layout.addWidget(self.rms_label, 0, 1)
        stats_layout.addWidget(QLabel("峰值频率:"), 1, 0)
        stats_layout.addWidget(self.peak_freq_label, 1, 1)
        stats_layout.addWidget(QLabel("超声波功率:"), 2, 0)
        stats_layout.addWidget(self.ultrasonic_power_label, 2, 1)
        stats_layout.addWidget(QLabel("数据速率:"), 3, 0)
        stats_layout.addWidget(self.data_rate_label, 3, 1)
        
        stats_group.setLayout(stats_layout)
        
        # 添加到主布局
        layout.addWidget(status_group)
        layout.addWidget(control_group)
        layout.addWidget(display_group)
        layout.addWidget(stats_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 连接信号
        self.time_scale_slider.valueChanged.connect(self._update_time_scale)
        
    def _update_time_scale(self, value):
        """更新时间刻度标签"""
        self.time_scale_label.setText(f"{value}ms")
    
    def update_status(self, status_text, color="white"):
        """更新状态显示"""
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def update_stats(self, rms, peak_freq, ultrasonic_ratio, data_rate):
        """更新统计信息"""
        self.rms_label.setText(f"{rms:.6f}")
        self.peak_freq_label.setText(f"{peak_freq:.0f} Hz")
        self.ultrasonic_power_label.setText(f"{ultrasonic_ratio*100:.1f}%")
        self.data_rate_label.setText(f"{data_rate:.2f} MB/s")


class UltrasonicMainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UltraMic384K 超声波实时可视化器")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 核心组件
        self.capture_thread = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        
        # 统计变量
        self.data_count = 0
        self.last_update_time = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        self.control_panel = UltrasonicControlPanel()
        self.control_panel.setMaximumWidth(350)
        
        # 右侧可视化区域
        self.spectrum_widget = UltrasonicSpectrumWidget()
        
        main_layout.addWidget(self.control_panel)
        main_layout.addWidget(self.spectrum_widget, 1)
        
        central_widget.setLayout(main_layout)
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 点击开始按钮启动超声波监测")
        
        # 连接信号
        self.control_panel.start_button.clicked.connect(self.toggle_monitoring)
        self.control_panel.clear_button.clicked.connect(self.clear_displays)
        
    def toggle_monitoring(self):
        """切换监测状态"""
        if self.control_panel.start_button.isChecked():
            self.start_monitoring()
        else:
            self.stop_monitoring()
            
    def start_monitoring(self):
        """开始监测"""
        try:
            self.capture_thread = UltrasonicCaptureThread()
            if self.capture_thread.start_capture():
                self.update_timer.start(16)  # ~60fps
                self.control_panel.start_button.setText("停止监测")
                self.control_panel.update_status("运行中", "green")
                self.statusBar().showMessage("超声波监测已启动 - 384kHz实时采集中...")
                self.last_update_time = time.time()
            else:
                self.control_panel.start_button.setChecked(False)
                self.control_panel.update_status("启动失败", "red")
                self.statusBar().showMessage("启动失败 - 请检查UltraMic384K设备连接")
        except Exception as e:
            self.control_panel.start_button.setChecked(False)
            self.control_panel.update_status(f"错误: {e}", "red")
            
    def stop_monitoring(self):
        """停止监测"""
        if self.capture_thread:
            self.capture_thread.stop_capture()
            self.capture_thread = None
            
        self.update_timer.stop()
        self.control_panel.start_button.setText("开始超声波监测")
        self.control_panel.update_status("已停止", "orange")
        self.statusBar().showMessage("超声波监测已停止")
        
    def update_displays(self):
        """更新显示"""
        if not self.capture_thread:
            return
            
        audio_data = self.capture_thread.get_data()
        if audio_data is not None:
            # 更新可视化
            self.spectrum_widget.update_displays(audio_data)
            
            # 计算统计信息
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            # 简单的峰值频率检测
            if len(audio_data) >= 1024:
                fft_result = np.fft.rfft(audio_data.flatten()[-1024:])
                frequencies = np.fft.rfftfreq(1024, 1/384000)
                peak_idx = np.argmax(np.abs(fft_result))
                peak_freq = frequencies[peak_idx]
                
                # 超声波功率比
                ultrasonic_mask = frequencies >= 20000
                if np.any(ultrasonic_mask):
                    total_power = np.sum(np.abs(fft_result) ** 2)
                    ultrasonic_power = np.sum(np.abs(fft_result[ultrasonic_mask]) ** 2)
                    ultrasonic_ratio = ultrasonic_power / total_power if total_power > 0 else 0
                else:
                    ultrasonic_ratio = 0
            else:
                peak_freq = 0
                ultrasonic_ratio = 0
                
            # 计算数据速率
            self.data_count += len(audio_data) * 2  # 16bit = 2 bytes
            current_time = time.time()
            if current_time - self.last_update_time >= 1.0:
                data_rate = self.data_count / (1024 * 1024)  # MB/s
                self.data_count = 0
                self.last_update_time = current_time
            else:
                data_rate = 0
                
            # 更新控制面板统计
            self.control_panel.update_stats(rms, peak_freq, ultrasonic_ratio, data_rate)
            
    def clear_displays(self):
        """清空显示"""
        self.spectrum_widget.clear_displays()
        self.statusBar().showMessage("显示已清空")
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.capture_thread:
            self.capture_thread.stop_capture()
        event.accept()


def main():
    """主函数"""
    import time
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置暗色主题
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; color: white; }
        QWidget { background-color: #2b2b2b; color: white; }
        QGroupBox { font-weight: bold; border: 2px solid #555; margin: 5px; padding: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QPushButton { background-color: #404040; border: 1px solid #666; padding: 8px; }
        QPushButton:hover { background-color: #505050; }
        QPushButton:pressed { background-color: #353535; }
    """)
    
    window = UltrasonicMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()