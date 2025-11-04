from __future__ import annotations

import platform

import psutil


def display_system_usage() -> str:
    """Return a formatted string describing system resource usage."""
    lines = ["\n当前系统资源使用情况：\n"]

    cpu_name = platform.processor() or "CPU 信息不可用"
    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)

    lines.append(f"CPU 型号: {cpu_name}")
    lines.append(f"CPU 核心数: {physical_cores} 物理核心 / {logical_cores} 逻辑核心")
    lines.append(f"CPU 使用率: {psutil.cpu_percent()}%")

    cpu_freq = psutil.cpu_freq()
    if cpu_freq:
        lines.append(
            f"CPU 频率: {cpu_freq.current:.2f} MHz (最小: {cpu_freq.min:.2f} MHz, 最大: {cpu_freq.max:.2f} MHz)"
        )

    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    lines.append(f"{name} 温度: {entry.current}°C")
        else:
            lines.append("温度信息不可用")
    except AttributeError:
        lines.append("温度信息不可用")

    virtual_mem = psutil.virtual_memory()
    lines.append(f"内存总大小: {virtual_mem.total / (1024 ** 3):.2f} GB")
    lines.append(f"内存使用率: {virtual_mem.percent}%")
    lines.append(
        f"内存已使用: {virtual_mem.used / (1024 ** 3):.2f} GB / 可用: {virtual_mem.available / (1024 ** 3):.2f} GB"
    )

    disk_usage = psutil.disk_usage("/")
    total_gb = disk_usage.total / (1024 ** 3)
    free_gb = disk_usage.free / (1024 ** 3)
    used_gb = total_gb - free_gb
    usage_percent = (used_gb / total_gb) * 100

    lines.append(f"磁盘总大小: {total_gb:.2f} GB")
    lines.append(f"磁盘空余量: {free_gb:.2f} GB")
    lines.append(f"磁盘已使用: {used_gb:.2f} GB")
    lines.append(f"磁盘使用率: {usage_percent:.1f}%")

    return "\n".join(lines)
