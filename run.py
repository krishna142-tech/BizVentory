from app import app
import socket
import netifaces

def get_all_ips():
    ips = []
    try:
        # Get hostname first
        hostname = socket.gethostname()
        ips.append(socket.gethostbyname(hostname))
        
        # Try getting other network interfaces
        interfaces = netifaces.interfaces()
        for interface in interfaces:
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if not ip.startswith('127.'):
                        ips.append(ip)
    except Exception as e:
        print(f"Error getting IPs: {e}")
    return list(set(ips))  # Remove duplicates

if __name__ == '__main__':
    port = 3000
    
    print("\nBizVentory Server Starting...")
    print("============================")
    print(f"Local access:     http://localhost:{port}")
    print("\nTry these URLs on other devices:")
    
    # Get and display all possible IPs
    ips = get_all_ips()
    for ip in ips:
        print(f"                http://{ip}:{port}")
    
    print(f"\nAlso try using computer name:")
    print(f"                http://{socket.gethostname()}:{port}")
    
    print("\nMake sure:")
    print("1. Other devices are on the same WiFi network")
    print("2. Windows Defender Firewall is disabled")
    print("3. Network is set to 'Private' in Windows settings")
    print("4. Mobile data is turned off on phones")
    print("\nPress Ctrl+C to stop the server")
    print("============================\n")
    
    # Run the app with explicit host and port
    app.run(
        host='0.0.0.0',  # Makes the server externally visible
        port=port,
        debug=True
    ) 