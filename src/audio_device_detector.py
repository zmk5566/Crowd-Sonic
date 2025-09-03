"""
更专业的音频设备检测模块
使用PyAudio的is_format_supported方法准确检测USB音频设备支持的采样率
"""
import sounddevice as sd
from typing import List, Dict, Optional, Tuple
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioDeviceDetector:
    """音频设备检测器 - 使用增强的sounddevice检测，基于网上最佳实践"""
    
    def __init__(self):
        self.test_duration = 0.001  # 1ms测试时长，最小化干扰
    
    def get_all_devices(self) -> List[Dict]:
        """获取所有音频设备信息"""
        devices = []
        
        # 使用sounddevice获取基本设备信息
        try:
            sd_devices = sd.query_devices()
            for i, device in enumerate(sd_devices):
                if device['max_input_channels'] > 0:  # 只关心输入设备
                    devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'default_sample_rate': device['default_samplerate'],
                        'hostapi': sd.query_hostapis(device['hostapi'])['name'],
                        'latency': device['default_low_input_latency']
                    })
        except Exception as e:
            logger.error(f"获取设备列表失败: {e}")
            
        return devices
    
    def get_supported_sample_rates_advanced(self, device_index: int, 
                                           channels: int = 1) -> List[int]:
        """
        使用增强的sounddevice方法检测支持的采样率
        基于网上最佳实践，更准确地检测真实支持的采样率
        """
        # 按重要性排序的采样率列表，特别关注UAC设备
        test_rates = [
            # UAC2设备常见的高采样率（优先测试）
            384000, 352800, 192000, 176400,
            # 标准高品质采样率
            96000, 88200, 
            # 标准采样率
            48000, 44100,
            # 特殊采样率（一些UAC设备可能支持）
            768000, 512000, 256000, 128000,
            # 低采样率（通信用）
            32000, 22050, 16000, 11025, 8000
        ]
        
        supported_rates = []
        
        for sample_rate in test_rates:
            try:
                # 使用check_input_settings检测
                sd.check_input_settings(
                    device=device_index,
                    channels=channels,
                    samplerate=sample_rate,
                    dtype=np.float32
                )
                
                # 进一步验证：尝试真实创建流
                try:
                    with sd.InputStream(
                        device=device_index,
                        channels=channels,
                        samplerate=sample_rate,
                        dtype=np.float32,
                        blocksize=64,  # 小的块大小减少干扰
                        latency='low'
                    ) as stream:
                        # 简短测试读取
                        data = stream.read(16)  # 只读取16个样本
                        if data is not None:
                            supported_rates.append(sample_rate)
                            logger.debug(f"设备 {device_index} 验证支持采样率: {sample_rate} Hz")
                        
                except Exception as stream_error:
                    # 流创建失败，但check_input_settings通过了
                    # 这可能表示设备名义上支持但实际不可用
                    logger.debug(f"设备 {device_index} 采样率 {sample_rate} Hz: 检测通过但流创建失败: {stream_error}")
                    continue
                    
            except Exception as check_error:
                # 不支持该采样率
                logger.debug(f"设备 {device_index} 不支持采样率 {sample_rate} Hz: {check_error}")
                continue
                
        return sorted(supported_rates)
    
    def get_supported_sample_rates_sounddevice(self, device_index: int, 
                                             channels: int = 1) -> List[int]:
        """
        使用sounddevice检测支持的采样率（备用方法）
        """
        test_rates = [8000, 16000, 22050, 32000, 44100, 48000, 
                     88200, 96000, 176400, 192000, 352800, 384000]
        supported_rates = []
        
        for sample_rate in test_rates:
            try:
                sd.check_input_settings(
                    device=device_index,
                    channels=channels,
                    samplerate=sample_rate
                )
                supported_rates.append(sample_rate)
                logger.debug(f"sounddevice: 设备 {device_index} 支持采样率: {sample_rate} Hz")
                
            except Exception:
                logger.debug(f"sounddevice: 设备 {device_index} 不支持采样率: {sample_rate} Hz")
                continue
                
        return sorted(supported_rates)
    
    def get_device_capabilities(self, device_index: int) -> Dict:
        """
        获取设备的完整能力信息
        使用增强的检测方法确保准确性
        """
        capabilities = {
            'device_index': device_index,
            'supported_sample_rates': [],
            'max_channels': 0,
            'formats': [],
            'detection_method': 'enhanced_sounddevice'
        }
        
        # 使用增强的检测方法
        try:
            enhanced_rates = self.get_supported_sample_rates_advanced(device_index)
            if enhanced_rates:
                capabilities['supported_sample_rates'] = enhanced_rates
                logger.info(f"增强检测到设备 {device_index} 支持采样率: {enhanced_rates}")
            else:
                # 如果增强检测失败，使用基本检测
                basic_rates = self.get_supported_sample_rates_sounddevice(device_index)
                capabilities['supported_sample_rates'] = basic_rates
                capabilities['detection_method'] = 'basic_sounddevice'
                logger.info(f"基本检测到设备 {device_index} 支持采样率: {basic_rates}")
        except Exception as e:
            logger.warning(f"设备采样率检测失败: {e}")
            # 使用基本检测作为最后手段
            try:
                basic_rates = self.get_supported_sample_rates_sounddevice(device_index)
                capabilities['supported_sample_rates'] = basic_rates
                capabilities['detection_method'] = 'fallback_basic'
            except Exception as fallback_error:
                logger.error(f"所有检测方法都失败: {fallback_error}")
        
        # 获取其他设备信息
        try:
            device_info = sd.query_devices(device_index)
            capabilities['max_channels'] = device_info['max_input_channels']
            capabilities['default_sample_rate'] = device_info['default_samplerate']
            capabilities['name'] = device_info['name']
            capabilities['latency'] = device_info.get('default_low_input_latency', 0)
        except Exception as e:
            logger.warning(f"获取设备基本信息失败: {e}")
            
        return capabilities
    
    def find_uac_devices(self) -> List[Dict]:
        """
        查找所有UAC设备并获取其完整能力信息
        """
        devices = self.get_all_devices()
        uac_devices = []
        
        for device in devices:
            device_name = device['name'].lower()
            
            # 判断是否为UAC设备的关键词
            uac_keywords = ['usb', 'uac', 'audio', 'dac', 'adc', 'interface']
            
            is_uac = any(keyword in device_name for keyword in uac_keywords)
            
            # 或者检查是否支持高采样率（通常UAC2设备支持）
            capabilities = self.get_device_capabilities(device['index'])
            high_sample_rates = [rate for rate in capabilities['supported_sample_rates'] 
                               if rate >= 96000]
            
            if is_uac or high_sample_rates:
                device_info = {
                    **device,
                    **capabilities,
                    'is_high_quality': len(high_sample_rates) > 0,
                    'ultrasonic_capable': any(rate >= 192000 for rate in capabilities['supported_sample_rates'])
                }
                uac_devices.append(device_info)
                
                logger.info(f"发现UAC设备: {device['name']}")
                logger.info(f"  支持的采样率: {capabilities['supported_sample_rates']}")
                logger.info(f"  检测方法: {capabilities['detection_method']}")
                
        return uac_devices
    
    def get_best_uac_device(self) -> Optional[Dict]:
        """
        获取最佳的UAC设备（支持最高采样率的）
        """
        uac_devices = self.find_uac_devices()
        
        if not uac_devices:
            return None
            
        # 按最高支持的采样率排序
        best_device = max(uac_devices, 
                         key=lambda d: max(d['supported_sample_rates']) if d['supported_sample_rates'] else 0)
        
        return best_device


