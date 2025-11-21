"""
Log Manager for Medical Receipt Extraction System
จัดการ logs แยกตามวันที่และเก็บแค่ 30 วัน
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timedelta
import os
import glob
from typing import Dict, Any, Optional


class LogManager:
    """จัดการระบบ logging ด้วย rotation ตามวันที่และ cleanup อัตโนมัติ"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_dir = Path(config.get('log_directory', './logs'))
        self.max_days = config.get('max_days', 30)
        self.log_level = getattr(logging, config.get('level', 'INFO').upper())
        self.log_format = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # สร้าง directory ถ้ายังไม่มี
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Cleanup logs เก่าๆ
        self._cleanup_old_logs()

        # ตั้งค่า root logger
        self._setup_root_logger()

    def _setup_root_logger(self):
        """ตั้งค่า root logger ด้วย file rotation"""

        # สร้าง logger
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

        # ลบ handlers เดิม (ถ้ามี)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # สร้าง formatter
        formatter = logging.Formatter(self.log_format)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler ด้วย daily rotation
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f'pipeline_{today}.log'

        # ใช้ RotatingFileHandler เพื่อจัดการขนาดไฟล์
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB per file
            backupCount=5,  # เก็บ 5 ไฟล์ backup
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # สร้าง logger สำหรับ security แยกต่างหาก
        self._setup_security_logger()

    def _setup_security_logger(self):
        """ตั้งค่า security logger แยกต่างหาก"""
        security_logger = logging.getLogger('security')
        security_logger.setLevel(self.log_level)

        # ลบ handlers เดิม (ถ้ามี)
        for handler in security_logger.handlers[:]:
            security_logger.removeHandler(handler)

        # สร้าง formatter สำหรับ security
        formatter = logging.Formatter(
            '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
        )

        # Security file handler
        today = datetime.now().strftime('%Y-%m-%d')
        security_log_file = self.log_dir / f'security_{today}.log'

        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=5*1024*1024,  # 5MB per file
            backupCount=3,  # เก็บ 3 ไฟล์ backup
            encoding='utf-8'
        )
        security_handler.setFormatter(formatter)
        security_logger.addHandler(security_handler)

        # ไม่ propagate ไป parent logger
        security_logger.propagate = False

    def _cleanup_old_logs(self):
        """ลบ log files ที่เก่ากว่า max_days"""

        if not self.log_dir.exists():
            return

        # คำนวณวันที่ cutoff
        cutoff_date = datetime.now() - timedelta(days=self.max_days)

        # หาไฟล์ log เก่าๆ
        log_patterns = [
            'pipeline_*.log',
            'security_*.log',
            'pipeline_*.log.*',
            'security_*.log.*',
            '*.log'  # สำหรับไฟล์ log เก่าๆ ที่ไม่มี pattern ใหม่
        ]

        deleted_count = 0

        for pattern in log_patterns:
            for log_file in self.log_dir.glob(pattern):
                try:
                    # ตรวจสอบวันที่จากชื่อไฟล์
                    if self._is_file_too_old(log_file, cutoff_date):
                        log_file.unlink()
                        deleted_count += 1
                        print(f"Deleted old log file: {log_file.name}")
                except Exception as e:
                    print(f"Error deleting {log_file}: {e}")

        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} old log files (keeping last {self.max_days} days)")

    def _is_file_too_old(self, log_file: Path, cutoff_date: datetime) -> bool:
        """ตรวจสอบว่าไฟล์ log เก่ากว่า cutoff date หรือไม่"""

        try:
            # ดึงวันที่จากชื่อไฟล์ (format: pipeline_2024-01-15.log)
            filename = log_file.stem  # ตัด .log ออก

            # จับวันที่จากชื่อไฟล์
            date_str = None
            if '_20' in filename:  # มี pattern วันที่
                parts = filename.split('_')
                for part in parts:
                    if len(part) == 10 and part.count('-') == 2:  # format YYYY-MM-DD
                        date_str = part
                        break

            if date_str:
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                return file_date < cutoff_date
            else:
                # ถ้าไม่มีวันที่ในชื่อไฟล์ ตรวจสอบจาก mtime
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                return file_mtime < cutoff_date

        except Exception:
            # ถ้าพระลัยอะไรไม่ได้ ตรวจสอบจาก mtime
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                return file_mtime < cutoff_date
            except:
                return False  # ถ้าลบไม่ได้ ก็ปล่อยไว้

    def get_current_log_files(self) -> Dict[str, str]:
        """ส่งคืน path ของ log files ปัจจุบัน"""
        today = datetime.now().strftime('%Y-%m-%d')

        return {
            'pipeline': str(self.log_dir / f'pipeline_{today}.log'),
            'security': str(self.log_dir / f'security_{today}.log')
        }

    def get_log_stats(self) -> Dict[str, Any]:
        """ส่งคืนสถิติของ log files"""

        if not self.log_dir.exists():
            return {'total_files': 0, 'total_size': 0, 'oldest_file': None, 'newest_file': None}

        log_files = list(self.log_dir.glob('*.log*'))
        total_size = sum(f.stat().st_size for f in log_files if f.exists())

        if not log_files:
            return {'total_files': 0, 'total_size': 0, 'oldest_file': None, 'newest_file': None}

        # หาไฟล์ที่เก่าที่สุดและใหม่ที่สุด
        files_with_mtime = [(f, f.stat().st_mtime) for f in log_files if f.exists()]
        files_with_mtime.sort(key=lambda x: x[1])

        oldest_file = datetime.fromtimestamp(files_with_mtime[0][1]).strftime('%Y-%m-%d %H:%M:%S')
        newest_file = datetime.fromtimestamp(files_with_mtime[-1][1]).strftime('%Y-%m-%d %H:%M:%S')

        return {
            'total_files': len(log_files),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024*1024), 2),
            'oldest_file': oldest_file,
            'newest_file': newest_file
        }


# Global instance
_log_manager = None


def get_log_manager(config: Optional[Dict[str, Any]] = None) -> LogManager:
    """Get or create global log manager instance"""

    global _log_manager

    if _log_manager is None:
        if config is None:
            # Default config
            config = {
                'log_directory': './logs',
                'max_days': 30,
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }

        _log_manager = LogManager(config)

    return _log_manager


def setup_logging(config: Optional[Dict[str, Any]] = None):
    """Convenience function to setup logging"""
    return get_log_manager(config)


# สำหรับการใช้งานใน main scripts
if __name__ == "__main__":
    # Test log manager
    config = {
        'log_directory': './logs',
        'max_days': 30,
        'level': 'INFO'
    }

    manager = get_log_manager(config)
    logger = logging.getLogger(__name__)

    logger.info("🧪 Testing Log Manager")
    logger.info("📊 Log statistics: " + str(manager.get_log_stats()))
    logger.info("📁 Current log files: " + str(manager.get_current_log_files()))

    # Test security logger
    security_logger = logging.getLogger('security')
    security_logger.warning("🚨 Test security log entry")
    security_logger.error("🚨 Test security error entry")

    print("✅ Log Manager test completed")
