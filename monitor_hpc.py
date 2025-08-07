#!/usr/bin/env python3
"""
High-Performance Pipeline Monitoring Script

Monitors system resources, pipeline performance, and provides real-time statistics
for the quantum circuit processing pipeline running on HPC hardware.
"""

import time
import json
import psutil
import os
from datetime import datetime, timedelta
from pathlib import Path
import argparse

def get_system_stats():
    """Get current system resource usage"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('.')
    
    # Get per-core CPU usage
    cpu_per_core = psutil.cpu_percent(percpu=True)
    
    # Get process count
    python_processes = len([p for p in psutil.process_iter(['name']) if 'python' in p.info['name'].lower()])
    
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu': {
            'total_percent': cpu_percent,
            'per_core': cpu_per_core,
            'core_count': psutil.cpu_count()
        },
        'memory': {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percent': memory.percent
        },
        'disk': {
            'total_gb': disk.total / (1024**3),
            'free_gb': disk.free / (1024**3),
            'used_gb': disk.used / (1024**3),
            'percent': (disk.used / disk.total) * 100
        },
        'processes': {
            'python_count': python_processes,
            'total_count': len(list(psutil.process_iter()))
        }
    }

def get_pipeline_stats():
    """Get pipeline-specific statistics"""
    circuits_dir = Path('./circuits_hpc')
    if not circuits_dir.exists():
        circuits_dir = Path('./circuits')
    
    if circuits_dir.exists():
        # Count circuit files
        circuit_count = len(list(circuits_dir.glob('*/meta.json')))
        
        # Calculate total storage used
        total_size = sum(f.stat().st_size for f in circuits_dir.rglob('*') if f.is_file())
        total_size_gb = total_size / (1024**3)
        
        # Get newest and oldest circuits
        meta_files = list(circuits_dir.glob('*/meta.json'))
        if meta_files:
            newest = max(meta_files, key=lambda f: f.stat().st_mtime)
            oldest = min(meta_files, key=lambda f: f.stat().st_mtime)
            
            newest_time = datetime.fromtimestamp(newest.stat().st_mtime)
            oldest_time = datetime.fromtimestamp(oldest.stat().st_mtime)
        else:
            newest_time = oldest_time = None
    else:
        circuit_count = 0
        total_size_gb = 0
        newest_time = oldest_time = None
    
    return {
        'circuit_count': circuit_count,
        'storage_used_gb': total_size_gb,
        'newest_circuit': newest_time.isoformat() if newest_time else None,
        'oldest_circuit': oldest_time.isoformat() if oldest_time else None
    }

def analyze_log_file(log_file='pipeline.log'):
    """Analyze pipeline log file for performance metrics including Azure uploads"""
    if not os.path.exists(log_file):
        return {'error': 'Log file not found'}
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Look for batch completion messages
        batch_lines = [line for line in lines if 'Batch' in line and '✓' in line]
        
        # Look for Azure upload messages
        azure_lines = [line for line in lines if 'Azure:' in line or 'Uploaded' in line]
        
        stats = {}
        
        if batch_lines:
            latest_batch = batch_lines[-1]
            # Enhanced format: "Batch X: Y✓/Z✗ | Total: A✓/B✗ | Rate: C/min | CPU: D% | RAM: E% | Disk: FGB | Azure: G↑ | Buffer: H"
            
            parts = latest_batch.split('|')
            
            for part in parts:
                part = part.strip()
                if 'Total:' in part:
                    # Extract total successful/failed
                    total_part = part.split('Total:')[1].strip()
                    if '✓' in total_part and '✗' in total_part:
                        success = int(total_part.split('✓')[0])
                        failed = int(total_part.split('✓')[1].split('✗')[0].replace('/', ''))
                        stats['total_successful'] = success
                        stats['total_failed'] = failed
                        stats['success_rate'] = success / (success + failed) * 100 if (success + failed) > 0 else 0
                
                elif 'Rate:' in part:
                    # Extract processing rate
                    rate_str = part.split('Rate:')[1].strip().split('/min')[0]
                    try:
                        stats['rate_per_minute'] = float(rate_str)
                    except ValueError:
                        pass
                
                elif 'Azure:' in part:
                    # Extract Azure upload count
                    azure_part = part.split('Azure:')[1].strip()
                    if '↑' in azure_part:
                        try:
                            uploaded = int(azure_part.split('↑')[0])
                            stats['azure_uploaded'] = uploaded
                        except ValueError:
                            pass
                
                elif 'Buffer:' in part:
                    # Extract buffer size
                    buffer_str = part.split('Buffer:')[1].strip()
                    try:
                        stats['upload_buffer_size'] = int(buffer_str)
                    except ValueError:
                        pass
        
        # Count recent Azure upload events
        recent_uploads = len([line for line in lines[-100:] if 'Uploaded' in line and 'circuits to Azure' in line])
        if recent_uploads > 0:
            stats['recent_azure_uploads'] = recent_uploads
        
        return stats if stats else {'error': 'No batch statistics found in log'}
    
    except Exception as e:
        return {'error': f'Error reading log file: {e}'}

def print_dashboard(stats, pipeline_stats, log_stats):
    """Print a real-time dashboard"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("🖥️  HIGH-PERFORMANCE QUANTUM CIRCUIT PIPELINE MONITOR")
    print("=" * 80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # System Resources
    print("💻 SYSTEM RESOURCES")
    print("-" * 40)
    print(f"CPU Usage:    {stats['cpu']['total_percent']:6.1f}% ({stats['cpu']['core_count']} cores)")
    print(f"Memory:       {stats['memory']['percent']:6.1f}% ({stats['memory']['used_gb']:.1f}GB / {stats['memory']['total_gb']:.1f}GB)")
    print(f"Disk Usage:   {stats['disk']['percent']:6.1f}% ({stats['disk']['free_gb']:.1f}GB free)")
    print(f"Python Procs: {stats['processes']['python_count']:6d}")
    print()
    
    # Pipeline Statistics
    print("⚡ PIPELINE STATISTICS")
    print("-" * 40)
    print(f"Circuits:     {pipeline_stats['circuit_count']:6d} total (local)")
    print(f"Storage:      {pipeline_stats['storage_used_gb']:6.1f}GB used (local)")
    
    if 'total_successful' in log_stats:
        print(f"Successful:   {log_stats['total_successful']:6d}")
        print(f"Failed:       {log_stats['total_failed']:6d}")
        print(f"Success Rate: {log_stats['success_rate']:6.1f}%")
        
        if 'rate_per_minute' in log_stats:
            print(f"Rate:         {log_stats['rate_per_minute']:6.1f} circuits/min")
    
    # Azure/Remote Storage Statistics
    if 'azure_uploaded' in log_stats:
        print(f"Azure Upload: {log_stats['azure_uploaded']:6d} circuits")
        
    if 'upload_buffer_size' in log_stats:
        print(f"Upload Buffer:{log_stats['upload_buffer_size']:6d} pending")
        
    if 'recent_azure_uploads' in log_stats:
        print(f"Recent Uploads:{log_stats['recent_azure_uploads']:5d} batches")
    
    print()
    
    # Resource Alerts
    alerts = []
    if stats['cpu']['total_percent'] > 95:
        alerts.append("🔥 HIGH CPU USAGE")
    if stats['memory']['percent'] > 90:
        alerts.append("🔥 HIGH MEMORY USAGE")
    if stats['disk']['percent'] > 95:
        alerts.append("🔥 LOW DISK SPACE")
    
    if alerts:
        print("⚠️  ALERTS")
        print("-" * 40)
        for alert in alerts:
            print(alert)
        print()
    
    # Performance Tips
    print("💡 PERFORMANCE TIPS")
    print("-" * 40)
    if stats['cpu']['total_percent'] < 70:
        print("• CPU usage is low - consider increasing batch size")
    if stats['memory']['percent'] < 50:
        print("• Memory usage is low - consider increasing max_qubits")
    if pipeline_stats['storage_used_gb'] > 50:
        print("• Storage usage is high - consider enabling cleanup")
    
    print()
    print("Press Ctrl+C to exit monitoring")

def save_stats_to_file(stats, pipeline_stats, log_stats, filename='performance_log.json'):
    """Save statistics to JSON file for historical analysis"""
    combined_stats = {
        'timestamp': stats['timestamp'],
        'system': stats,
        'pipeline': pipeline_stats,
        'log_analysis': log_stats
    }
    
    # Append to existing file or create new one
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    data.append(combined_stats)
    
    # Keep only last 1000 entries to prevent file from growing too large
    if len(data) > 1000:
        data = data[-1000:]
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Monitor HPC Pipeline Performance')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    parser.add_argument('--log-file', default='pipeline.log', help='Pipeline log file to analyze')
    parser.add_argument('--save-stats', action='store_true', help='Save statistics to JSON file')
    parser.add_argument('--no-dashboard', action='store_true', help='Disable real-time dashboard')
    
    args = parser.parse_args()
    
    print(f"Starting pipeline monitor (update interval: {args.interval}s)")
    
    try:
        while True:
            # Collect statistics
            system_stats = get_system_stats()
            pipeline_stats = get_pipeline_stats()
            log_stats = analyze_log_file(args.log_file)
            
            # Display dashboard
            if not args.no_dashboard:
                print_dashboard(system_stats, pipeline_stats, log_stats)
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')} - "
                      f"CPU: {system_stats['cpu']['total_percent']:.1f}% | "
                      f"RAM: {system_stats['memory']['percent']:.1f}% | "
                      f"Circuits: {pipeline_stats['circuit_count']}")
            
            # Save statistics
            if args.save_stats:
                save_stats_to_file(system_stats, pipeline_stats, log_stats)
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped")

if __name__ == "__main__":
    main()