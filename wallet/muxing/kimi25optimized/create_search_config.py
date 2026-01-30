#!/usr/bin/env python3
"""
Configuration Generator for Muxed Address Hunter
Run: python create_search_config.py
"""
import os
import re

def validate_g(addr):
    if not re.match(r'^G[A-Z2-7]{55}$', addr):
        raise ValueError("Must be 56 chars starting with G")
    return addr

def main():
    print("=" * 50)
    print("Create Search Configuration File")
    print("=" * 50)
    print("This will create 'search_config.py' for automatic loading.\n")
    
    # Get inputs
    while True:
        g_address = input("Enter your G-address: ").strip().upper()
        try:
            validate_g(g_address)
            break
        except Exception as e:
            print(f"❌ {e}")
    
    while True:
        suffix = input("Enter target suffix (e.g., WORD): ").strip().upper()
        if len(suffix) >= 2 and re.match(r'^[A-Z2-7]+$', suffix):
            break
        print("❌ Use A-Z, 2-7 only (min 2 chars)")
    
    resume_default = input("Default resume filename (press Enter for 'hunt_progress.txt'): ").strip()
    if not resume_default:
        resume_default = "hunt_progress.txt"
    
    # Write the config file
    filename = "search_config.py"
    content = f'''# Auto-generated search configuration
# This file is imported automatically by the hunter script.
# Delete it to return to interactive mode.

G_ADDRESS = "{g_address}"
TARGET_SUFFIX = "{suffix}"
RESUME_FILE = "{resume_default}"

# Optional: Set default resource limits (uncomment to use)
# DEFAULT_WORKERS = 4
# DEFAULT_PRIORITY = "low"  # idle, low, normal
'''
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"\n✅ Configuration saved to: {filename}")
    print(f"   Address: {g_address[:12]}...{g_address[-4:]}")
    print(f"   Suffix:  {suffix}")
    print(f"\nYou can now run: python suffix_hunter_optimized.py")
    print("(It will load these settings automatically)")

if __name__ == "__main__":
    main()
