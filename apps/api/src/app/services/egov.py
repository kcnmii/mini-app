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

def _detect_entity_type(number: str, name: str = "") -> str:
    """
    Determine if a 12-digit number is IIN (individual/ИП) or BIN (business/ТОО).
    Uses a hybrid approach: checks strong name signals first, then analyzes
    Kazakhstan's IIN/BIN structure.
    """
    upper_name = name.upper().strip()
    
    # Step 1: Very strong name signals
    if upper_name.startswith("ИП ") or "ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ" in upper_name:
        return "IP"
        
    org_prefixes = [
        "ТОО", "АО ", "АО\"", "ОАО", "ЗАО", "НАО", "КТ ", "ПТ ", "ГКП", "РГП",
        "ТОВАРИЩЕСТВО", "АКЦИОНЕРНОЕ", "ГОСУДАРСТВЕННОЕ", "ОБЩЕСТВО"
    ]
    if any(upper_name.startswith(p) for p in org_prefixes):
        return "UL"

    # Step 2: Structural detection
    if len(number) == 12 and number.isdigit():
        mm = int(number[2:4])   # month (positions 3-4)
        dd = int(number[4:6])   # day (pos 5-6) for IIN, or entity type for BIN
        d7 = int(number[6])     # gender/century for IIN (1-6)
        
        # If dd > 31 or dd == 0, it can't be a birth day → it's a BIN
        # If mm > 12 or mm == 0, it can't be a birth month → it's a BIN
        if dd > 31 or dd == 0 or mm > 12 or mm == 0:
            # It's a BIN. Check 5th digit: 6 = ИП registered as business
            d5 = int(number[4])
            return "IP" if d5 == 6 else "UL"
        
        # Valid date range + gender code 1-6 → mostly IIN (individual = ИП)
        if 1 <= d7 <= 6:
            return "IP"
            
        # Fallback for BINs with type < 4 and 7th digit > 6
        return "UL"
    
    # Default to UL if can't determine
    return "UL"


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
                            
                        # Try title first (new kyc.kz), then name_ru (old)
                        name_match = re.search(r'(?:title|name_ru):\s*(["\'].*?(?<!\\)["\'])', content)
                        if name_match:
                            try:
                                name_val = name_match.group(1).replace("\\'", "'")
                                name = json.loads(name_val) if name_val.startswith('"') else name_val.strip("'")
                            except:
                                name = name_match.group(1).strip('"\'')
                                
                        addr_match = re.search(r'official_address:\s*(["\'].*?(?<!\\)["\'])', content)
                        if addr_match:
                            try:
                                addr_val = addr_match.group(1).replace("\\'", "'")
                                address = json.loads(addr_val) if addr_val.startswith('"') else addr_val.strip("'")
                            except:
                                address = addr_match.group(1).strip('"\'')
                        break
                        
                # Fallback to parsing meta description if JSON failed
                if not name or name.lower() == "undefined":
                    # Try to extract from "Проверить ... на благонадёжность" or "Проверить ..., БИН ..."
                    name_match = re.search(r'Проверить\s+(.*?)\s+(?:на благонадёжность|, БИН|, ИИН)', desc)
                    if name_match:
                        name = name_match.group(1).strip().strip('"').strip("'")
                
                if not director or director.lower() == "undefined":
                    director_match = re.search(r'Руководитель\s+(.*?)(?:,|\s+\|)', desc)
                    if director_match:
                        director = director_match.group(1).strip()
                
                if not address or address.lower() == "undefined":
                    # Address is often after BIN/IIN and before OKED or |
                    addr_match = re.search(r'(?:БИН|ИИН)\s+\d{12},\s+(.*?)(?:,\s+ОКЭД|\s+\|)', desc)
                    if addr_match:
                        address = addr_match.group(1).strip()
                    else:
                        # desperate fallback - splitting
                        if director:
                            parts = desc.split(f"Руководитель {director},")
                        else:
                            parts = desc.split(f"БИН {clean_bin},") if f"БИН {clean_bin}" in desc else desc.split(f"ИИН {clean_bin},")
                            
                        if len(parts) > 1:
                            rest = parts[1]
                            addr_end = rest.find(", ОКЭД")
                            if addr_end == -1: addr_end = rest.find(" |")
                            address = rest[:addr_end].strip() if addr_end != -1 else rest.strip()
                            
                    address = (address or "").strip(',')
                
                name = normalize_org_name(name)
                if name.lower() == "undefined" or not name:
                    return None
                
                # Determine type using the BIN/IIN number structure
                org_type = _detect_entity_type(clean_bin, name)
                
                # Automatically add "ИП" prefix if missing for individual entrepreneurs
                if org_type == "IP" and not name.upper().startswith("ИП "):
                    name = f"ИП {name}"
                
                return {
                    "name": name,
                    "bin": clean_bin,
                    "address": address if address.lower() != "undefined" else "",
                    "director": director if director.lower() != "undefined" else "",
                    "type": org_type,
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
