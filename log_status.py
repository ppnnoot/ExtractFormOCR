#!/usr/bin/env python3
"""
แสดงสถานะ logs ปัจจุบัน
"""

import json
from log_manager import get_log_manager

def main():
    # โหลด config
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # เริ่ม log manager
    manager = get_log_manager(config['logging'])

    print("=== LOG MANAGEMENT STATUS ===")
    print(f"Log Directory: {config['logging']['log_directory']}")
    print(f"Max Retention: {config['logging']['max_days']} days")
    print()

    # แสดงไฟล์ปัจจุบัน
    current_files = manager.get_current_log_files()
    print("Current Log Files:")
    print(f"  Pipeline: {current_files['pipeline']}")
    print(f"  Security: {current_files['security']}")
    print()

    # แสดงสถิติ
    stats = manager.get_log_stats()
    print("Log Statistics:")
    print(f"  Total Files: {stats['total_files']}")
    print(f"  Total Size: {stats['total_size_mb']} MB")
    print(f"  Date Range: {stats['oldest_file']} to {stats['newest_file']}")
    print()

    print("=== LOG ROTATION & CLEANUP ===")
    print(f"Rotation: {config['logging']['rotation']['max_bytes'] // (1024*1024)} MB per file")
    print(f"Backup Count: {config['logging']['rotation']['backup_count']} files")
    print(f"Auto Cleanup: {'Enabled' if config['logging']['cleanup']['enabled'] else 'Disabled'}")

if __name__ == "__main__":
    main()
