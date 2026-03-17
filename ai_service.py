import os
import base64
import json
import re
import requests
import google.generativeai as genai
import anthropic
from pathlib import Path

# ─────────────────────────────────────────────
# AI EXTRACTION PROMPT
# ─────────────────────────────────────────────

# Shared prompt for both providers
EXTRACTION_PROMPT = """
ACT AS A PHOTOCOPIER. Extract every text row from the Grafana dashboard legend.

1. Find every panel. Each panel has a TITLE at the top (e.g., FINGRID SERVERS CPU ABOVE 90).
2. Identify the panel type: CPU, MEM, or DISK.

For EACH panel, output:
---PANEL: [FULL TITLE]---
[Literal Row 1 from Legend]
[Literal Row 2 from Legend]
...

STRICT RULES:
- Copy characters EXACTLY. Do not fix what you think are mistakes.
- IMPORTANT: In DISK panels, labels like ( \\C: ) must keep the backslash. Use ( \\C: ) NOT ( IC: ).
- Do not compress IP addresses (e.g., if you see "10.1.1", do not write "10.11").
- Output every single row you see in the legend.
- If a row is unreadable, write [UNREADABLE].
"""

# ─────────────────────────────────────────────
# PROVIDER: GOOGLE GEMINI
# ─────────────────────────────────────────────
def _call_google_gemini_batch(image_bytes_list, config):
    """Calls Google Gemini API using dynamic configuration."""
    import time
    
    api_key = config.get("api_key")
    model_id = config.get("model_id")
    
    if not api_key:
        raise Exception("Google API Key is missing in the selected configuration.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    
    prompt_parts = [EXTRACTION_PROMPT]
    for img_bytes in image_bytes_list:
        prompt_parts.append({"mime_type": "image/png", "data": img_bytes})
    
    for attempt in range(3):
        try:
            print(f"[AI Service] Sending batch to Gemini ({model_id})...")
            response = model.generate_content(
                prompt_parts,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=8192
                )
            )
            
            if response and response.text:
                return response.text
            return ""
            
        except Exception as e:
            if "429" in str(e):
                wait = 60
                print(f"[AI Service] Rate limited. Retrying {attempt+1}/3...")
                time.sleep(wait)
                continue
            raise e
    
    raise Exception("Gemini API rate limit exceeded.")

# ─────────────────────────────────────────────
# PROVIDER: ANTHROPIC CLAUDE
# ─────────────────────────────────────────────
def _call_anthropic_batch(image_bytes_list, config):
    """Calls Anthropic Claude API using dynamic configuration."""
    api_key = config.get("api_key")
    model_id = config.get("model_id")

    if not api_key:
        raise Exception("Anthropic API Key is missing in the selected configuration.")

    client = anthropic.Anthropic(api_key=api_key)
    
    content_parts = [{"type": "text", "text": EXTRACTION_PROMPT}]
    for img_bytes in image_bytes_list:
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        content_parts.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": b64_img
            }
        })
    
    print(f"[AI Service] Sending batch to Claude ({model_id})...")
    
    response = client.messages.create(
        model=model_id,
        max_tokens=8192,
        messages=[{"role": "user", "content": content_parts}]
    )
    
    if response and response.content:
        return response.content[0].text
    return ""

def _call_openai_compatible(image_bytes_list, config):
    """Calls OpenAI-compatible APIs (DeepSeek, LM Studio, etc.)."""
    from openai import OpenAI
    
    api_key = config.get("api_key")
    model_id = config.get("model_id")
    provider = config.get("provider", "openai").lower()
    
    # Determine base URL
    if provider == "deepseek":
        base_url = "https://api.deepseek.com"
    elif provider == "openai":
        base_url = "https://api.openai.com/v1"
    else:
        base_url = os.getenv("AI_URL", "http://host.docker.internal:1234/v1")
    
    client = OpenAI(base_url=base_url, api_key=api_key if api_key else "not-needed", timeout=600.0)
    
    accumulated_text = ""
    for i, img_bytes in enumerate(image_bytes_list):
        print(f"[AI Service] Sending image {i+1} to {provider} ({model_id})...")
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            }],
            temperature=0.0,
            max_tokens=4096
        )
        accumulated_text += response.choices[0].message.content + "\n"
        
    return accumulated_text

# ─────────────────────────────────────────────
# MAIN EXTRACTION FUNCTION
# ─────────────────────────────────────────────
def extract_data_from_images(image_bytes_list, config):
    """
    Pass 1: Send images to the AI provider defined in config.
    Pass 2: Python parses blocks, repairs IPs, and formats JSON.
    """
    raw_accumulated_text = ""
    provider = config.get("provider", "google").lower()
    
    print(f"[AI Service] Using dynamic provider: {provider}")
    
    if not image_bytes_list:
        return {"one_day": [], "under_utilized": []}

    try:
        if provider == "google":
            raw_accumulated_text = _call_google_gemini_batch(image_bytes_list, config)
        elif provider == "claude" or provider == "anthropic":
            raw_accumulated_text = _call_anthropic_batch(image_bytes_list, config)
        elif provider == "deepseek" or provider == "openai" or provider == "lmstudio":
            raw_accumulated_text = _call_openai_compatible(image_bytes_list, config)
        else:
            raise Exception(f"Unsupported AI provider: {provider}")
            
    except Exception as e:
        print(f"[AI Service] Error during extraction: {e}")
        raise e

    return _parse_raw_text_to_json(raw_accumulated_text)

