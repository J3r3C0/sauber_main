import socket
import time

ports = [3000, 3001, 8001, 9000, 8081]
for port in ports:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            res = sock.connect_ex(('127.0.0.1', port))
            print(f"Port {port} (127.0.0.1): {'OK' if res == 0 else f'FAIL ({res})'}")
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock2:
                sock2.settimeout(1.0)
                res2 = sock2.connect_ex(('localhost', port))
                print(f"Port {port} (localhost): {'OK' if res2 == 0 else f'FAIL ({res2})'}")
    except Exception as e:
        print(f"Port {port} Error: {e}")
