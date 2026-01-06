"""
Network Data Validation System - Service Controller
Windows için start, stop, restart, status komutları
"""
import os
import sys
import time
import signal
import subprocess
import psutil

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(BASE_DIR, "service.pid")
LOG_FILE = os.path.join(BASE_DIR, "service.log")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")


def get_pid():
    """PID dosyasından process ID'yi oku."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None
    return None


def is_running(pid):
    """Process'in çalışıp çalışmadığını kontrol et."""
    if pid is None:
        return False
    try:
        process = psutil.Process(pid)
        # Python process mi ve bizim script mi kontrol et
        cmdline = ' '.join(process.cmdline()).lower()
        return process.is_running() and 'main.py' in cmdline and '--schedule' in cmdline
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def write_pid(pid):
    """PID'yi dosyaya yaz."""
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def remove_pid():
    """PID dosyasını sil."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def start_service():
    """Servisi başlat."""
    pid = get_pid()
    if is_running(pid):
        print(f"⚠️  Servis zaten çalışıyor (PID: {pid})")
        return False
    
    # Eski PID dosyasını temizle
    remove_pid()
    
    print("🚀 Servis başlatılıyor...")
    
    # Windows'ta arka planda başlat
    # CREATE_NO_WINDOW flag'i ile pencere açılmadan çalışır
    CREATE_NO_WINDOW = 0x08000000
    
    # Log dosyasına yönlendir
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f"\n{'='*60}\n")
        log.write(f"Servis başlatıldı: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"{'='*60}\n")
    
    # pythonw.exe kullanarak pencere açmadan başlat
    python_exe = sys.executable
    pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
    
    # pythonw varsa onu kullan, yoksa normal python ile arka planda çalıştır
    if os.path.exists(pythonw_exe):
        process = subprocess.Popen(
            [pythonw_exe, MAIN_SCRIPT, '--schedule'],
            cwd=BASE_DIR,
            stdout=open(LOG_FILE, 'a', encoding='utf-8'),
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW
        )
    else:
        process = subprocess.Popen(
            [python_exe, MAIN_SCRIPT, '--schedule'],
            cwd=BASE_DIR,
            stdout=open(LOG_FILE, 'a', encoding='utf-8'),
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW
        )
    
    # PID'yi kaydet
    write_pid(process.pid)
    
    # Biraz bekle ve kontrol et
    time.sleep(2)
    
    if is_running(process.pid):
        print(f"✅ Servis başarıyla başlatıldı (PID: {process.pid})")
        print(f"📝 Log dosyası: {LOG_FILE}")
        print(f"\n📅 Zamanlama: Her gün 09:30 ve 17:30")
        return True
    else:
        print("❌ Servis başlatılamadı. Log dosyasını kontrol edin.")
        remove_pid()
        return False


def stop_service():
    """Servisi durdur."""
    pid = get_pid()
    
    if not is_running(pid):
        print("⚠️  Servis zaten çalışmıyor")
        remove_pid()
        return True
    
    print(f"🛑 Servis durduruluyor (PID: {pid})...")
    
    try:
        process = psutil.Process(pid)
        
        # Önce nazikçe kapat
        process.terminate()
        
        # 5 saniye bekle
        try:
            process.wait(timeout=5)
        except psutil.TimeoutExpired:
            # Hala çalışıyorsa zorla kapat
            print("   Zorla kapatılıyor...")
            process.kill()
            process.wait(timeout=3)
        
        remove_pid()
        
        # Log'a yaz
        with open(LOG_FILE, 'a', encoding='utf-8') as log:
            log.write(f"\nServis durduruldu: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print("✅ Servis başarıyla durduruldu")
        return True
        
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"❌ Servis durdurulamadı: {e}")
        remove_pid()
        return False


def restart_service():
    """Servisi yeniden başlat."""
    print("🔄 Servis yeniden başlatılıyor...")
    stop_service()
    time.sleep(1)
    return start_service()


def status_service():
    """Servis durumunu göster."""
    pid = get_pid()
    
    print("\n" + "=" * 50)
    print("   Network Data Validation System - Durum")
    print("=" * 50)
    
    if is_running(pid):
        try:
            process = psutil.Process(pid)
            create_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                       time.localtime(process.create_time()))
            memory = process.memory_info().rss / 1024 / 1024  # MB
            
            print(f"\n🟢 Durum: ÇALIŞIYOR")
            print(f"   PID: {pid}")
            print(f"   Başlangıç: {create_time}")
            print(f"   Bellek: {memory:.1f} MB")
            print(f"\n📅 Zamanlama: Her gün 09:30 ve 17:30")
            print(f"📝 Log: {LOG_FILE}")
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"\n🔴 Durum: DURMUŞ")
    else:
        print(f"\n🔴 Durum: DURMUŞ")
    
    # Son log satırlarını göster
    if os.path.exists(LOG_FILE):
        print(f"\n📋 Son log kayıtları:")
        print("-" * 50)
        try:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")
        except Exception as e:
            print(f"   Log okunamadı: {e}")
    
    print("\n" + "=" * 50)


def show_logs(lines=50):
    """Log dosyasını göster."""
    if not os.path.exists(LOG_FILE):
        print("📝 Henüz log dosyası yok")
        return
    
    print(f"\n📋 Son {lines} log satırı ({LOG_FILE}):")
    print("=" * 60)
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line.rstrip())
    except Exception as e:
        print(f"Log okunamadı: {e}")


def print_help():
    """Yardım mesajını göster."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║     Network Data Validation System - Servis Kontrolü         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Kullanım: python service.py <komut>                         ║
║                                                              ║
║  Komutlar:                                                   ║
║    start    - Servisi başlat (arka planda çalışır)          ║
║    stop     - Servisi durdur                                 ║
║    restart  - Servisi yeniden başlat                         ║
║    status   - Servis durumunu göster                         ║
║    logs     - Son log kayıtlarını göster                     ║
║                                                              ║
║  Zamanlama: Her gün 09:30 ve 17:30'da çalışır               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    """Ana fonksiyon."""
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        start_service()
    elif command == 'stop':
        stop_service()
    elif command == 'restart':
        restart_service()
    elif command == 'status':
        status_service()
    elif command == 'logs':
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        show_logs(lines)
    elif command in ['help', '--help', '-h']:
        print_help()
    else:
        print(f"❌ Bilinmeyen komut: {command}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
