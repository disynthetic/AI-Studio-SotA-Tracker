import os
import sys
import time
import glob
import re
import numpy as np
from PIL import ImageGrab, ImageOps, Image
import cv2

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# =========================================================================
# SYSTEM & DUAL SPECIALIZATION CONFIGURATION
# =========================================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CUSTOM_LOG_DIR = r'C:\Users\hyperlight_drifter\AppData\Roaming\Catnip Games\Shroud of the Avatar\ChatLogs'

# Aeromancer Dual-Specialization Baseline (160 Combined Cap)
AIR_SPEC_CONFIG = {
    "current_level": 77,
    "xp_into_current_level": 0
}

FOCUS_SPEC_CONFIG = {
    "current_level": 66,
    "xp_into_current_level": 0
}

DUAL_SPEC_CAP = 160

# Adventurer Level 131 -> 132 & Banked Pool Baseline
ADVENTURER_CONFIG = {
    "current_level": 131,
    "xp_to_next_level": 36576254,
    "banked_xp_pool": 128277025
}

# =========================================================================
# CALIBRATED 2560x1440 HUD REGIONS
# =========================================================================
STATS_PANEL_ROI = (0, 0, 325, 920)
BUFF_BAR_ROI = (0, 915, 420, 1110)
TOTA_METER_ROI = (2140, 500, 2500, 790)

MATCH_THRESHOLD = 0.75

TARGET_BUFFS = {
    "Air's Embrace": {
        "filename": "airs_embrace.png",
        "advice": "Re-cast Air's Embrace to maintain passive Air Attunement & Dexterity.",
        "template": None,
        "was_active": True
    },
    "Shield of Air": {
        "filename": "shield_of_air.png",
        "advice": "Re-cast Shield of Air immediately to maintain damage mitigation & passive Air XP.",
        "template": None,
        "was_active": True
    },
    "Dash": {
        "filename": "dash.png",
        "advice": "Re-cast Dash to maintain movement speed for kiting and passive Air Attunement XP.",
        "template": None,
        "was_active": True
    },
    "Blessing of Honor": {
        "filename": "blessing_of_honor.png",
        "advice": "Visit the Devotional of Honor to refresh your Dexterity and Combat Health Regen buff.",
        "template": None,
        "was_active": True
    },
    "Blessing of Sacrifice": {
        "filename": "blessing_of_sacrifice.png",
        "advice": "Visit the Devotional of Sacrifice to refresh your Focus and Focus Regen buff.",
        "template": None,
        "was_active": True
    },
    "Blessing of Theurgy": {
        "filename": "blessing_of_theurgy.png",
        "advice": "Visit the Devotional of Theurgy to refresh your Spell Critical Damage and Attunement buff.",
        "template": None,
        "was_active": True
    }
}

# Skills already at or above your 131 baseline
CAPPED_ENDGAME_SKILLS = {
    "Shield of Air", "Ranged Combat", "Draw Strength", "Eagle Eye",
    "Aimed Shot", "Berserker's Stance", "Blink", "Chain Lightning",
    "Dash", "Discharge", "Gust", "Lightning", "Lightning Storm",
    "Rapid Discharge", "Well Grounded"
}

# =========================================================================
# XP CURVE CALCULATORS
# =========================================================================
def get_xp_required_for_next_spec_level(current_level):
    if current_level < 100:
        base_marginal = 100.0 * (1.0615 ** (current_level - 1))
    else:
        base_100 = 100.0 * (1.0615 ** 99)
        base_marginal = base_100 * (1.10 ** (current_level - 100))
    return int(round(base_marginal * 20))

# =========================================================================
# CLEAN TWO-PART TERMINAL DASHBOARD (NO ANSI OVERLAP BUGS)
# =========================================================================
EVENT_HISTORY = []
MAX_EVENTS = 14

def add_event(msg):
    timestamp = time.strftime("%H:%M:%S")
    EVENT_HISTORY.append(f"[{timestamp}] {msg}")
    if len(EVENT_HISTORY) > MAX_EVENTS:
        EVENT_HISTORY.pop(0)

