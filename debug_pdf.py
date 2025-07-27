#!/usr/bin/env python3
"""
Debug script to examine PDF content and understand why parsing is failing
"""

import pdfplumber
from pathlib import Path

def debug_pdf_content():
    pdf_path = "/app/GST104.pdf"
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Check first few pages
        for i, page in enumerate(pdf.pages[:3]):
            print(f"\n=== PAGE {i+1} ===")
            text = page.extract_text()
            if text:
                print(f"Text length: {len(text)}")
                print("First 500 characters:")
                print(text[:500])
                print("\n" + "="*50)
            else:
                print("No text extracted from this page")

if __name__ == "__main__":
    debug_pdf_content()