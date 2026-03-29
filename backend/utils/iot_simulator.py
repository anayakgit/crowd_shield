import random
import time
from backend.config import Config

class IoTSimulator:
    """Simulate IoT sensor data based on crowd conditions"""
    
    def __init__(self):
        self.base_temperature = Config.TEMP_BASE
        self.base_noise = Config.NOISE_BASE
        self.base_humidity = 55.0
        self.last_update = time.time()
        
    def generate_sensor_data(self, crowd_count, movement_magnitude=0):
        """
        Generate simulated IoT sensor readings
        
        Args:
            crowd_count: Number of people detected
            movement_magnitude: Movement intensity (0-10)
            
        Returns:
            dict: Simulated sensor readings
        """
        # Temperature increases with crowd size
        temperature = self.base_temperature + (crowd_count * Config.TEMP_CROWD_FACTOR)
        temperature += random.uniform(-0.5, 0.5)  # Random variation
        
        # Noise level increases with crowd size and movement
        noise_level = self.base_noise + (crowd_count * Config.NOISE_CROWD_FACTOR)
        noise_level += movement_magnitude * 3  # Movement adds noise
        noise_level += random.uniform(-2, 2)  # Random variation
        
        # Humidity slightly increases with crowd (breathing, perspiration)
        humidity = self.base_humidity + (crowd_count * 0.2)
        humidity += random.uniform(-1, 1)
        humidity = min(humidity, 95)  # Cap at 95%
        
        # Air quality degrades with crowd density
        air_quality_index = 50 - (crowd_count * 0.5)  # Lower is worse
        air_quality_index = max(air_quality_index, 10)  # Floor at 10
        air_quality_index += random.uniform(-3, 3)
        
        # CO2 level (ppm) increases with crowd
        co2_level = 400 + (crowd_count * 15)  # Start at atmospheric level
        co2_level += random.uniform(-20, 20)
        
        # Panic button status (simulated)
        panic_button_pressed = crowd_count > 60 and random.random() < 0.1
        
        sensor_data = {
            'temperature': float(round(temperature, 1)),
            'noise_level': float(round(noise_level, 1)),
            'humidity': float(round(humidity, 1)),
            'air_quality_index': float(round(air_quality_index, 1)),
            'co2_level': float(round(co2_level, 0)),
            'panic_button': bool(panic_button_pressed),
            'timestamp': float(time.time())
        }
        
        return sensor_data
    
    def get_sensor_status(self, sensor_data):
        """Get human-readable sensor status"""
        status = []
        
        # Temperature status
        temp = sensor_data['temperature']
        if temp > 32:
            status.append({'sensor': 'Temperature', 'status': 'CRITICAL', 'value': f'{temp}°C'})
        elif temp > 28:
            status.append({'sensor': 'Temperature', 'status': 'WARNING', 'value': f'{temp}°C'})
        else:
            status.append({'sensor': 'Temperature', 'status': 'NORMAL', 'value': f'{temp}°C'})
        
        # Noise status
        noise = sensor_data['noise_level']
        if noise > 85:
            status.append({'sensor': 'Noise', 'status': 'CRITICAL', 'value': f'{noise} dB'})
        elif noise > 70:
            status.append({'sensor': 'Noise', 'status': 'WARNING', 'value': f'{noise} dB'})
        else:
            status.append({'sensor': 'Noise', 'status': 'NORMAL', 'value': f'{noise} dB'})
        
        # Humidity status
        humidity = sensor_data['humidity']
        if humidity > 75:
            status.append({'sensor': 'Humidity', 'status': 'WARNING', 'value': f'{humidity}%'})
        else:
            status.append({'sensor': 'Humidity', 'status': 'NORMAL', 'value': f'{humidity}%'})
        
        # Air quality status
        aqi = sensor_data['air_quality_index']
        if aqi < 20:
            status.append({'sensor': 'Air Quality', 'status': 'CRITICAL', 'value': f'AQI {aqi}'})
        elif aqi < 35:
            status.append({'sensor': 'Air Quality', 'status': 'WARNING', 'value': f'AQI {aqi}'})
        else:
            status.append({'sensor': 'Air Quality', 'status': 'NORMAL', 'value': f'AQI {aqi}'})
        
        # CO2 status
        co2 = sensor_data['co2_level']
        if co2 > 1000:
            status.append({'sensor': 'CO2 Level', 'status': 'WARNING', 'value': f'{co2} ppm'})
        else:
            status.append({'sensor': 'CO2 Level', 'status': 'NORMAL', 'value': f'{co2} ppm'})
        
        # Panic button
        if sensor_data['panic_button']:
            status.append({'sensor': 'Panic Button', 'status': 'CRITICAL', 'value': 'PRESSED'})
        
        return status
    
    def simulate_environmental_changes(self, time_of_day='day'):
        """Adjust base values based on time of day"""
        if time_of_day == 'day':
            self.base_temperature = 25.0
            self.base_humidity = 55.0
        elif time_of_day == 'night':
            self.base_temperature = 20.0
            self.base_humidity = 65.0
        elif time_of_day == 'evening':
            self.base_temperature = 22.0
            self.base_humidity = 60.0
