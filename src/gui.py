"""
跨平台GUI界面
使用PyQt6创建实时超声波数据可视化界面
"""
import sys
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QPushButton, QComboBox, QLabel, QSlider,
                            QSpinBox, QCheckBox, QGroupBox, QGridLayout,
                            QStatusBar, QSplitter, QTabWidget)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.style as mplstyle

from audio_capture import AudioCapture
from signal_processor import SignalProcessor
from audio_device_detector import AudioDeviceDetector

# 使用快速绘制样式
mplstyle.use('fast')


class SpectrumWidget(FigureCanvas):
    """频谱显示组件"""
    
    def __init__(self, parent=None):
        self.figure = Figure(facecolor='black', figsize=(12, 6))
        super().__init__(self.figure)
        self.setParent(parent)
        
        # 创建子图
        self.spectrum_ax = self.figure.add_subplot(211)
        self.spectrogram_ax = self.figure.add_subplot(212)
        
        # 配置样式
        self._setup_plot_style()
        
        # 频谱图数据缓冲区
        self.spectrogram_data = []
        self.max_spectrogram_length = 200  # 增加缓冲长度
        
        # 频率范围
        self.freq_min = 0
        self.freq_max = 192000
        
        # 绘图对象缓存
        self.spectrum_line = None
        self.spectrogram_image = None
        self.time_axis = []
        
        # 初始化绘图
        self._init_plots()
        
    def _setup_plot_style(self):
        """设置绘图样式"""
        # 频谱图
        self.spectrum_ax.set_facecolor('black')
        self.spectrum_ax.grid(True, alpha=0.3, color='white')
        self.spectrum_ax.set_xlabel('频率 (Hz)', color='white')
        self.spectrum_ax.set_ylabel('幅度 (dB)', color='white')
        self.spectrum_ax.tick_params(colors='white')
        self.spectrum_ax.set_title('实时频谱', color='white', fontsize=12)
        
        # 声谱图
        self.spectrogram_ax.set_facecolor('black')
        self.spectrogram_ax.set_xlabel('时间', color='white')
        self.spectrogram_ax.set_ylabel('频率 (Hz)', color='white')
        self.spectrogram_ax.tick_params(colors='white')
        self.spectrogram_ax.set_title('实时声谱图', color='white', fontsize=12)
        
        self.figure.tight_layout()
    
    def _init_plots(self):
        """初始化绘图对象"""
        # 初始化频谱线
        self.spectrum_line, = self.spectrum_ax.plot([], [], 'cyan', linewidth=0.8)
        
        # 初始化声谱图（空的）
        dummy_data = np.zeros((100, 10))  # 临时数据
        self.spectrogram_image = self.spectrogram_ax.imshow(
            dummy_data, aspect='auto', origin='lower',
            cmap='viridis', vmin=-80, vmax=20
        )
        
    def update_spectrum(self, frequencies, magnitude):
        """更新频谱显示"""
        # 频率范围滤波
        freq_mask = (frequencies >= self.freq_min) & (frequencies <= self.freq_max)
        freq_filtered = frequencies[freq_mask]
        mag_filtered = magnitude[freq_mask]
        
        # 更新频谱线（不清除，只更新数据）
        if self.spectrum_line is None:
            self._init_plots()
            
        self.spectrum_line.set_data(freq_filtered, mag_filtered)
        self.spectrum_ax.set_xlim(self.freq_min, self.freq_max)
        self.spectrum_ax.set_ylim(-80, 20)
        
        # 添加到声谱图数据
        self.spectrogram_data.append(mag_filtered)
        self.time_axis.append(len(self.time_axis))
        
        if len(self.spectrogram_data) > self.max_spectrogram_length:
            self.spectrogram_data.pop(0)
            self.time_axis.pop(0)
            
        # 更新声谱图（滚动显示）
        if len(self.spectrogram_data) > 5:  # 至少5帧才开始显示
            spectrogram_array = np.array(self.spectrogram_data).T
            
            # 更新图像数据而不重新创建
            self.spectrogram_image.set_array(spectrogram_array)
            self.spectrogram_image.set_extent([
                0, len(self.spectrogram_data), 
                freq_filtered[0], freq_filtered[-1]
            ])
            
            # 更新坐标轴范围
            self.spectrogram_ax.set_xlim(0, len(self.spectrogram_data))
            self.spectrogram_ax.set_ylim(freq_filtered[0], freq_filtered[-1])
        
        # 只重绘画布，不重新创建图形
        self.draw_idle()  # 使用idle绘制提高性能
        
    def set_frequency_range(self, freq_min, freq_max):
        """设置频率显示范围"""
        self.freq_min = freq_min
        self.freq_max = freq_max


