#!/usr/bin/env python3
"""
GitHub Cloudflare 全自动加速配置工具
License: MIT
Repository: （填写你的GitHub仓库地址）
Dependencies: Python 3.6+ (仅使用Python标准库，无第三方依赖)
"""

import os
import sys
import json
import subprocess
import shutil
import platform
import socket
import urllib.request
import threading
import time
import ctypes
from pathlib import Path
from typing import Optional, Tuple

# ========== 全局常量 ==========
CONFIG_FILE = Path.home() / ".github_cf_proxy_config.json"
SCRIPT_PATH = Path(__file__).resolve()
OS_TYPE = platform.system().lower()
# 测速配置：走加速代理的GitHub小文件（仅10KB以内，无流量负担）
SPEED_TEST_URL = "/raw/octocat/Hello-World/master/README"
# 状态栏刷新间隔（秒）
STATUS_REFRESH_INTERVAL = 2
# 测速超时时间（秒）
TEST_TIMEOUT = 5


class GitHubCFProxy:
    def __init__(self):
        # 基础配置
        self.config = self._load_config()
        self.worker_domain = self.config.get("worker_domain", "")
        self.auto_start_enabled = self.config.get("auto_start", False)
        # 状态栏相关配置
        self.status_bar_enabled = self.config.get("status_bar_enabled", False)
        self._terminal_inited = False
        # 网速/延迟状态变量（后台线程更新）
        self._current_speed: str = "-- MB/s"
        self._current_delay: str = "-- ms"
        self._speed_thread: Optional[threading.Thread] = None
        self._thread_stop_flag = threading.Event()
        self._thread_lock = threading.Lock()

    def _load_config(self):
        """加载本地配置文件"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[警告] 配置文件损坏，将重置: {e}")
        return {}

    def _save_config(self):
        """保存配置到本地"""
        self.config["worker_domain"] = self.worker_domain
        self.config["auto_start"] = self.auto_start_enabled
        self.config["status_bar_enabled"] = self.status_bar_enabled
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[错误] 保存配置失败: {e}")
            return False

    def _init_terminal(self):
        """初始化终端，开启Windows ANSI支持，跨终端兼容"""
        if self._terminal_inited:
            return
        # Windows开启虚拟终端ANSI支持
        if OS_TYPE == "windows":
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, ctypes.c_ulong(mode.value | 0x0004))
        # 隐藏光标（状态栏模式）
        if self.status_bar_enabled:
            print("\033[?25l", end="")
        self._terminal_inited = True

    def _reset_terminal(self):
        """退出时重置终端状态"""
        # 恢复光标
        print("\033[?25h", end="")
        # 清除状态栏行
        print("\r\033[K", end="", flush=True)

    def _test_node_delay(self) -> int:
        """测试Cloudflare代理节点TCP延迟（ms），无权限要求，跨平台兼容"""
        if not self.worker_domain:
            return -1
        try:
            # 提取域名，去掉https://前缀
            host = self.worker_domain.replace("https://", "").replace("http://", "").split("/")[0]
            port = 443
            start_time = time.time()
            # 建立TCP连接，测握手延迟
            sock = socket.create_connection((host, port), timeout=TEST_TIMEOUT)
            sock.close()
            delay = int((time.time() - start_time) * 1000)
            return delay if delay > 0 else 0
        except Exception:
            return -1

    def _test_download_speed(self) -> Tuple[float, str]:
        """测试加速链路下载速率，返回字节数+格式化字符串"""
        if not self.worker_domain:
            return 0, "-- MB/s"
        try:
            test_url = f"{self.worker_domain}{SPEED_TEST_URL}"
            start_time = time.time()
            # 仅下载前10KB，无流量负担
            req = urllib.request.Request(test_url, method="GET", headers={"Range": "bytes=0-10240"})
            with urllib.request.urlopen(req, timeout=TEST_TIMEOUT) as resp:
                data = resp.read()
                download_size = len(data)
                cost_time = time.time() - start_time
                if cost_time <= 0:
                    return 0, "-- MB/s"
                # 计算速率
                speed_bps = download_size / cost_time
                # 格式化单位
                if speed_bps < 1024:
                    speed_str = f"{speed_bps:.2f} B/s"
                elif speed_bps < 1024 * 1024:
                    speed_str = f"{speed_bps/1024:.2f} KB/s"
                else:
                    speed_str = f"{speed_bps/(1024*1024):.2f} MB/s"
                return speed_bps, speed_str
        except Exception:
            return 0, "-- MB/s"

    def _speed_monitor_worker(self):
        """后台网速/延迟监控线程，不阻塞主线程输入"""
        while not self._thread_stop_flag.is_set():
            if not self.worker_domain or not self.status_bar_enabled:
                time.sleep(STATUS_REFRESH_INTERVAL)
                continue
            # 测延迟和速率
            delay = self._test_node_delay()
            speed_bps, speed_str = self._test_download_speed()
            # 线程安全更新变量
            with self._thread_lock:
                self._current_speed = speed_str
                self._current_delay = f"{delay} ms" if delay >= 0 else "-- ms"
            # 按间隔刷新
            time.sleep(STATUS_REFRESH_INTERVAL)

    def _start_speed_monitor(self):
        """启动后台监控线程"""
        if self._speed_thread and self._speed_thread.is_alive():
            return
        self._thread_stop_flag.clear()
        self._speed_thread = threading.Thread(target=self._speed_monitor_worker, daemon=True)
        self._speed_thread.start()

    def _stop_speed_monitor(self):
        """停止后台监控线程"""
        self._thread_stop_flag.set()
        if self._speed_thread and self._speed_thread.is_alive():
            self._speed_thread.join(timeout=1)

    def _render_status_bar(self):
        """渲染状态栏，仅在开启状态下生效"""
        if not self.status_bar_enabled:
            return
        # 线程安全读取状态
        with self._thread_lock:
            speed = self._current_speed
            delay = self._current_delay
        # 加速状态
        accelerate_status = "已启用" if self.worker_domain else "未配置"
        auto_start_status = "自启已开" if self.auto_start_enabled else "自启已关"
        # 状态栏内容
        status_content = f"[加速状态: {accelerate_status}] | [实时速率: {speed}] | [节点延迟: {delay}] | [{auto_start_status}]"
        # 终端宽度适配，超出截断
        try:
            terminal_width = os.get_terminal_size().columns
        except Exception:
            terminal_width = 80
        if len(status_content) > terminal_width - 2:
            status_content = status_content[:terminal_width - 5] + "..."
        # ANSI渲染：行首清除+状态栏+固定行，不影响菜单内容
        print(f"\r\033[K\033[38;5;47m{status_content}\033[0m\n\033[F", end="", flush=True)

    def toggle_status_bar(self):
        """切换状态栏显示/隐藏，主菜单入口"""
        self.status_bar_enabled = not self.status_bar_enabled
        self._save_config()
        if self.status_bar_enabled:
            self._init_terminal()
            self._start_speed_monitor()
            print("[√] 实时网速状态栏已开启，将在主菜单常驻显示")
        else:
            self._stop_speed_monitor()
            self._reset_terminal()
            print("[√] 实时网速状态栏已隐藏")

    def _check_git(self):
        """检查Git是否安装"""
        if not shutil.which("git"):
            print("[错误] 未找到Git！请先安装Git并添加到系统环境变量（PATH）")
            sys.exit(1)
        print("[√] Git环境检测正常")

    def _set_git_credential_helper(self):
        """配置Git凭证助手（自动保存用户名/Token）"""
        helpers = {
            "windows": "manager-core",
            "darwin": "osxkeychain",
            "linux": "store"
        }
        helper = helpers.get(OS_TYPE, "store")
        
        try:
            subprocess.run(
                ["git", "config", "--global", "credential.helper", helper],
                check=True, capture_output=True
            )
            print(f"[√] Git凭证助手已配置: {helper}")
            return True
        except Exception as e:
            print(f"[警告] 凭证助手配置失败: {e}")
            return False

    def set_accelerate(self):
        """配置Cloudflare加速规则"""
        self._check_git()
        # 暂停状态栏刷新，避免操作时界面乱跳
        self._stop_speed_monitor()
        
        # 首次运行或重置后，让用户输入域名
        if not self.worker_domain:
            self.worker_domain = input("请输入你的Cloudflare Worker自定义域（如 https://github-proxy.example.com）: ").strip()
            if not self.worker_domain.startswith("http"):
                self.worker_domain = "https://" + self.worker_domain
            self.worker_domain = self.worker_domain.rstrip("/")
            self._save_config()

        # 定义加速规则
        rules = [
            ("https://github.com/", f"{self.worker_domain}/"),
            ("https://raw.githubusercontent.com/", f"{self.worker_domain}/raw/"),
            ("https://gist.githubusercontent.com/", f"{self.worker_domain}/gist/"),
            ("https://gist.github.com/", f"{self.worker_domain}/gist-web/")
        ]

        print(f"\n[信息] 开始配置加速（代理域: {self.worker_domain}）")
        for original, proxy in rules:
            # 先清除旧规则避免重复
            subprocess.run(
                ["git", "config", "--global", "--unset-all", f"url.{proxy}.insteadOf"],
                capture_output=True
            )
            # 添加新规则
            try:
                subprocess.run(
                    ["git", "config", "--global", f"url.{proxy}.insteadOf", original],
                    check=True, capture_output=True
                )
                print(f"  [√] {original} → {proxy}")
            except Exception as e:
                print(f"  [×] 配置失败: {original} - {e}")
                return False

        # 配置凭证助手
        self._set_git_credential_helper()
        print("\n[√] 加速配置完成！")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()
        return True

    def test_accelerate(self):
        """测试加速效果"""
        if not self.worker_domain:
            print("[错误] 请先配置加速规则！")
            return
        # 暂停状态栏刷新
        self._stop_speed_monitor()

        print("\n[信息] 测试加速连接（无需克隆完整仓库）...")
        try:
            result = subprocess.run(
                ["git", "ls-remote", "https://github.com/octocat/Hello-World.git"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and "refs/heads" in result.stdout:
                print("[√] 加速成功！GitHub连接正常")
            else:
                print(f"[×] 加速失败: {result.stderr or '无有效返回'}")
        except subprocess.TimeoutExpired:
            print("[×] 测试超时！请检查Cloudflare Worker是否正常")
        except Exception as e:
            print(f"[×] 测试异常: {e}")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def _get_auto_start_path(self):
        """获取不同系统的自启路径"""
        if OS_TYPE == "windows":
            return Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup" / "GitHub_CF_Proxy.bat"
        elif OS_TYPE == "darwin":
            return Path.home() / "Library/LaunchAgents" / "com.github.cfproxy.plist"
        elif OS_TYPE == "linux":
            return Path.home() / ".config/systemd/user" / "github-cf-proxy.service"
        return None

    def _create_auto_start_file(self):
        """创建自启文件"""
        auto_path = self._get_auto_start_path()
        if not auto_path:
            print("[错误] 不支持的系统类型")
            return False

        auto_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if OS_TYPE == "windows":
                # Windows: 创建BAT启动脚本
                with open(auto_path, "w", encoding="gbk") as f:
                    f.write(f'@echo off\npython "{SCRIPT_PATH}" --silent\n')
            elif OS_TYPE == "darwin":
                # macOS: 创建LaunchAgents plist
                plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.github.cfproxy</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{SCRIPT_PATH}</string>
        <string>--silent</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>'''
                with open(auto_path, "w", encoding="utf-8") as f:
                    f.write(plist_content)
                # 加载服务
                subprocess.run(["launchctl", "load", "-w", str(auto_path)], capture_output=True)
            elif OS_TYPE == "linux":
                # Linux: 创建Systemd用户服务
                service_content = f'''[Unit]
Description=GitHub Cloudflare Proxy Auto Config
After=network.target

[Service]
Type=oneshot
ExecStart={sys.executable} {SCRIPT_PATH} --silent

[Install]
WantedBy=default.target'''
                with open(auto_path, "w", encoding="utf-8") as f:
                    f.write(service_content)
                # 启用服务
                subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
                subprocess.run(["systemctl", "--user", "enable", "github-cf-proxy.service"], capture_output=True)
            return True
        except Exception as e:
            print(f"[错误] 创建自启文件失败: {e}")
            return False

    def _remove_auto_start_file(self):
        """移除自启文件"""
        auto_path = self._get_auto_start_path()
        if not auto_path:
            return False

        try:
            if OS_TYPE == "darwin" and auto_path.exists():
                subprocess.run(["launchctl", "unload", "-w", str(auto_path)], capture_output=True)
            elif OS_TYPE == "linux" and auto_path.exists():
                subprocess.run(["systemctl", "--user", "disable", "github-cf-proxy.service"], capture_output=True)
            
            if auto_path.exists():
                auto_path.unlink()
            return True
        except Exception as e:
            print(f"[错误] 移除自启文件失败: {e}")
            return False

    def manage_auto_start(self):
        """管理开机自启"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        print(f"\n[信息] 当前自启状态: {'已启用' if self.auto_start_enabled else '已禁用'}")
        choice = input("请选择操作 (1: 启用自启  2: 禁用自启  3: 返回): ").strip()

        if choice == "1":
            if self._create_auto_start_file():
                self.auto_start_enabled = True
                self._save_config()
                print("[√] 开机自启已启用")
        elif choice == "2":
            if self._remove_auto_start_file():
                self.auto_start_enabled = False
                self._save_config()
                print("[√] 开机自启已禁用")
        elif choice == "3":
            pass
        else:
            print("[错误] 无效选项")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def clean_rules(self):
        """仅清理加速规则"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        print("\n[信息] 正在清理加速规则...")
        try:
            result = subprocess.run(
                ["git", "config", "--global", "--get-regexp", "url\\..*\\.insteadOf"],
                capture_output=True, text=True
            )
            if result.stdout:
                for line in result.stdout.splitlines():
                    key = line.split()[0]
                    subprocess.run(["git", "config", "--global", "--unset", key], check=True)
                    print(f"  [√] 已清除: {key}")
            else:
                print("  [信息] 未找到加速规则")
        except Exception as e:
            print(f"[错误] 清理失败: {e}")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def clean_credentials(self):
        """仅清理Git凭证"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        print("\n[警告] 此操作将清除Git保存的GitHub用户名/Token！")
        confirm = input("确认继续? (y/n): ").strip().lower()
        if confirm != "y":
            # 恢复状态栏刷新
            if self.status_bar_enabled:
                self._start_speed_monitor()
            return

        try:
            # 清除凭证助手配置
            subprocess.run(["git", "config", "--global", "--unset", "credential.helper"], capture_output=True)
            # 不同系统的额外清理
            if OS_TYPE == "windows":
                print("[信息] Windows请手动打开「凭据管理器」→「Windows凭据」删除GitHub相关条目")
            elif OS_TYPE == "darwin":
                subprocess.run(["security", "delete-internet-password", "-s", "github.com"], capture_output=True)
            elif OS_TYPE == "linux":
                cred_file = Path.home() / ".git-credentials"
                if cred_file.exists():
                    cred_file.unlink()
            print("[√] Git凭证已清理")
        except Exception as e:
            print(f"[错误] 清理凭证失败: {e}")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def clean_config(self):
        """仅清理脚本配置文件"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        print("\n[警告] 此操作将清除脚本保存的域名、自启状态、状态栏设置等配置！")
        confirm = input("确认继续? (y/n): ").strip().lower()
        if confirm != "y":
            # 恢复状态栏刷新
            if self.status_bar_enabled:
                self._start_speed_monitor()
            return

        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            self.worker_domain = ""
            self.auto_start_enabled = False
            self.status_bar_enabled = False
            print("[√] 脚本配置已清理")
        else:
            print("[信息] 未找到配置文件")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def reset_all(self):
        """一键重置所有"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        print("\n[警告] 此操作将重置所有配置（加速规则、Git凭证、脚本配置、自启、状态栏）！")
        confirm = input("确认继续? (y/n): ").strip().lower()
        if confirm != "y":
            # 恢复状态栏刷新
            if self.status_bar_enabled:
                self._start_speed_monitor()
            return

        print("\n[信息] 开始重置...")
        self.clean_rules()
        self._remove_auto_start_file()
        self.clean_credentials()
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        # 重置所有状态
        self.worker_domain = ""
        self.auto_start_enabled = False
        self.status_bar_enabled = False
        # 重置终端
        self._reset_terminal()
        print("\n[√] 所有配置已重置，恢复初始状态")

    def show_menu(self):
        """显示主菜单"""
        # 先渲染状态栏（开启状态下）
        self._render_status_bar()
        print("\n" + "="*60)
        print("  GitHub Cloudflare 全自动加速工具 (开源版)")
        print(f"  当前代理域: {self.worker_domain or '未配置'}")
        print(f"  自启状态: {'已启用' if self.auto_start_enabled else '已禁用'} | 状态栏: {'已开启' if self.status_bar_enabled else '已隐藏'}")
        print("="*60)
        print("  1. 配置/更新加速规则")
        print("  2. 测试加速效果")
        print("  3. 管理开机自启")
        print("  4. 清理选项")
        print("  5. 一键重置所有")
        print("  6. 显示/隐藏实时网速状态栏")
        print("  7. 退出")
        print("="*60)

    def clean_menu(self):
        """清理子菜单"""
        # 暂停状态栏刷新
        self._stop_speed_monitor()
        while True:
            print("\n--- 清理选项 ---")
            print("1. 仅清理加速规则")
            print("2. 仅清理Git凭证")
            print("3. 仅清理脚本配置")
            print("4. 返回主菜单")
            choice = input("请选择: ").strip()

            if choice == "1":
                self.clean_rules()
            elif choice == "2":
                self.clean_credentials()
            elif choice == "3":
                self.clean_config()
            elif choice == "4":
                break
            else:
                print("[错误] 无效选项")

        # 恢复状态栏刷新
        if self.status_bar_enabled:
            self._start_speed_monitor()

    def run(self):
        """主运行逻辑"""
        # 静默模式（用于开机自启，不启动状态栏和交互）
        if "--silent" in sys.argv:
            if self.worker_domain:
                self.set_accelerate()
            sys.exit(0)

        # 初始化环境
        self._check_git()
        self._init_terminal()
        # 开启状态栏的情况下，启动后台监控
        if self.status_bar_enabled:
            self._start_speed_monitor()

        # 注册退出钩子，重置终端状态
        import atexit
        atexit.register(self._reset_terminal)
        atexit.register(self._stop_speed_monitor)

        # 主交互循环
        while True:
            self.show_menu()
            choice = input("请选择操作 (1-7): ").strip()

            if choice == "1":
                self.set_accelerate()
            elif choice == "2":
                self.test_accelerate()
            elif choice == "3":
                self.manage_auto_start()
            elif choice == "4":
                self.clean_menu()
            elif choice == "5":
                self.reset_all()
            elif choice == "6":
                self.toggle_status_bar()
            elif choice == "7":
                print("\n[信息] 退出工具，再见！")
                sys.exit(0)
            else:
                print("[错误] 无效选项，请重新输入")


if __name__ == "__main__":
    proxy = GitHubCFProxy()
    proxy.run()