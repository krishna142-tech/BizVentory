import os
import subprocess
import sys
import socket

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def setup_firewall():
    if not is_admin():
        print("This script needs to be run as administrator!")
        print("Please run PowerShell or Command Prompt as administrator and try again.")
        return False

    commands = [
        'netsh advfirewall firewall delete rule name="Flask Web App"',  # Delete if exists
        'netsh advfirewall firewall add rule name="Flask Web App" dir=in action=allow protocol=TCP localport=5000',
        'netsh advfirewall firewall add rule name="Flask Web App" dir=out action=allow protocol=TCP localport=5000'
    ]

    for cmd in commands:
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError:
            print(f"Error executing command: {cmd}")
            return False

    return True

def get_ip_addresses():
    try:
        # Get hostname and all associated IP addresses
        hostname = socket.gethostname()
        ip_list = socket.gethostbyname_ex(hostname)[2]
        
        # Filter and categorize IPs
        local_ips = []
        network_ips = []
        
        for ip in ip_list:
            if ip.startswith('127.'):
                local_ips.append(ip)
            else:
                network_ips.append(ip)
        
        return {
            'hostname': hostname,
            'local_ips': local_ips,
            'network_ips': network_ips
        }
    except Exception as e:
        print(f"Error getting IP addresses: {str(e)}")
        return {
            'hostname': 'unknown',
            'local_ips': ['127.0.0.1'],
            'network_ips': []
        }

def main():
    print("\nBizVentory Network Setup")
    print("=======================")
    
    if not is_admin():
        print("\n⚠️ ERROR: This script must be run as administrator!")
        print("Please:")
        print("1. Close this window")
        print("2. Right-click on PowerShell or Command Prompt")
        print("3. Select 'Run as administrator'")
        print("4. Navigate to the project directory")
        print("5. Run this script again")
        return

    print("\nSetting up firewall rules...")
    if setup_firewall():
        print("✅ Firewall rules successfully configured")
    else:
        print("❌ Failed to configure firewall rules")
        return

    ip_info = get_ip_addresses()
    port = 5000

    print(f"\nSystem Information:")
    print(f"Hostname: {ip_info['hostname']}")
    
    print("\nNetwork Access URLs:")
    print("-------------------")
    print(f"Local access:     http://localhost:{port}")
    
    if ip_info['network_ips']:
        print("\nExternal access (use these URLs from other devices):")
        for ip in ip_info['network_ips']:
            print(f"                 http://{ip}:{port}")
    else:
        print("\n⚠️ No network IP addresses found!")
        print("The server might only be accessible locally.")
    
    print("\nTroubleshooting:")
    print("--------------")
    print("1. Make sure all devices are on the same network")
    print("2. Check Windows Defender or antivirus is not blocking Python")
    print("3. Verify the Flask application (app.py) is running")
    print("4. Try accessing using different URLs if one doesn't work")
    print("5. If using a VPN, try disconnecting from it")
    
    print("\nNext Steps:")
    print("-----------")
    print("1. Start the Flask application: python app.py")
    print("2. Access the application using one of the URLs above")
    print("3. If you can't connect, try disabling the firewall temporarily")
    print("   to check if it's causing the issue")

if __name__ == "__main__":
    main() 