def render_dashboard(state_dict):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("========================================================================================")
    print("                 SOTA AEROMANCER DUAL-SPEC & HUD OPTIMIZATION TRACKER")
    print("========================================================================================")
    print(" RECENT ALERTS & TELEMETRY LOG:")
    if not EVENT_HISTORY:
        print("   (Waiting for combat XP, buff changes, or HUD scans...)")
    else:
        for line in EVENT_HISTORY:
            print(f"   {line}")
    
    # Pad empty event lines so the bottom block stays in a steady visual position
    for _ in range(MAX_EVENTS - len(EVENT_HISTORY)):
        print("")

    elapsed_hours = max((time.time() - state_dict['start_time']) / 3600.0, 0.0001)

    # Air Spec math
    air_lvl = state_dict['air_spec_level']
    air_cur = state_dict['air_spec_xp_in_level']
    air_req = get_xp_required_for_next_spec_level(air_lvl)
    air_rem = max(0, air_req - air_cur)
    air_pct = min(100.0, (air_cur / air_req) * 100.0) if air_req > 0 else 100.0
    air_rate = state_dict['session_air_spec_xp'] / elapsed_hours
    air_eta = f"{(air_rem / air_rate):.2f}h" if air_rate > 0 else "--"

    # Focus Spec math
    foc_lvl = state_dict['focus_spec_level']
    foc_cur = state_dict['focus_spec_xp_in_level']
    foc_req = get_xp_required_for_next_spec_level(foc_lvl)
    foc_rem = max(0, foc_req - foc_cur)
    foc_pct = min(100.0, (foc_cur / foc_req) * 100.0) if foc_req > 0 else 100.0
    foc_rate = state_dict['session_focus_spec_xp'] / elapsed_hours
    foc_eta = f"{(foc_rem / foc_rate):.2f}h" if foc_rate > 0 else "--"

    # Combined Dual-Spec Cap
    combined_spec = air_lvl + foc_lvl
    spec_headroom = max(0, DUAL_SPEC_CAP - combined_spec)

    # Adventurer Level 131 -> 132 math
    adv_lvl = state_dict['adv_level']
    adv_rem = max(0, state_dict['adv_xp_to_next'])
    adv_rate = state_dict['session_adv_xp'] / elapsed_hours
    adv_eta = f"{(adv_rem / adv_rate):.2f}h" if adv_rate > 0 else "--"
    est_pool = max(0, state_dict['banked_pool'] - state_dict['session_spent_xp'])

    print("========================================================================================")
    print(f" AEROMANCER DUAL-SPEC CAP: {combined_spec} / {DUAL_SPEC_CAP} ({spec_headroom} levels remaining to 80/80 target)")
    print(f"  * Air Spec   [Lvl {air_lvl}->{air_lvl+1}]: {air_cur:,}/{air_req:,} XP ({air_pct:.1f}%) | Rem: {air_rem:,} | ETA: {air_eta}")
    print(f"  * Focus Spec [Lvl {foc_lvl}->{foc_lvl+1}]: {foc_cur:,}/{foc_req:,} XP ({foc_pct:.1f}%) | Rem: {foc_rem:,} | ETA: {foc_eta}")
    print("----------------------------------------------------------------------------------------")
    print(f" ADVENTURER [Lvl {adv_lvl}->{adv_lvl+1}]: Rem: {adv_rem:,} XP | Pace: {int(adv_rate):,} XP/hr | ETA: {adv_eta}")
    print(f" BANKED XP POOL: ~{est_pool:,} XP | Session Spent: {state_dict['session_spent_xp']:,} XP | Active Log: {state_dict['log_name']}")
    print("========================================================================================")
    print(" Press Ctrl+C in this window to stop.")

# =========================================================================
# OPENCV MULTI-BUFF TEMPLATE MATCHING
# =========================================================================
def load_all_templates():
    for buff_name, data in TARGET_BUFFS.items():
        path = os.path.join(BASE_DIR, data["filename"])
        if os.path.exists(path):
            template = cv2.imread(path, cv2.IMREAD_COLOR)
            if template is not None:
                data["template"] = template
                add_event(f"[OK] Loaded icon: {data['filename']} ({template.shape[1]}x{template.shape[0]}px)")
        else:
            add_event(f"[WARN] Missing icon: {data['filename']}")

