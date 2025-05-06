import requests
import random

def get_active_proxies():
    url = "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=transparent&protocols=http%2Chttps&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if "data" not in data:
            raise ValueError("Unexpected response format.")
        
        active_proxies = []
        
        for proxy in data["data"]:
            for proto in proxy["protocols"]:
                if proto in ["http", "https"]:
                    active_proxies.append({proto: f"{proxy['ip']}:{proxy['port']}"})
        
        if not active_proxies:
            raise ValueError("No active HTTP/HTTPS proxies found.")
        
        return active_proxies
    
    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching proxy list: {e}")
        return None

ACTIVE_PROXIES : dict = get_active_proxies()

def get_random_proxy():
    return random.choice(ACTIVE_PROXIES)