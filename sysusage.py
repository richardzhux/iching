import psutil
import platform

def display_system_usage():
    """Display detailed system information, including CPU, RAM, and disk usage."""
    print("\n当前系统资源使用情况：\n")

    # CPU Information
    cpu_name = platform.processor() or "CPU 信息不可用"
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)
    print(f"CPU 型号: {cpu_name}")
    print(f"CPU 核心数: {physical_cores} 物理核心 / {logical_cores} 逻辑核心")
    print(f"CPU 使用率: {psutil.cpu_percent()}%")
    
    cpu_freq = psutil.cpu_freq()
    if cpu_freq:
        print(f"CPU 频率: {cpu_freq.current:.2f} MHz (最小: {cpu_freq.min:.2f} MHz, 最大: {cpu_freq.max:.2f} MHz)")
    try:
        # CPU temperature (may not be available on all systems)
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    print(f"{name} 温度: {entry.current}°C\n")
        else:
            print("温度信息不可用\n")
    except AttributeError:
        print("温度信息不可用\n")

    # Memory (RAM) Usage
    virtual_mem = psutil.virtual_memory()
    print(f"内存总大小: {virtual_mem.total / (1024 ** 3):.2f} GB")
    print(f"内存使用率: {virtual_mem.percent}%")
    print(f"内存已使用: {virtual_mem.used / (1024 ** 3):.2f} GB / 可用: {virtual_mem.available / (1024 ** 3):.2f} GB\n")

    # Disk Usage
    disk_usage = psutil.disk_usage('/')
    total_gb = disk_usage.total / (1024 ** 3)
    free_gb = disk_usage.free / (1024 ** 3)
    used_gb = total_gb - free_gb
    usage_percent = (used_gb / total_gb) * 100

    print(f"磁盘总大小: {total_gb:.2f} GB")
    print(f"磁盘空余量: {free_gb:.2f} GB")
    print(f"磁盘已使用: {used_gb:.2f} GB")
    print(f"磁盘使用率: {usage_percent:.1f}%")
