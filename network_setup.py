import os
import socket
import subprocess
import sys
import netifaces

def is_admin():
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def get_all_ip_addresses():
    ip_addresses = []
    interfaces = netifaces.interfaces()
    
    for interface in interfaces:
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                if not ip.startswith('127.'):
                    ip_addresses.append(ip)
    return ip_addresses

def setup_firewall():
    if not is_admin():
        print("⚠️ This script must be run as administrator!")
        print("Please:")
        print("1. Close this window")
        print("2. Right-click on PowerShell or Command Prompt")
        print("3. Select 'Run as administrator'")
        print("4. Navigate to your project directory")
        print("5. Run this script again")
        return False

    try:
        # Remove existing rules if they exist
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=Flask Web App'], 
                      capture_output=True)
        
        # Add new inbound rule
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                       'name=Flask Web App',
                       'dir=in',
                       'action=allow',
                       'protocol=TCP',
                       'localport=3000'], 
                      check=True)
        
        # Add new outbound rule
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                       'name=Flask Web App',
                       'dir=out',
                       'action=allow',
                       'protocol=TCP',
                       'localport=3000'], 
                      check=True)
        
        print("✅ Firewall rules configured successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error configuring firewall: {e}")
        return False

def check_port_availability(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    except:
        return False

def main():
    print("\nBizVentory Network Setup")
    print("=======================")
    
    # Check if port 3000 is available
    if not check_port_availability(3000):
        print("❌ Error: Port 3000 is already in use!")
        print("Please either:")
        print("1. Close the application using port 3000")
        print("2. Or modify the port number in app.py")
        return
    
    # Setup firewall rules
    if not setup_firewall():
        return
    
    # Get all IP addresses
    ip_addresses = get_all_ip_addresses()
    
    print("\n✨ Network Configuration Complete!")
    print("================================")
    print(f"Local URL:      http://localhost:3000")
    print("\nPossible Network URLs (try these in order):")
    for ip in ip_addresses:
        print(f"                http://{ip}:3000")
    
    print("\n📱 To access from other devices:")
    print("1. Make sure all devices are on the same WiFi network")
    print("2. Try each Network URL listed above until one works")
    print("3. If none work, try these steps:")
    print("   a. Temporarily disable Windows Defender Firewall")
    print("   b. Ensure your antivirus is not blocking the connection")
    print("   c. Turn off mobile data on phones (use only WiFi)")
    print("   d. Disconnect from any VPN services")
    print("\n🔍 Network Diagnostics:")
    print("1. Your computer's hostname:", socket.gethostname())
    print("2. Available network interfaces:", ", ".join(netifaces.interfaces()))
    print("\n🚀 Ready to start the application!")
    print("Run 'python app.py' to start the server")

if __name__ == "__main__":
    main() 