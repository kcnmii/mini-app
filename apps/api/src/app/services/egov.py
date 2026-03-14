import json
import logging
import re
import httpx
from bs4 import BeautifulSoup
import asyncio

# Limit simultaneous requests
egov_semaphore = asyncio.Semaphore(5)

def normalize_org_name(name: str) -> str:
    """Shortens long legal forms in the name."""
    if not name:
        return ""
    # Replace long names with abbreviations (case-insensitive)
    name = re.sub(r'Товарищество с ограниченной ответственностью', 'ТОО', name, flags=re.IGNORECASE)
    name = re.sub(r'Индивидуальный предприниматель', 'ИП', name, flags=re.IGNORECASE)
    # Remove extra spaces
    return " ".join(name.split())

async def search_bin_details(bin_number: str, client: httpx.AsyncClient = None):
    """
    Service to search BIN/IIN details from kyc.kz.
    Returns cleaned dictionary or None if not found.
    """
    clean_bin = "".join(filter(str.isdigit, bin_number))
    if len(clean_bin) != 12:
        return None

    async def _search_kyc(cl: httpx.AsyncClient):
        url = f"https://kyc.kz/search/bin/{clean_bin}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = await cl.get(url, headers=headers, timeout=10.0)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                meta_desc = soup.find('meta', {'name': 'description'})
                if not meta_desc:
                    return None
                    
                desc = meta_desc.get('content', '')
                
                # Check if it was actually found
                if "на благонадёжность" not in desc:
                   return None
                   
                # Try to extract data from window.__NUXT__
                name, director, address = "", "", ""
                scripts = soup.find_all('script')
                for s in scripts:
                    if s.string and 'window.__NUXT__' in s.string:
                        content = s.string
                        
                        chief_match = re.search(r'chief_name:\s*["\']([^"\']+)["\']', content)
                        if chief_match:
                            director = chief_match.group(1)
                            
                        name_match = re.search(r'name_ru:\s*(["\'].*?(?<!\\)["\'])', content)
                        if name_match:
                            try:
                                name = json.loads(name_match.group(1).replace("\\'", "'"))
                            except:
                                name = name_match.group(1).strip('"\'')
                                
                        addr_match = re.search(r'official_address:\s*(["\'].*?(?<!\\)["\'])', content)
                        if addr_match:
                            try:
                                address = json.loads(addr_match.group(1).replace("\\'", "'"))
                            except:
                                address = addr_match.group(1).strip('"\'')
                        break
                        
                # Fallback to parsing meta description
                if not name:
                    name_match = re.search(r'Проверить\s+(.*?)\s+на благонадёжность', desc)
                    name = name_match.group(1).strip() if name_match else ""
                
                if not director:
                    director_match = re.search(r'Руководитель\s+(.*?),\s+', desc)
                    director = director_match.group(1).strip() if director_match else ""
                
                if not address:
                    if director:
                        parts = desc.split(f"Руководитель {director},")
                    else:
                        parts = desc.split(f"БИН {clean_bin},")
                        if len(parts) < 2:
                             parts = desc.split(f"ИИН {clean_bin},")
                             
                    if len(parts) > 1:
                        rest = parts[1]
                        addr_end = rest.find(", ОКЭД")
                        if addr_end == -1:
                             addr_end = rest.find(" |")
                        
                        if addr_end != -1:
                            address = rest[:addr_end].strip()
                        else:
                            address = rest.strip()
                            
                    address = address.strip(',')
                
                name = normalize_org_name(name)
                
                return {
                    "name": name,
                    "bin": clean_bin,
                    "address": address,
                    "director": director,
                    "type": "IP" if not director else "UL",
                    "found": True
                }
        except Exception as e:
            logging.error(f"Error fetching kyc.kz data: {e}")
        return None

    async with egov_semaphore:
        if client:
            return await _search_kyc(client)
        else:
            async with httpx.AsyncClient(verify=False) as new_client:
                return await _search_kyc(new_client)