def check_buffs_on_screen(frame_bgr, threshold=0.75):
    changed = False
    try:
        x1, y1, x2, y2 = BUFF_BAR_ROI
        buff_crop = frame_bgr[y1:y2, x1:x2]

        for buff_name, data in TARGET_BUFFS.items():
            template_img = data["template"]
            if template_img is None:
                continue

            if (template_img.shape[0] > buff_crop.shape[0] or 
                template_img.shape[1] > buff_crop.shape[1]):
                continue

            result = cv2.matchTemplate(buff_crop, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            is_active = max_val >= threshold

            if not is_active and data["was_active"]:
                add_event(f"[ALERT] {buff_name} dropped! ({max_val:.2f}) -> {data['advice']}")
                data["was_active"] = False
                changed = True
            elif is_active and not data["was_active"]:
                add_event(f"[OK] {buff_name} re-applied! ({max_val:.2f})")
                data["was_active"] = True
                changed = True
    except Exception as e:
        add_event(f"[Visual Scan Error]: {e}")
        changed = True
    return changed

# =========================================================================
# HUD OCR CHECKS (STATS SHEET & RIGHT-SIDE TOTA METER)
# =========================================================================
def read_hud_region_text(bgr_crop):
    if not HAS_TESSERACT:
        return ""
    try:
        large = cv2.resize(bgr_crop, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(large, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        return pytesseract.image_to_string(Image.fromarray(thresh), config='--psm 6')
    except Exception:
        return ""

def check_hud_ocr(full_screen_bgr, state_dict):
    changed = False
    if not HAS_TESSERACT:
        return False

    # 1. Left-Edge Character Stats Sheet
    sx1, sy1, sx2, sy2 = STATS_PANEL_ROI
    stats_text = read_hud_region_text(full_screen_bgr[sy1:sy2, sx1:sx2])
    if stats_text:
        weight_match = re.search(r"Weight:\s*([\d,]+\.\d+)\s*/\s*([\d,]+\.\d+)", stats_text)
        if weight_match:
            cur_w = float(weight_match.group(1).replace(",", ""))
            max_w = float(weight_match.group(2).replace(",", ""))
            if cur_w > max_w and not state_dict['warned_overweight']:
                add_event(f"[HUD ALERT] Overencumbered ({cur_w:.1f}/{max_w:.1f})! Movement & combat slowed.")
                state_dict['warned_overweight'] = True
                changed = True
            elif cur_w <= max_w:
                state_dict['warned_overweight'] = False

        dur_match = re.search(r"Weapon Durability Effectiveness:\s*([\d\.]+)%", stats_text)
        if dur_match:
            dur_pct = float(dur_match.group(1))
            if dur_pct < 50.0 and not state_dict['warned_durability']:
                add_event(f"[HUD ALERT] Weapon Durability Effectiveness low ({dur_pct}%)! Repair crossbow soon.")
                state_dict['warned_durability'] = True
                changed = True
            elif dur_pct >= 50.0:
                state_dict['warned_durability'] = False

    # 2. Middle-Right TotA Meter Overlay
    mx1, my1, mx2, my2 = TOTA_METER_ROI
    meter_text = read_hud_region_text(full_screen_bgr[my1:my2, mx1:mx2])
    if meter_text:
        pool_match = re.search(r"Pool\s*([\d,]{6,})", meter_text)
        if pool_match:
            live_pool = int(pool_match.group(1).replace(",", ""))
            if abs(live_pool - state_dict['banked_pool']) > 5000:
                state_dict['banked_pool'] = live_pool
                state_dict['session_spent_xp'] = 0
                changed = True

    return changed

# =========================================================================
# NATIVE CHAT LOG PARSING (WITH MIDNIGHT ROLLOVER)
# =========================================================================
def get_latest_chat_log():
    possible_dirs = [
        CUSTOM_LOG_DIR,
        os.path.expanduser(r'~\AppData\Roaming\Catnip Games\Shroud of the Avatar\ChatLogs'),
        os.path.expanduser(r'~\AppData\Roaming\Portalarium\Shroud of the Avatar\ChatLogs'),
        os.path.expanduser(r'~\Documents\Shroud of the Avatar\ChatLogs')
    ]
    for log_dir in possible_dirs:
        if log_dir and os.path.exists(log_dir):
            list_of_files = glob.glob(os.path.join(log_dir, '*.txt'))
            if list_of_files:
                return max(list_of_files, key=os.path.getctime)
    return None

def parse_log_telemetry(file_path, state_dict):
    if not file_path or not os.path.exists(file_path):
        return False

    changed = False
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if state_dict['file_position'] == 0:
                f.seek(0, 2)
                state_dict['file_position'] = f.tell()
                return False

            f.seek(state_dict['file_position'])
            lines = f.readlines()
            state_dict['file_position'] = f.tell()

            skill_xp_pattern = re.compile(r"You gained (\d+) experience towards (.+?)\.")
            adv_xp_pattern = re.compile(r"You gained (\d+) adventurer experience", re.IGNORECASE)

            for line in lines:
                adv_match = adv_xp_pattern.search(line)
                if adv_match:
                    gained = int(adv_match.group(1))
                    state_dict['session_adv_xp'] += gained
                    state_dict['adv_xp_to_next'] = max(0, state_dict['adv_xp_to_next'] - gained)
                    state_dict['banked_pool'] += gained
                    changed = True

                match = skill_xp_pattern.search(line)
                if match:
                    xp_amount = int(match.group(1))
                    skill_name = match.group(2).strip()
                    state_dict['session_spent_xp'] += xp_amount
                    changed = True

                    if "Air Magic Specialization" in skill_name:
                        state_dict['session_air_spec_xp'] += xp_amount
                        state_dict['air_spec_xp_in_level'] += xp_amount
                        req_xp = get_xp_required_for_next_spec_level(state_dict['air_spec_level'])
                        while state_dict['air_spec_xp_in_level'] >= req_xp:
                            state_dict['air_spec_xp_in_level'] -= req_xp
                            state_dict['air_spec_level'] += 1
                            add_event(f"*** LEVEL UP! Air Magic Specialization reached Level {state_dict['air_spec_level']}! ***")
                            req_xp = get_xp_required_for_next_spec_level(state_dict['air_spec_level'])
                        add_event(f"[AIR SPEC] +{xp_amount:,} XP (Lvl {state_dict['air_spec_level']})")

                    elif "Focus Specialization" in skill_name:
                        state_dict['session_focus_spec_xp'] += xp_amount
                        state_dict['focus_spec_xp_in_level'] += xp_amount
                        req_xp = get_xp_required_for_next_spec_level(state_dict['focus_spec_level'])
                        while state_dict['focus_spec_xp_in_level'] >= req_xp:
                            state_dict['focus_spec_xp_in_level'] -= req_xp
                            state_dict['focus_spec_level'] += 1
                            add_event(f"*** LEVEL UP! Focus Specialization reached Level {state_dict['focus_spec_level']}! ***")
                            req_xp = get_xp_required_for_next_spec_level(state_dict['focus_spec_level'])
                        add_event(f"[FOCUS SPEC] +{xp_amount:,} XP (Lvl {state_dict['focus_spec_level']})")

                    elif skill_name in CAPPED_ENDGAME_SKILLS:
                        add_event(f"[XP LEAK WARNING] +{xp_amount:,} XP spent on {skill_name} (already 131+!). Lock to Not Training.")
                    else:
                        add_event(f"[XP GAIN] +{xp_amount:,} XP -> {skill_name}")

    except Exception as e:
        add_event(f"[Log Read Error]: {e}")
        changed = True
    return changed

# =========================================================================
# MAIN ENGINE OPTIMIZATION LOOP
# =========================================================================
def main_loop():
    telemetry_state = {
        'file_position': 0,
        'log_path': None,
        'log_name': 'Not found',
        'start_time': time.time(),
        'air_spec_level': AIR_SPEC_CONFIG['current_level'],
        'air_spec_xp_in_level': AIR_SPEC_CONFIG['xp_into_current_level'],
        'session_air_spec_xp': 0,
        'focus_spec_level': FOCUS_SPEC_CONFIG['current_level'],
        'focus_spec_xp_in_level': FOCUS_SPEC_CONFIG['xp_into_current_level'],
        'session_focus_spec_xp': 0,
        'adv_level': ADVENTURER_CONFIG['current_level'],
        'adv_xp_to_next': ADVENTURER_CONFIG['xp_to_next_level'],
        'banked_pool': ADVENTURER_CONFIG['banked_xp_pool'],
        'session_adv_xp': 0,
        'session_spent_xp': 0,
        'warned_overweight': False,
        'warned_durability': False
    }

    load_all_templates()

    active_log = get_latest_chat_log()
    if active_log:
        telemetry_state['log_path'] = active_log
        telemetry_state['log_name'] = os.path.basename(active_log)
        add_event(f"[OK] Tailing log: {telemetry_state['log_name']}")
    else:
        add_event("[WARN] Chat log not found. Check CUSTOM_LOG_DIR.")

    render_dashboard(telemetry_state)

    loop_counter = 0
    while True:
        needs_redraw = False

        # Check for midnight chat log rollover every 10 seconds
        if loop_counter % 5 == 0:
            newest_log = get_latest_chat_log()
            if newest_log and newest_log != telemetry_state['log_path']:
                telemetry_state['log_path'] = newest_log
                telemetry_state['log_name'] = os.path.basename(newest_log)
                telemetry_state['file_position'] = 0
                add_event(f"[LOG ROLLOVER] Switched to new daily log: {telemetry_state['log_name']}")
                needs_redraw = True

        if telemetry_state['log_path']:
            if parse_log_telemetry(telemetry_state['log_path'], telemetry_state):
                needs_redraw = True

        # Capture full 2560x1440 screen once per cycle
        try:
            full_shot = ImageGrab.grab()
            full_bgr = cv2.cvtColor(np.array(full_shot), cv2.COLOR_RGB2BGR)

            if check_buffs_on_screen(full_bgr, MATCH_THRESHOLD):
                needs_redraw = True

            if loop_counter % 6 == 0:
                if check_hud_ocr(full_bgr, telemetry_state):
                    needs_redraw = True
        except Exception as e:
            add_event(f"[Screen Capture Error]: {e}")
            needs_redraw = True

        if needs_redraw:
            render_dashboard(telemetry_state)

        loop_counter += 1
        time.sleep(2)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nSotA Tracker stopped.")
    except Exception:
        import traceback
        print("\n================ CRASH REPORT ================")
        traceback.print_exc()
        print("==============================================")
        input("\nPress Enter to close this window...")