# ─────────────────────────────────────────────
# IP REPAIR
# ─────────────────────────────────────────────
def _repair_ip(ip_str):
    """Fixes common OCR/AI compression mistakes in IP addresses.
    An IP must have exactly 3 dots. If it has fewer, we try to split segments."""
    if not ip_str: return ip_str
    
    # Clean artifacts first
    ip_str = ip_str.replace("\\.", ".").replace(" .", ".").replace(". ", ".")
    
    dots = ip_str.count(".")
    
    # Already looks correct (3 dots = 4 octets)
    if dots == 3:
        return ip_str
    
    # 2 dots = 3 segments, one segment needs splitting
    if dots == 2:
        parts = ip_str.split(".")
        # For 10.x.x.x: split middle segment (10.11.13 -> 10.1.1.13)
        if parts[0] == "10" and len(parts[1]) == 2:
            return f"{parts[0]}.{parts[1][0]}.{parts[1][1]}.{parts[2]}"
        # For 172.x.x: split second segment (172.116.5 -> 172.1.16.5)
        if parts[0] == "172" and len(parts[1]) == 3:
            return f"{parts[0]}.{parts[1][0]}.{parts[1][1:]}.{parts[2]}"
        # For 172.x.x: split second segment (172.14.12 -> 172.1.4.12)
        if parts[0] == "172" and len(parts[1]) == 2:
            return f"{parts[0]}.{parts[1][0]}.{parts[1][1]}.{parts[2]}"
    
    return ip_str

# ─────────────────────────────────────────────
# POST-PROCESSING
# ─────────────────────────────────────────────
def _flatten_single_disks(entries, category):
    """Convert single-drive disks entries to disk_avg/disk format.
    If disks has only 1 key, convert to disk_avg (FINGRID) or disk (HOLDCO)."""
    for entry in entries:
        if "disks" in entry and len(entry["disks"]) == 1:
            val = list(entry["disks"].values())[0]
            del entry["disks"]
            key = "disk" if category == "HOLDCO" else "disk_avg"
            entry[key] = val
    return entries

# ─────────────────────────────────────────────
# PASS 2: STATE-MACHINE PARSER
# ─────────────────────────────────────────────
def _parse_raw_text_to_json(text):
    """
    Parses raw AI text output into Claude-style JSON.
    - Creates SEPARATE entries for each metric (CPU, MEM, DISK).
    - Groups multiple drives for the same server into one disk entry.
    - Repairs IP addresses.
    - Detects panel headers with or without ---PANEL:--- markers.
    """
    one_day_list = []
    under_list = []
    
    one_day_disk_cache = {}
    under_disk_cache = {}
    
    current_category = "FINGRID"
    current_metric = "CPU"
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or "[UNREADABLE]" in line: continue
        
        # Panel Detection - flexible: matches both "---PANEL: title---" AND raw titles
        upper_line = line.upper()
        if "PANEL:" in upper_line or ("ABOVE" in upper_line and ("CPU" in upper_line or "MEM" in upper_line or "DISK" in upper_line)):
            current_category = "HOLDCO" if "HOLDCO" in upper_line else "FINGRID"
            if "CPU" in upper_line: current_metric = "CPU"
            elif "MEM" in upper_line: current_metric = "MEM"
            elif "DISK" in upper_line: current_metric = "DISK"
            continue

        # Row Detection: ServerName : IP [Drive] Mean: Value
        row_match = re.search(r"(.*?)\s*:\s*([\d\.]+(?:\s*\(.*?\))?)\s*.*?(?:Mean|:)\s*([\d\.]+)", line, re.IGNORECASE)
        if not row_match: continue
        
        name_part, ip_drive_part, val_str = row_match.groups()
        
        # Extract drive letter from IP/Name part
        drive_match = re.search(r"\((.*?)\)", ip_drive_part)
        drive_label = ""
        ip_part = ip_drive_part
        
        if drive_match:
            drive_label = drive_match.group(1).replace("\\", "").strip()
            # Clean common OCR mistakes (e.g., "IC" instead of "C")
            if len(drive_label) == 2 and drive_label.startswith("I"):
                drive_label = drive_label[1:]
            ip_part = ip_drive_part.replace(drive_match.group(0), "").strip()
            
        # Fallback: check name part for drive
        name_drive_match = re.search(r"\((.*?)\)", name_part)
        if name_drive_match and not drive_label:
            drive_label = name_drive_match.group(1).replace("\\", "").strip()
            name_part = name_part.replace(name_drive_match.group(0), "").strip()

        # Repair IP
        ip_part = _repair_ip(ip_part.strip())
        name_part = name_part.strip()
        server_id = f"{name_part} : {ip_part}"
        
        try:
            val = round(float(val_str))
        except:
            continue

        target_list = under_list if current_category == "HOLDCO" else one_day_list
        disk_cache = under_disk_cache if current_category == "HOLDCO" else one_day_disk_cache

        # CPU and MEM: always create a NEW separate entry
        if current_metric == "CPU":
            key = "cpu_min" if current_category == "HOLDCO" else "cpu_avg"
            target_list.append({"name": server_id, key: val})
        elif current_metric == "MEM":
            key = "memory" if current_category == "HOLDCO" else "mem_avg"
            target_list.append({"name": server_id, key: val})
        elif current_metric == "DISK":
            if drive_label:
                if server_id not in disk_cache:
                    entry = {"name": server_id, "disks": {}}
                    disk_cache[server_id] = entry
                    target_list.append(entry)
                disk_cache[server_id]["disks"][drive_label] = val
            else:
                key = "disk" if current_category == "HOLDCO" else "disk_avg"
                target_list.append({"name": server_id, key: val})

    # Post-process: Convert single-drive disks to disk_avg/disk
    _flatten_single_disks(one_day_list, "FINGRID")
    _flatten_single_disks(under_list, "HOLDCO")

    return {
        "one_day": one_day_list,
        "under_utilized": under_list
    }
