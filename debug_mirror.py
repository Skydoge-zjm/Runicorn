#!/usr/bin/env python3
"""
Mirror同步调试脚本
用于检查Mirror任务是否正常运行
"""

import requests
import time
import json

VIEWER_URL = "http://localhost:23300"

def check_mirror_status():
    """检查Mirror任务状态"""
    print("\n" + "="*60)
    print("Mirror 同步状态诊断")
    print("="*60)
    
    try:
        # 1. 检查Viewer是否运行
        print("\n[1] 检查Viewer状态...")
        resp = requests.get(f"{VIEWER_URL}/api/health", timeout=5)
        if resp.status_code == 200:
            print("✓ Viewer 运行正常")
        else:
            print(f"✗ Viewer 响应异常: {resp.status_code}")
            return
    except Exception as e:
        print(f"✗ 无法连接Viewer: {e}")
        print("请先运行: runicorn viewer")
        return
    
    # 2. 检查Mirror任务
    print("\n[2] 检查Mirror任务...")
    try:
        resp = requests.get(f"{VIEWER_URL}/api/ssh/mirror/list", timeout=5)
        data = resp.json()
        mirrors = data.get("mirrors", [])
        
        if not mirrors:
            print("✗ 没有活跃的Mirror任务")
            print("请在前端创建SSH连接并启动Mirror同步")
            return
        
        print(f"✓ 找到 {len(mirrors)} 个Mirror任务\n")
        
        for idx, mirror in enumerate(mirrors, 1):
            print(f"--- Mirror #{idx} ---")
            print(f"  ID: {mirror.get('id')}")
            print(f"  Host: {mirror.get('host')}")
            print(f"  Remote: {mirror.get('remote_root')}")
            print(f"  Local: {mirror.get('local_root')}")
            print(f"  间隔: {mirror.get('interval')}秒")
            print(f"  扫描次数: {mirror.get('scans', 0)}")
            print(f"  已复制文件: {mirror.get('copied_files', 0)}")
            print(f"  线程存活: {mirror.get('alive', False)}")
            
            if mirror.get('last_error'):
                print(f"  ⚠ 最后错误: {mirror['last_error'][:100]}")
            print()
            
    except Exception as e:
        print(f"✗ 获取Mirror列表失败: {e}")
        return
    
    # 3. 实时监控
    print("\n[3] 实时监控 (每5秒刷新, Ctrl+C退出)...")
    try:
        last_scans = {}
        while True:
            time.sleep(5)
            
            resp = requests.get(f"{VIEWER_URL}/api/ssh/mirror/list", timeout=5)
            mirrors = resp.json().get("mirrors", [])
            
            print(f"\n[{time.strftime('%H:%M:%S')}] 状态更新:")
            for mirror in mirrors:
                mid = mirror.get('id')
                scans = mirror.get('scans', 0)
                files = mirror.get('copied_files', 0)
                alive = mirror.get('alive', False)
                
                # 检查是否有新扫描
                last = last_scans.get(mid, 0)
                if scans > last:
                    status = f"✓ 新扫描 #{scans}"
                    last_scans[mid] = scans
                else:
                    status = f"⏸ 无变化 (上次扫描#{scans})"
                
                if not alive:
                    status = "✗ 线程已停止!"
                
                print(f"  Mirror {mid[:20]}... - {status} - 文件:{files}")
                
    except KeyboardInterrupt:
        print("\n\n监控已停止")
    except Exception as e:
        print(f"\n✗ 监控出错: {e}")

if __name__ == "__main__":
    check_mirror_status()
