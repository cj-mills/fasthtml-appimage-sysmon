"""
GPU monitoring module (NVIDIA, AMD, Intel).
"""

import subprocess


def check_gpu():
    """Check for GPU availability and get info using nvitop."""
    gpu_info = {'available': False, 'type': 'None', 'details': {}, 'processes': []}

    try:
        import nvitop
        from nvitop import Device, GpuProcess, NA

        devices = Device.all()  # Get all NVIDIA devices
        if devices:
            gpu_info['available'] = True
            gpu_info['type'] = 'NVIDIA'

            for i, device in enumerate(devices):
                # Get memory in MB for consistency, with NA checks
                mem_total = device.memory_total()
                mem_used = device.memory_used()
                mem_free = device.memory_free()

                memory_total_mb = mem_total // (1024 * 1024) if mem_total and mem_total != NA else 0
                memory_used_mb = mem_used // (1024 * 1024) if mem_used and mem_used != NA else 0
                memory_free_mb = mem_free // (1024 * 1024) if mem_free and mem_free != NA else 0

                # Get power values and convert from milliwatts to watts
                power_usage_mw = device.power_usage()
                power_limit_mw = device.power_limit()
                power_usage_w = power_usage_mw / 1000.0 if power_usage_mw and power_usage_mw != NA else None
                power_limit_w = power_limit_mw / 1000.0 if power_limit_mw and power_limit_mw != NA else None

                # Get other metrics with NA checks
                gpu_util = device.gpu_utilization()
                temp = device.temperature()
                fan = device.fan_speed()
                enc_util = device.encoder_utilization()
                dec_util = device.decoder_utilization()

                gpu_info['details'][f'gpu_{i}'] = {
                    'name': device.name(),
                    'memory_total': memory_total_mb,
                    'memory_used': memory_used_mb,
                    'memory_free': memory_free_mb,
                    'utilization': gpu_util if gpu_util != NA else 0,
                    'temperature': temp if temp != NA else None,
                    'power_usage': power_usage_w,  # Now in watts
                    'power_limit': power_limit_w,  # Now in watts
                    'fan_speed': fan if fan != NA else None,
                    'compute_processes': len(device.processes()),
                    'encoder_utilization': enc_util if enc_util != NA else 0,
                    'decoder_utilization': dec_util if dec_util != NA else 0,
                }

                # Get process information for this GPU
                processes = device.processes()
                if processes:
                    try:
                        # Take snapshots of processes for detailed info
                        process_snapshots = GpuProcess.take_snapshots(processes.values(), failsafe=True)
                        for snapshot in process_snapshots:
                            # In snapshots, gpu_memory() is still a method according to the docs
                            # But let's try accessing it as a property first, then as a method
                            try:
                                # Try as a method first (according to docs)
                                gpu_mem = snapshot.gpu_memory() if callable(getattr(snapshot, 'gpu_memory', None)) else snapshot.gpu_memory
                            except:
                                # Fallback to property access
                                gpu_mem = getattr(snapshot, 'gpu_memory', NA)

                            gpu_memory_mb = gpu_mem // (1024 * 1024) if gpu_mem and gpu_mem != NA else 0

                            # Get the process name - try different attributes
                            proc_name = None
                            if hasattr(snapshot, 'name') and callable(snapshot.name):
                                try:
                                    proc_name = snapshot.name()
                                except:
                                    pass
                            if not proc_name and hasattr(snapshot, 'command'):
                                proc_name = snapshot.command
                            if not proc_name and hasattr(snapshot, 'username'):
                                proc_name = f"{snapshot.username} (PID {snapshot.pid})"
                            if not proc_name:
                                proc_name = f"PID {snapshot.pid}"

                            if proc_name and len(str(proc_name)) > 50:
                                proc_name = str(proc_name)[:47] + "..."

                            gpu_info['processes'].append({
                                'pid': snapshot.pid,  # pid is a property on snapshot
                                'name': str(proc_name),
                                'gpu_memory_mb': gpu_memory_mb,
                                'gpu_utilization': getattr(snapshot, 'gpu_sm_utilization', 0) if getattr(snapshot, 'gpu_sm_utilization', 0) != NA else 0,
                                'device_id': i,
                                'device_name': device.name()
                            })
                    except Exception as e:
                        print(f"Error processing GPU processes: {e}, type: {type(e).__name__}, details: {str(e)}")

    except ImportError:
        # nvitop not available, fallback to nvidia-smi
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw,power.limit',
                                   '--format=csv,noheader,nounits'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        gpu_info['available'] = True
                        gpu_info['type'] = 'NVIDIA'
                        gpu_info['details'][f'gpu_{i}'] = {
                            'name': parts[0],
                            'memory_total': int(float(parts[1])) if parts[1] and parts[1] != 'N/A' else 0,
                            'memory_used': int(float(parts[2])) if parts[2] and parts[2] != 'N/A' else 0,
                            'memory_free': int(float(parts[3])) if parts[3] and parts[3] != 'N/A' else 0,
                            'utilization': int(float(parts[4])) if parts[4] and parts[4] != 'N/A' else 0,
                            'temperature': float(parts[5]) if len(parts) > 5 and parts[5] and parts[5] != 'N/A' else None,
                            'power_usage': float(parts[6]) if len(parts) > 6 and parts[6] and parts[6] != 'N/A' else None,  # nvidia-smi returns watts directly
                            'power_limit': float(parts[7]) if len(parts) > 7 and parts[7] and parts[7] != 'N/A' else None,  # nvidia-smi returns watts directly
                        }
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
    except Exception as e:
        print(f"Error checking GPU: {e}")

    return gpu_info