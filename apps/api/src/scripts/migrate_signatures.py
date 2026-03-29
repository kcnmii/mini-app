"""
Migration script: Extract certificate metadata from existing CMS signatures.
Run this script to retroactively populate missing certificate data
(serial number, validity period, org info) for older signatures in the DB.

Usage:
    cd /home/observer/Projects/new/doc-mini-app/apps/api
    uv run python -m src.scripts.migrate_signatures
"""

import sys
import os

# Add src to Python path so we can import internal modules directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.db import SessionLocal, Signature
from app.services.cms_parser import parse_cms_signature

def main():
    db = SessionLocal()
    
    # Only fetch CMS signatures that are missing the certificate serial
    signatures = db.query(Signature).filter(
        Signature.signature_type == "cms"
    ).all()
    
    updated_count = 0
    error_count = 0
    
    print(f"Found {len(signatures)} total CMS signatures in Database.")
    
    for sig in signatures:
        if sig.certificate_serial:
            continue  # already parsed
            
        print(f"Parsing signature ID: {sig.id}")
        
        try:
            cert_info = parse_cms_signature(sig.signature_data)
            
            if cert_info:
                # Update but don't overwrite if we already had a proper value and cert value is empty
                if cert_info.subject_iin:
                    sig.signer_iin = cert_info.subject_iin
                
                if cert_info.subject_cn:
                    sig.signer_name = cert_info.subject_cn
                    
                if cert_info.subject_org:
                    sig.signer_org_name = cert_info.subject_org
                    
                sig.certificate_serial = cert_info.serial_hex
                
                if cert_info.valid_from:
                    sig.certificate_valid_from = cert_info.valid_from.replace(tzinfo=None)
                    
                if cert_info.valid_to:
                    sig.certificate_valid_to = cert_info.valid_to.replace(tzinfo=None)
                    
                updated_count += 1
                print(f"  [OK] Extracted: SN={cert_info.serial_hex}, IIN={cert_info.subject_iin}")
            else:
                print(f"  [ERROR] Failed to parse CMS for signature ID {sig.id}")
                error_count += 1
                
        except Exception as e:
            print(f"  [ERROR] Exception parsing signature ID {sig.id}: {e}")
            error_count += 1
            
    if updated_count > 0:
        db.commit()
        print(f"\\nSuccessfully updated and committed {updated_count} signatures.")
    else:
        print("\\nNo signatures needed updating.")
        
    db.close()

if __name__ == "__main__":
    main()