class ControlPanel(QWidget):
    """控制面板"""
    
    # 信号
    device_changed = pyqtSignal(int)
    frequency_range_changed = pyqtSignal(int, int)
    recording_toggled = pyqtSignal(bool)
    sample_rate_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout()
        
        # 设备选择组
        device_group = QGroupBox("音频设备")
        device_layout = QVBoxLayout()
        
        self.device_combo = QComboBox()
        self.refresh_button = QPushButton("刷新设备")
        self.refresh_button.clicked.connect(self.refresh_devices)
        
        device_layout.addWidget(QLabel("选择UAC设备:"))
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(self.refresh_button)
        device_group.setLayout(device_layout)
        
        # 音频参数组
        audio_group = QGroupBox("音频参数")
        audio_layout = QGridLayout()
        
        # 采样率选择
        self.sample_rate_combo = QComboBox()
        # 初始时显示常见采样率，设备选中后会更新
        self.sample_rate_combo.addItems(["48000", "96000", "192000", "384000"])
        self.sample_rate_combo.setCurrentText("384000")
        
        # 支持的采样率缓存
        self.supported_sample_rates = {}
        
        # 设备检测器
        self.device_detector = AudioDeviceDetector()
        
        audio_layout.addWidget(QLabel("采样率:"), 0, 0)
        audio_layout.addWidget(self.sample_rate_combo, 0, 1)
        
        audio_group.setLayout(audio_layout)
        
        # 频率范围组
        freq_group = QGroupBox("频率范围")
        freq_layout = QGridLayout()
        
        self.freq_min_spinbox = QSpinBox()
        self.freq_min_spinbox.setRange(0, 200000)
        self.freq_min_spinbox.setValue(0)
        self.freq_min_spinbox.setSuffix(" Hz")
        
        self.freq_max_spinbox = QSpinBox()
        self.freq_max_spinbox.setRange(1000, 200000)
        self.freq_max_spinbox.setValue(100000)  # 提高默认值显示更多超声波
        self.freq_max_spinbox.setSuffix(" Hz")
        
        freq_layout.addWidget(QLabel("最小频率:"), 0, 0)
        freq_layout.addWidget(self.freq_min_spinbox, 0, 1)
        freq_layout.addWidget(QLabel("最大频率:"), 1, 0)
        freq_layout.addWidget(self.freq_max_spinbox, 1, 1)
        
        freq_group.setLayout(freq_layout)
        
        # 控制按钮组
        control_group = QGroupBox("控制")
        control_layout = QVBoxLayout()
        
        self.record_button = QPushButton("开始录制")
        self.record_button.setCheckable(True)
        self.record_button.clicked.connect(self._on_record_clicked)
        
        self.ultrasonic_checkbox = QCheckBox("突出超声波频段 (>20kHz)")
        self.ultrasonic_checkbox.setChecked(True)
        
        control_layout.addWidget(self.record_button)
        control_layout.addWidget(self.ultrasonic_checkbox)
        control_group.setLayout(control_layout)
        
        # 添加到主布局
        layout.addWidget(device_group)
        layout.addWidget(audio_group)
        layout.addWidget(freq_group)
        layout.addWidget(control_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 连接信号
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.freq_min_spinbox.valueChanged.connect(self._on_freq_range_changed)
        self.freq_max_spinbox.valueChanged.connect(self._on_freq_range_changed)
        self.sample_rate_combo.currentTextChanged.connect(self._on_sample_rate_changed)
        
    def refresh_devices(self):
        """刷新设备列表"""
        self.device_combo.clear()
        self.supported_sample_rates.clear()
        
        # 使用新的设备检测器
        devices = self.device_detector.get_all_devices()
        
        for device in devices:
            display_name = f"{device['name']} ({device['channels']}ch, {device['hostapi']})"
            self.device_combo.addItem(display_name, device['index'])
            
            # 使用增强的采样率检测
            try:
                capabilities = self.device_detector.get_device_capabilities(device['index'])
                supported_rates = capabilities['supported_sample_rates']
                if supported_rates:
                    self.supported_sample_rates[device['index']] = supported_rates
                    # 显示检测到的信息
                    print(f"设备 {device['index']} ({device['name'][:30]}...): {supported_rates}")
                else:
                    # 使用默认值
                    self.supported_sample_rates[device['index']] = [48000]
            except Exception as e:
                print(f"检测设备 {device['index']} 采样率失败: {e}")
                # 使用默认值
                self.supported_sample_rates[device['index']] = [48000]
        
        # 更新第一个设备的采样率
        if self.device_combo.count() > 0:
            self._update_sample_rates(0)
    
    def _on_record_clicked(self):
        """录制按钮点击"""
        is_recording = self.record_button.isChecked()
        self.record_button.setText("停止录制" if is_recording else "开始录制")
        self.recording_toggled.emit(is_recording)
        
    def _on_freq_range_changed(self):
        """频率范围改变"""
        min_freq = self.freq_min_spinbox.value()
        max_freq = self.freq_max_spinbox.value()
        if max_freq > min_freq:
            self.frequency_range_changed.emit(min_freq, max_freq)
    
    def _on_device_changed(self, index):
        """设备选择改变"""
        self._update_sample_rates(index)
        device_data = self.device_combo.itemData(index)
        if device_data is not None:
            self.device_changed.emit(device_data)
    
    def _update_sample_rates(self, device_combo_index):
        """更新采样率列表"""
        device_index = self.device_combo.itemData(device_combo_index)
        if device_index is None:
            return
            
        # 获取支持的采样率
        supported_rates = self.supported_sample_rates.get(device_index, [48000])
        
        # 保存当前选中的采样率
        current_rate = self.sample_rate_combo.currentText()
        
        # 更新下拉框
        self.sample_rate_combo.clear()
        for rate in supported_rates:
            self.sample_rate_combo.addItem(str(rate))
        
        # 尝试保持之前选中的采样率
        if current_rate and current_rate in [str(r) for r in supported_rates]:
            self.sample_rate_combo.setCurrentText(current_rate)
        else:
            # 选择最高的采样率
            if supported_rates:
                self.sample_rate_combo.setCurrentText(str(max(supported_rates)))
    
    def _on_sample_rate_changed(self, sample_rate_text):
        """采样率改变"""
        try:
            sample_rate = int(sample_rate_text)
            self.sample_rate_changed.emit(sample_rate)
        except ValueError:
            pass


class StatusPanel(QWidget):
    """状态信息面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 实时状态
        status_group = QGroupBox("实时状态")
        status_layout = QGridLayout()
        
        self.peak_freq_label = QLabel("0 Hz")
        self.peak_mag_label = QLabel("0 dB")
        self.centroid_label = QLabel("0 Hz")
        self.ultrasonic_ratio_label = QLabel("0%")
        
        status_layout.addWidget(QLabel("峰值频率:"), 0, 0)
        status_layout.addWidget(self.peak_freq_label, 0, 1)
        status_layout.addWidget(QLabel("峰值幅度:"), 1, 0)
        status_layout.addWidget(self.peak_mag_label, 1, 1)
        status_layout.addWidget(QLabel("频谱质心:"), 2, 0)
        status_layout.addWidget(self.centroid_label, 2, 1)
        status_layout.addWidget(QLabel("超声波占比:"), 3, 0)
        status_layout.addWidget(self.ultrasonic_ratio_label, 3, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def update_status(self, features):
        """更新状态显示"""
        self.peak_freq_label.setText(f"{features['peak_frequency']:.0f} Hz")
        self.peak_mag_label.setText(f"{features['peak_magnitude']:.1f} dB")
        self.centroid_label.setText(f"{features['spectral_centroid']:.0f} Hz")
        self.ultrasonic_ratio_label.setText(f"{features['ultrasonic_ratio']*100:.1f}%")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple UAC Visualizer")
        self.setGeometry(100, 100, 1400, 900)
        
        # 初始参数
        self.current_sample_rate = 384000
        
        # 核心组件
        self.audio_capture = None
        self.signal_processor = None
        self._init_components()
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        
        self.setup_ui()
        
    def _init_components(self):
        """初始化核心组件"""
        # 创建临时配置文件
        temp_config = {
            'audio': {
                'sample_rate': self.current_sample_rate,
                'channels': 1,
                'buffer_size': 1024,
                'device_name': None
            },
            'processing': {
                'fft_size': 2048,
                'overlap': 0.5,
                'window_type': 'hann'
            },
            'visualization': {
                'update_rate': 60
            }
        }
        
        # 保存临时配置
        import tempfile
        import yaml
        self.temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(temp_config, self.temp_config_file)
        self.temp_config_file.flush()
        
        # 创建组件
        self.audio_capture = AudioCapture(self.temp_config_file.name)
        self.signal_processor = SignalProcessor(self.temp_config_file.name)
        
    def setup_ui(self):
        """设置用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        self.control_panel = ControlPanel()
        self.status_panel = StatusPanel()
        
        left_layout.addWidget(self.control_panel)
        left_layout.addWidget(self.status_panel)
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(300)
        
        # 右侧可视化区域
        self.spectrum_widget = SpectrumWidget()
        
        # 添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.spectrum_widget, 1)
        
        central_widget.setLayout(main_layout)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 连接信号
        self.control_panel.device_changed.connect(self.on_device_changed)
        self.control_panel.frequency_range_changed.connect(self.on_frequency_range_changed)
        self.control_panel.recording_toggled.connect(self.on_recording_toggled)
        
        # 初始化设备列表
        self.control_panel.refresh_devices()
        
    def on_device_changed(self, device_index):
        """设备改变"""
        # 如果正在录制，停止后重新开始
        was_recording = self.audio_capture and self.audio_capture.is_recording
        if was_recording:
            self.audio_capture.stop_stream()
            self.update_timer.stop()
            self.statusBar().showMessage(f"已切换到设备 {device_index}")
            
        # 如果之前在录制，重新开始
        if was_recording:
            if self.audio_capture.start_stream(device_index):
                self.update_timer.start(16)
                self.statusBar().showMessage(f"设备 {device_index} 录制中...")
        
    def on_frequency_range_changed(self, min_freq, max_freq):
        """频率范围改变"""
        self.spectrum_widget.set_frequency_range(min_freq, max_freq)
        
    def on_recording_toggled(self, is_recording):
        """录制状态切换"""
        if is_recording:
            # 获取选中的设备
            device_data = self.control_panel.device_combo.currentData()
            device_index = device_data if device_data is not None else None
            
            if self.audio_capture.start_stream(device_index):
                self.update_timer.start(33)  # ~30 FPS
                self.statusBar().showMessage("录制中...")
            else:
                self.control_panel.record_button.setChecked(False)
                self.control_panel.record_button.setText("开始录制")
                self.statusBar().showMessage("启动录制失败")
        else:
            self.audio_capture.stop_stream()
            self.update_timer.stop()
            self.statusBar().showMessage("录制已停止")
            
    def update_display(self):
        """更新显示"""
        # 获取音频数据
        audio_data = self.audio_capture.get_audio_data()
        if audio_data is not None:
            # 信号处理
            frequencies, magnitude = self.signal_processor.process_overlapped_chunk(audio_data)
            if frequencies is not None and magnitude is not None:
                # 更新频谱显示
                self.spectrum_widget.update_spectrum(frequencies, magnitude)
                
                # 计算并更新状态
                features = self.signal_processor.calculate_spectrum_features(frequencies, magnitude)
                self.status_panel.update_status(features)
                
                # 更新状态栏信息
                peak_freq = features['peak_frequency']
                if peak_freq > 20000:
                    self.statusBar().showMessage(f"检测到超声波: {peak_freq:.0f} Hz - 采样率: {self.current_sample_rate} Hz")
                else:
                    self.statusBar().showMessage(f"录制中 - 峰值: {peak_freq:.0f} Hz - 采样率: {self.current_sample_rate} Hz")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置样式
    app.setStyle('Fusion')
    
    # 设置暗色主题
    palette = app.palette()
    palette.setColor(palette.ColorRole.Window, palette.color(palette.ColorRole.Base))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()