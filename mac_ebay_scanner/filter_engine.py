import re
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    matched: bool
    reason: str
    detected_model: Optional[str] = None
    detected_chip: Optional[str] = None
    detected_ram: Optional[str] = None


class MacFilterEngine:
    """Filters eBay listings for M3 or higher MacBook Pro or Mac Studio with 128GB memory."""

    NEGATIVE_TITLE_PATTERNS = [
        # Accessories / Non-laptops
        r"\b(case|cover|sleeve|skin|screen protector|keyboard cover|shell)\b",
        r"\b(charger|power adapter|power supply|mag safe|magsafe cable|cable only)\b",
        r"\b(dock|docking station|hub|stand|bag|backpack)\b",
        r"\b(box only|empty box|box|dummy|packaging only)\b",
        r"\b(decal|sticker)\b",
        # Non-target Mac models
        r"\b(macbook air|mac\s*mini|imac)\b",
    ]

    PARTS_REPAIR_PATTERNS = [
        r"\b(for parts|parts only|not working|as is / for parts|read description|cracked|spill|water damage)\b",
        r"\b(icloud lock|activation lock|mdm|firmware lock|locked)\b",
    ]

    OLDER_CHIPS = [
        r"\b(m1|m1 pro|m1 max|m1 ultra)\b",
        r"\b(m2|m2 pro|m2 max|m2 ultra)\b",
        r"\b(intel|i3|i5|i7|i9|xeon|core 2 duo)\b",
    ]

    # Target chips: M3, M4, M5, M6, M7, M8...
    TARGET_CHIP_PATTERN = re.compile(
        r"\b(m[3-9]|m[1-9][0-9])(?:\s*(?:pro|max|ultra))?\b",
        re.IGNORECASE
    )

    # Target RAM patterns: 128GB or 256GB Unified Memory / RAM
    TARGET_RAM_PATTERNS = [
        # Explicit 128GB or 256GB RAM mentions
        r"\b(128|256)\s*(?:gb|g)?\s*(?:ram|unified memory|memory|unified|ddr|um)\b",
        r"\b(?:ram|memory|unified):\s*(128|256)\s*(?:gb)?\b",
        # "M3 Max 128GB" or "M4 Max 128GB" or "M4 Ultra 256GB"
        r"\b(m[3-9]|m[1-9][0-9])\s*(?:pro|max|ultra)?\s*(128|256)\s*(?:gb|g)?\b",
        # Model followed by 128GB or 256GB
        r"\b(128|256)\s*gb\b",
    ]

    # Non-target RAM mentions (e.g. 256GB SSD with 8GB/16GB RAM)
    OTHER_RAM_PATTERNS = [
        r"\b(8|16|18|24|32|36|48|64|96)\s*(?:gb|g)?\s*(?:ram|unified|memory)\b",
        r"\b(?:ram|memory):\s*(8|16|18|24|32|36|48|64|96)\s*(?:gb)?\b",
    ]

    def __init__(self, min_price: Optional[float] = None, max_price: Optional[float] = None, include_parts: bool = False):
        self.min_price = min_price
        self.max_price = max_price
        self.include_parts = include_parts

    def evaluate_item(self, item_summary: Dict[str, Any], item_details: Optional[Dict[str, Any]] = None) -> MatchResult:
        """
        Evaluate an item using its summary and optional full details.
        Returns a MatchResult.
        """
        title = item_summary.get("title", "")
        title_lower = title.lower()

        # 1. Price check
        price_val = None
        price_obj = item_summary.get("price") or {}
        try:
            price_val = float(price_obj.get("value", 0))
        except (ValueError, TypeError):
            pass

        if price_val is not None:
            if self.min_price is not None and price_val < self.min_price:
                return MatchResult(False, f"Price ${price_val:.2f} is below minimum ${self.min_price:.2f}")
            if self.max_price is not None and price_val > self.max_price:
                return MatchResult(False, f"Price ${price_val:.2f} is above maximum ${self.max_price:.2f}")

        # 2. Check parts / repair
        if not self.include_parts:
            # Check condition from summary
            condition = (item_summary.get("condition") or "").lower()
            if "for parts" in condition or "not working" in condition:
                return MatchResult(False, f"Condition indicates parts/repair: {condition}")

            for p in self.PARTS_REPAIR_PATTERNS:
                if re.search(p, title_lower):
                    return MatchResult(False, "Listing title indicates parts, damage, or locked state")

        # 3. Check negative title patterns (accessories, non-laptops)
        for neg in self.NEGATIVE_TITLE_PATTERNS:
            if re.search(neg, title_lower):
                # Ensure it's not a false positive (e.g. "case included" or "with sleeve" might appear, but usually accessories dominate)
                # If title starts with Case/Cover/Sleeve or has "for MacBook Pro", it's an accessory
                if re.search(r"\b(for|fits)\s+(?:apple\s+)?macbook\b", title_lower) or re.search(r"^(case|cover|sleeve|skin|bag)\b", title_lower):
                    return MatchResult(False, "Listing is an accessory (case/sleeve/charger/etc.)")
                if re.search(r"\b(box\s*only|empty\s*box)\b", title_lower):
                    return MatchResult(False, "Listing is box only")

        # 4. Target Model Detection (MacBook Pro OR Mac Studio)
        is_mbp = bool(re.search(r"\bmacbook\s*pro\b", title_lower))
        is_studio = bool(re.search(r"\bmac\s*studio\b", title_lower))

        # Check aspects if available
        aspects_dict = {}
        if item_details:
            for asp in item_details.get("localizedAspects", []):
                aspects_dict[asp.get("name", "").strip().lower()] = asp.get("value", "").strip()

            model_aspect = aspects_dict.get("model", "").lower()
            if "macbook pro" in model_aspect:
                is_mbp = True
            elif "mac studio" in model_aspect:
                is_studio = True

        if not (is_mbp or is_studio):
            return MatchResult(False, "Not a MacBook Pro or Mac Studio")

        detected_model = "MacBook Pro" if is_mbp else "Mac Studio"

        # 5. Chip Detection (Must be M3 or higher, NOT M1, M2, or Intel)
        # Check aspect first
        proc_aspect = aspects_dict.get("processor", "") or aspects_dict.get("processor model", "")
        detected_chip = None

        if proc_aspect:
            proc_lower = proc_aspect.lower()
            for old in ["m1", "m2", "intel", "i5", "i7", "i9", "xeon"]:
                if re.search(rf"\b{old}\b", proc_lower):
                    return MatchResult(False, f"Processor aspect indicates older chip: {proc_aspect}")

            m = self.TARGET_CHIP_PATTERN.search(proc_aspect)
            if m:
                detected_chip = proc_aspect

        if not detected_chip:
            # Check title for older chips (only if title explicitly states M1 or M2 without M3/M4)
            has_target_chip = bool(self.TARGET_CHIP_PATTERN.search(title))
            for old in self.OLDER_CHIPS:
                if re.search(old, title_lower) and not has_target_chip:
                    return MatchResult(False, f"Title indicates older non-target generation: {old}")

            chip_match = self.TARGET_CHIP_PATTERN.search(title)
            if chip_match:
                detected_chip = chip_match.group(0).upper()
            else:
                # If no chip in title, but it's MacBook Pro or Studio, we cannot verify M3+ unless details provide it
                if item_details and not proc_aspect:
                    return MatchResult(False, "Could not verify M3 or higher processor in listing aspects")
                elif not item_details:
                    # Might need aspect lookup
                    return MatchResult(False, "Chip generation not found in title (M3+ required)")

        # Verify chip is M3 or higher
        chip_num_match = re.search(r"m(\d+)", (detected_chip or "").lower())
        if chip_num_match:
            chip_gen = int(chip_num_match.group(1))
            if chip_gen < 3:
                return MatchResult(False, f"Detected chip M{chip_gen} is below M3 requirement")

        # 6. Memory (RAM) Detection: Must be 128GB or 256GB Unified Memory
        ram_aspect = aspects_dict.get("ram size", "") or aspects_dict.get("ram", "") or aspects_dict.get("memory", "")
        detected_ram = None

        if ram_aspect:
            ram_aspect_lower = ram_aspect.lower()
            if "256" in ram_aspect:
                detected_ram = "256GB"
            elif "128" in ram_aspect:
                detected_ram = "128GB"
            else:
                return MatchResult(False, f"RAM aspect is {ram_aspect}, not 128GB or 256GB")

        # Storage vs RAM collision check:
        # Many base Macs have 256GB SSD or 128GB SSD with 8GB/16GB RAM
        ssd_aspect = aspects_dict.get("ssd capacity", "") or aspects_dict.get("storage capacity", "") or aspects_dict.get("hard drive capacity", "")
        if ("128" in ssd_aspect.lower() or "256" in ssd_aspect.lower()) and detected_ram is None:
            return MatchResult(False, f"{ssd_aspect} is SSD storage capacity, not RAM")

        if not detected_ram:
            # Check title for other low-RAM mentions (e.g. 8GB RAM, 16GB RAM, 24GB, 36GB)
            for other_ram in self.OTHER_RAM_PATTERNS:
                if re.search(other_ram, title_lower):
                    return MatchResult(False, "Title mentions non-target RAM configuration")

            # Check if 256GB is explicitly identified as SSD in title without RAM mention
            has_256_ssd_in_title = bool(re.search(r"\b256\s*(?:gb|g)?\s*(?:ssd|storage|flash|drive|rom)\b", title_lower))
            has_explicit_target_ram = bool(re.search(r"\b(128|256)\s*(?:gb|g)?\s*(?:ram|unified|memory)\b", title_lower))

            if has_256_ssd_in_title and not has_explicit_target_ram:
                return MatchResult(False, "256GB in title refers to SSD storage, not RAM")

            # Check if title has target RAM pattern
            matched_ram_val = None
            if "256" in title_lower and not has_256_ssd_in_title:
                for p in self.TARGET_RAM_PATTERNS:
                    m = re.search(p, title_lower)
                    if m and "256" in m.group(0):
                        matched_ram_val = "256GB"
                        break

            if not matched_ram_val and "128" in title_lower:
                for p in self.TARGET_RAM_PATTERNS:
                    m = re.search(p, title_lower)
                    if m and "128" in m.group(0):
                        matched_ram_val = "128GB"
                        break

            if not matched_ram_val:
                return MatchResult(False, "Does not match 128GB or 256GB RAM pattern")

            detected_ram = matched_ram_val

        return MatchResult(
            matched=True,
            reason="Verified M3+ MacBook Pro / Mac Studio with target memory",
            detected_model=detected_model,
            detected_chip=detected_chip,
            detected_ram=detected_ram,
        )