def main():
    """测试函数"""
    detector = AudioDeviceDetector()
    
    print("=" * 80)
    print("专业音频设备检测")
    print("=" * 80)
    
    # 获取所有设备
    devices = detector.get_all_devices()
    print(f"\n找到 {len(devices)} 个音频输入设备:")
    
    for device in devices:
        print(f"\n设备 {device['index']}: {device['name']}")
        print(f"  默认采样率: {device['default_sample_rate']} Hz")
        print(f"  通道数: {device['channels']}")
        print(f"  音频API: {device['hostapi']}")
        
        # 检测支持的采样率
        capabilities = detector.get_device_capabilities(device['index'])
        supported_rates = capabilities['supported_sample_rates']
        
        if supported_rates:
            print(f"  支持的采样率: {supported_rates}")
            print(f"  检测方法: {capabilities['detection_method']}")
            
            # 标记特殊能力
            high_rates = [r for r in supported_rates if r >= 96000]
            if high_rates:
                print(f"  ★ 高品质采样: {high_rates}")
                
            ultra_rates = [r for r in supported_rates if r >= 192000]
            if ultra_rates:
                print(f"  ★★ 超声波采样: {ultra_rates}")
        else:
            print(f"  ⚠️ 无法检测到支持的采样率")
            
        print("-" * 60)
    
    # 重点显示UAC设备
    print(f"\n" + "=" * 80)
    print("UAC设备专项分析")
    print("=" * 80)
    
    uac_devices = detector.find_uac_devices()
    
    if uac_devices:
        print(f"\n发现 {len(uac_devices)} 个UAC设备:")
        
        for device in uac_devices:
            print(f"\n🎵 UAC设备: {device['name']}")
            print(f"   设备ID: {device['index']}")
            print(f"   支持采样率: {device['supported_sample_rates']}")
            print(f"   检测方法: {device['detection_method']}")
            print(f"   高品质音频: {'是' if device['is_high_quality'] else '否'}")
            print(f"   超声波能力: {'是' if device['ultrasonic_capable'] else '否'}")
            
        # 推荐最佳设备
        best = detector.get_best_uac_device()
        if best:
            max_rate = max(best['supported_sample_rates']) if best['supported_sample_rates'] else 0
            print(f"\n🏆 推荐设备: {best['name']} (最高支持 {max_rate} Hz)")
            
    else:
        print("\n❌ 未发现UAC设备")


if __name__ == "__main__":
    main()