# product_validators.py – Validated against EP XPL & XQE Layout Planning Specifications

def validate_xpl201(aisle_width_m, load_weight_kg, pallet_type=""):
    """
    XPL201 (Transport / Cross Docking).
    Vehicle capacity: 2000 kg.
    Euro pallet structural limit: ~1500 kg (dynamic load).
    Minimum aisle: 1.5 m one-way driving.
    """
    issues = []
    color = "green"

    # Pallet structural limit — separate from vehicle capacity
    if pallet_type == "Euro" and load_weight_kg > 1500:
        issues.append(
            f"Note: XPL201 can carry up to 2000 kg, but a standard Euro pallet is only structurally rated for ~1500 kg under dynamic load. "
            f"Current load: {load_weight_kg} kg on a Euro pallet. "
            "Consider using an Industrial or custom pallet for loads above 1500 kg."
        )
        color = "orange"

    # Vehicle capacity hard limit
    if load_weight_kg > 2000:
        issues.append(f"XPL201 maximum vehicle load capacity is 2000 kg. Current: {load_weight_kg} kg.")
        color = "red"

    # Aisle width
    if aisle_width_m and aisle_width_m < 1.5:
        issues.append(
            f"Minimum aisle width for XPL201 (one-way driving) is 1.5 m. Current: {aisle_width_m} m.\n"
            "Reference aisle table (Euro Pallets):\n"
            "  • One-way driving: 1.5 m\n"
            "  • Two-way driving: 3.0 m\n"
            "  • One-way turning: 2.3 m\n"
            "  • Two-way turning: 3.8 m\n"
            "  • Loading/Unloading one-side: 3.0 m\n"
            "  • Loading/Unloading both-sides: 3.5–5.6 m"
        )
        color = "red"
    elif aisle_width_m and aisle_width_m < 1.8:
        issues.append(
            f"Aisle {aisle_width_m} m is technically acceptable (≥1.5 m) but 1.8 m is recommended for "
            "better safety fields, higher speed, and easier commissioning."
        )
        if color == "green":
            color = "orange"

    if issues:
        return False, "\n\n".join(issues), color

    return True, "XPL201 – Within specification (Transport / Cross Docking)", "green"


def validate_xqe122(load_weight_kg, max_stacking_height_m, aisle_width_mm=0):
    """
    XQE122 (Stacking / Conveyor).
    Vehicle capacity: 1500 kg (900 kg above 4.5 m, 1200 kg above 3.5 m).
    Minimum aisle width: 2900 mm (straight passage, one-way).
    Floor stacking channel: truck body 1240 mm + 200 mm clearance each side = 1640 mm min channel width.
    Floor stacking gap: 200 mm between pallets/boxes in ALL directions.
    Rack stacking gap: 75 mm between pallets on shelf (standard).
    """
    issues = []
    color = "green"

    # Load capacity
    if load_weight_kg > 1500:
        issues.append(f"XQE122 maximum load capacity is 1500 kg. Current: {load_weight_kg} kg.")
        color = "red"
    elif load_weight_kg > 1200 and max_stacking_height_m > 3.5:
        issues.append(
            f"For loads above 1200 kg, maximum stacking height is 3.5 m. "
            f"Current: {load_weight_kg} kg at {max_stacking_height_m} m."
        )
        color = "red"
    elif load_weight_kg > 900 and max_stacking_height_m > 4.5:
        issues.append(
            f"For loads above 900 kg, maximum stacking height is 4.5 m. "
            f"Current: {load_weight_kg} kg at {max_stacking_height_m} m."
        )
        color = "red"
    elif max_stacking_height_m > 5.5:
        issues.append(
            f"XQE122 maximum stacking height is 5.5 m (at ≤900 kg). "
            f"Current: {max_stacking_height_m} m."
        )
        color = "red"

    # Aisle width — minimum 2900 mm straight passage (one-way)
    if aisle_width_mm and aisle_width_mm < 2900:
        issues.append(
            f"Minimum aisle width for XQE122 is 2900 mm (straight passage, one-way). "
            f"Current: {aisle_width_mm} mm.\n"
            "Note: XQE truck body width is 1240 mm. Add 200 mm clearance on each side for safe operation."
        )
        if color == "green":
            color = "orange"

    if issues:
        return False, "\n\n".join(issues), color

    return True, "XQE122 – Within specification (Stacking / Conveyor)", "green"


def validate_xna121_151(aisle_width_m, load_weight_kg, max_stacking_height_m, model):
    """
    XNA121 / XNA151 (Narrow Aisle).
    Minimum aisle: 1.78 m.
    """
    issues = []
    color = "green"

    if aisle_width_m and aisle_width_m < 1.78:
        issues.append(f"Minimum aisle width for XNA is 1.78 m. Current: {aisle_width_m} m.")
        color = "red"
    elif aisle_width_m and aisle_width_m > 2.0:
        issues.append(
            f"XNA is optimised for aisles up to 2.0 m. "
            f"Current: {aisle_width_m} m — wider aisles may reduce efficiency."
        )
        if color == "green":
            color = "orange"

    if model == "XNA121 (up to 8.5m)":
        if max_stacking_height_m > 8.5:
            issues.append(f"XNA121 maximum lift height is 8.5 m. Current: {max_stacking_height_m} m.")
            color = "red"
        if load_weight_kg > 1200:
            issues.append(f"XNA121 maximum load is 1200 kg. Current: {load_weight_kg} kg.")
            color = "red"
    else:
        if max_stacking_height_m > 13.0:
            issues.append(f"XNA151 maximum lift height is 13.0 m. Current: {max_stacking_height_m} m.")
            color = "red"
        if load_weight_kg > 1500:
            issues.append(f"XNA151 maximum load is 1500 kg. Current: {load_weight_kg} kg.")
            color = "red"

    if issues:
        return False, "\n\n".join(issues), color

    return True, f"{model} – Within specification (Narrow Aisle)", "green"
