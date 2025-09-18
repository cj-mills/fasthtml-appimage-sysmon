"""
Temperature sensors monitoring module.
"""

import subprocess
import psutil


def get_temperature_info():
    """Get temperature sensor information."""
    temps = []

    try:
        # Get temperature sensors using psutil
        if hasattr(psutil, 'sensors_temperatures'):
            temp_sensors = psutil.sensors_temperatures()

            # Process each sensor type
            for sensor_type, sensors in temp_sensors.items():
                for sensor in sensors:
                    # Filter out sensors with invalid readings
                    if sensor.current is not None and sensor.current > 0:
                        temp_info = {
                            'type': sensor_type,
                            'label': sensor.label or sensor_type,
                            'current': sensor.current,
                            'high': sensor.high,
                            'critical': sensor.critical
                        }
                        temps.append(temp_info)
    except Exception as e:
        print(f"Error getting temperature sensors: {e}")

    # If psutil doesn't provide temps, try alternative methods
    if not temps:
        # Try reading from thermal zones (Linux)
        try:
            import glob
            thermal_zones = glob.glob('/sys/class/thermal/thermal_zone*/temp')
            for i, zone_path in enumerate(thermal_zones):
                try:
                    with open(zone_path, 'r') as f:
                        temp_millidegree = int(f.read().strip())
                        temp_celsius = temp_millidegree / 1000.0

                        # Try to get the type
                        type_path = zone_path.replace('/temp', '/type')
                        sensor_type = f"thermal_zone{i}"
                        try:
                            with open(type_path, 'r') as f:
                                sensor_type = f.read().strip()
                        except:
                            pass

                        temps.append({
                            'type': 'thermal',
                            'label': sensor_type,
                            'current': temp_celsius,
                            'high': 85.0,  # Default high threshold
                            'critical': 95.0  # Default critical threshold
                        })
                except Exception:
                    continue
        except Exception:
            pass

    # Try to get NVIDIA GPU temperature (only if nvitop isn't available)
    try:
        import nvitop
        # If nvitop is available, GPU temps are handled in check_gpu()
        # so we skip adding them here to avoid duplication
    except ImportError:
        # nvitop not available, try nvidia-smi
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                gpu_temps = result.stdout.strip().split('\n')
                for i, temp in enumerate(gpu_temps):
                    if temp:
                        temps.append({
                            'type': 'gpu',
                            'label': f'NVIDIA GPU {i}',
                            'current': float(temp),
                            'high': 80.0,
                            'critical': 90.0
                        })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass

    return temps