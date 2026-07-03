import os
import math
import streamlit as st
from datetime import datetime
from product_validators import validate_xpl201, validate_xqe122, validate_xna121_151
from translations import t

SYSTEM_REQUIREMENTS_PDF = "5_System Requirments.pdf"


def _parse_load_height_m(dimensions_text: str) -> float:
    if not dimensions_text:
        return 0.0
    try:
        parts = str(dimensions_text).replace("x", "×").replace("X", "×").split("×")
        if len(parts) >= 3:
            return float(parts[2].strip()) / 1000.0
    except Exception:
        return 0.0
    return 0.0


def _build_pallet_block(index: int) -> dict:
    suffix = f"_{index}"
    st.markdown(f"#### {t('pallet_heading', n=index)}")

    pallet_type = st.radio(
        t("pallet_type_label", n=index),
        ["Euro", "Industrial", "Other"],
        horizontal=True,
        key=f"pallet_type{suffix}",
    )

    other_pallet_type = ""
    other_pallet_pickable = ""

    if pallet_type == "Other":
        other_pallet_type = st.text_input(
            t("pallet_specify_label", n=index),
            key=f"other_pallet_type{suffix}",
        )
        other_pallet_pickable = st.radio(
            t("pallet_pickable_label"),
            ["Yes", "No"],
            horizontal=True,
            key=f"other_pallet_pickable{suffix}",
        )
        if other_pallet_pickable == "No":
            st.warning(t("pallet_pickable_warn"))

    load_dimensions = st.text_input(
        t("pallet_dimensions_label", n=index),
        value="",
        placeholder="Example: 1200×800×1500",
        key=f"load_dimensions{suffix}",
    )

    pallet_width_mm = st.number_input(
        t("pallet_width_label", n=index),
        min_value=0,
        value=0,
        step=1,
        key=f"pallet_width_mm{suffix}",
    )

    return {
        "pallet_type": pallet_type,
        "other_pallet_type": other_pallet_type,
        "other_pallet_pickable": other_pallet_pickable,
        "load_dimensions": load_dimensions,
        "pallet_width_mm": pallet_width_mm,
    }


def _apply_smart_defaults(application: list):
    """Pre-fill sensible defaults when an application is first selected."""
    defaults_applied = False

    if "Transport / Cross Docking" in application:
        if st.session_state.get("cross_docking_aisle", 0) == 0:
            st.session_state["cross_docking_aisle"] = 1.8
            defaults_applied = True
        if st.session_state.get("load_weight_kg", 0) == 0:
            st.session_state["load_weight_kg"] = 1000
            defaults_applied = True

    if "Stacking/Conveyor" in application:
        if st.session_state.get("load_weight_kg", 0) == 0:
            st.session_state["load_weight_kg"] = 1000
            defaults_applied = True
        if "max_stacking_height_m" not in st.session_state:
            st.session_state["max_stacking_height_m"] = 3.5
            defaults_applied = True
        if st.session_state.get("aisle_width_mm", 0) == 0:
            st.session_state["aisle_width_mm"] = 2800
            defaults_applied = True

    if "Narrow Aisle" in application:
        if st.session_state.get("load_weight_kg", 0) == 0:
            st.session_state["load_weight_kg"] = 1000
            defaults_applied = True
        if st.session_state.get("aisle_width_m", 0.0) == 0.0:
            st.session_state["aisle_width_m"] = 1.8
            defaults_applied = True
        if "max_stacking_height_m" not in st.session_state:
            st.session_state["max_stacking_height_m"] = 6.0
            defaults_applied = True

    if defaults_applied:
        st.info(t("smart_defaults_notice"))


def build_header_inputs():
    st.subheader("1. Basic Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{t('section_customer')}**")
        customer_name = st.text_input(
            t("field_customer_name"),
            placeholder=t("ph_customer_name"),
            key="customer_name",
        )
        customer_email = st.text_input(
            t("field_customer_email"),
            placeholder=t("ph_customer_email"),
            key="customer_email",
        )
        customer_mobile = st.text_input(
            t("field_customer_mobile"),
            placeholder=t("ph_customer_mobile"),
            key="customer_mobile",
        )

    with col2:
        st.markdown(f"**{t('section_project')}**")
        project_name = st.text_input(
            t("field_project_name"),
            placeholder=t("ph_project_name"),
            key="project_name",
        )
        project_location = st.text_input(
            t("field_project_location"),
            placeholder=t("ph_project_location"),
            key="project_location",
        )
        _sd = st.session_state.get("survey_date")
        if isinstance(_sd, str):
            try:
                st.session_state["survey_date"] = datetime.strptime(_sd, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                st.session_state["survey_date"] = datetime.today().date()
        survey_date = st.date_input(t("field_survey_date"), datetime.today().date(), key="survey_date")
        warehouse_area = st.text_input(
            t("field_warehouse_area"),
            placeholder=t("ph_warehouse_area"),
            key="warehouse_area",
        )

    add_multiple_pallets = st.checkbox(t("add_multiple_pallets"), key="add_multiple_pallets")

    pallets = [_build_pallet_block(1)]

    if add_multiple_pallets:
        if "num_additional_pallets" not in st.session_state:
            st.session_state["num_additional_pallets"] = 1
        num_additional = st.number_input(
            "Number of Additional Pallets",
            min_value=1,
            max_value=5,
            step=1,
            key="num_additional_pallets"
        )
        for i in range(2, int(num_additional) + 2):
            pallets.append(_build_pallet_block(i))

    primary_pallet = pallets[0] if pallets else {
        "pallet_type": "",
        "other_pallet_type": "",
        "other_pallet_pickable": "",
        "load_dimensions": "",
        "pallet_width_mm": 0,
    }

    st.markdown(f"### {t('section_application')}")
    application = st.multiselect(
        t("field_application"),
        ["Transport / Cross Docking", "Stacking/Conveyor", "Narrow Aisle", "Other"],
        key="application",
    )

    _apply_smart_defaults(application)

    task_description = st.text_area(
        t("field_job_to_do"),
        height=120,
        key="task_description",
        placeholder=t("ph_job_to_do"),
        help="Describe the operation flow in a simple sequence.",
    )

    st.markdown("### Application-Specific Requirements")

    load_weight_kg = 0
    max_stacking_height_m = 0.0
    stacking_level = ""

    xpl_sub_type = None
    cross_docking_aisle = None

    pickup_type = None
    pickup_type_other = ""
    stacking_type = None
    stacking_type_other = ""
    storage_layout = ""
    box_distance_mm = 0
    aisle_width_mm = 0
    conveyor_height = 0
    conveyor_picture = None
    load_at_edge = ""
    distance_from_edge = 0
    storage_locations = ""

    aisle_width_m = 0.0
    xna_model = None

    if any(a in application for a in ["Transport / Cross Docking", "Stacking/Conveyor", "Narrow Aisle"]):
        load_weight_kg = st.number_input(
            "Load Weight [kg]",
            min_value=0,
            value=0,
            step=1,
            key="load_weight_kg"
        )

        if primary_pallet["pallet_type"] == "Euro" and load_weight_kg > 1500:
            st.warning(
                f"⚠️ XPL201 can carry up to 2000 kg, but a standard Euro pallet is only structurally rated for ~1500 kg under dynamic load. "
                f"Current: {load_weight_kg} kg on Euro pallet. "
                "Use an Industrial or custom pallet for loads above 1500 kg, or confirm the actual pallet rating with your supplier."
            )

    if "Transport / Cross Docking" in application:
        xpl_sub_type = st.radio(
            "Select Application Type",
            ["Transport", "Cross Docking"],
            key="xpl_sub_type"
        )

        cross_docking_aisle = st.number_input(
            "Aisle Width in Operation Zone [m]",
            min_value=0.0,
            value=float(st.session_state.get("cross_docking_aisle", 1.8) or 1.8),
            step=0.1,
            key="cross_docking_aisle"
        )

    if "Stacking/Conveyor" in application:
        st.info("Stacking / Conveyor (XQE122): maximum 5.5 m at 900 kg")

        pickup_type = st.radio(
            "Pickup Type",
            ["Ground", "Conveyor", "Other"],
            key="pickup_type"
        )

        if pickup_type == "Other":
            pickup_type_other = st.text_input(
                "Specify Other Pickup Type",
                key="pickup_type_other"
            )

        elif pickup_type == "Conveyor":
            conveyor_height = st.number_input(
                "Conveyor Height [mm]",
                min_value=0,
                value=0,
                step=1,
                key="conveyor_height"
            )

            conveyor_picture = st.file_uploader(
                "Upload Conveyor Picture(s)",
                type=["jpg", "jpeg", "png", "pdf"],
                key="conveyor_picture",
                accept_multiple_files=True,
            )
            if conveyor_picture:
                for _cp in conveyor_picture:
                    _ext = _cp.name.rsplit(".", 1)[-1].lower()
                    if _ext in ("png", "jpg", "jpeg"):
                        st.image(_cp, caption=_cp.name, use_container_width=True)
                    else:
                        st.caption(f"Uploaded: {_cp.name}")

            load_at_edge = st.radio(
                "Does the pallet arrive at the edge of the conveyor?",
                ["Yes", "No"],
                key="load_at_edge"
            )

            if load_at_edge == "No":
                distance_from_edge = st.number_input(
                    "Distance Between Conveyor Edge and Pallet [mm]",
                    min_value=0,
                    value=0,
                    step=1,
                    key="distance_from_edge"
                )

        stacking_type = st.radio(
            "Stacking Type",
            ["Floor Stacking", "Rack Stacking", "Other"],
            key="stacking_type"
        )

        if stacking_type == "Other":
            stacking_type_other = st.text_input(
                "Specify Other Stacking Type",
                key="stacking_type_other"
            )

        if stacking_type == "Floor Stacking":
            storage_layout = st.text_area(
                "Storage Layout Description",
                height=80,
                key="storage_layout"
            )

            storage_locations = st.text_area(
                "Storage Locations / Lane Details",
                height=80,
                key="storage_locations"
            )

            box_distance_mm = st.number_input(
                "Gap Between Pallets / Boxes [mm] (all directions)",
                min_value=0,
                value=0,
                step=1,
                key="floor_box_distance_mm",
                help="XQE requires minimum 200 mm clearance between pallets/boxes in ALL directions — front, back, left, right.",
            )

            if box_distance_mm and box_distance_mm < 200:
                st.error(
                    "❌ Minimum gap between pallets/boxes for XQE floor stacking is 200 mm in ALL directions "
                    "(front, back, left, right). Current: {} mm.".format(box_distance_mm)
                )
            elif box_distance_mm:
                st.success("✅ Gap between pallets OK ({} mm ≥ 200 mm in all directions).".format(box_distance_mm))

            aisle_width_mm = st.number_input(
                "Floor Storage Channel / Aisle Width [mm]",
                min_value=0,
                value=0,
                step=1,
                key="floor_aisle_width_mm",
                help="XQE truck body is 1240 mm wide. Add 200 mm clearance on each side = 1640 mm minimum channel. Overall aisle for XQE operation: minimum 2900 mm.",
            )

            if aisle_width_mm and aisle_width_mm < 1640:
                st.error(
                    f"❌ Minimum channel width for XQE floor stacking is 1640 mm "
                    f"(truck body 1240 mm + 200 mm clearance each side). Current: {aisle_width_mm} mm."
                )
            elif aisle_width_mm:
                st.success(f"✅ Channel width OK ({aisle_width_mm} mm — above minimum 1640 mm).")

        elif stacking_type == "Rack Stacking":
            storage_locations = st.text_area(
                "Storage Locations / Rack Details",
                height=80,
                key="storage_locations"
            )

            box_distance_mm = st.number_input(
                "Gap Between Pallets on Shelf [mm]",
                min_value=0,
                value=0,
                step=1,
                key="rack_box_distance_mm",
                help="Standard minimum gap between two pallets in a rack shelf is 75 mm.",
            )

            if box_distance_mm and box_distance_mm < 75:
                st.error(
                    f"❌ Minimum gap between pallets on a rack shelf is 75 mm (standard). Current: {box_distance_mm} mm."
                )
            elif box_distance_mm:
                st.success(f"✅ Rack shelf gap OK ({box_distance_mm} mm ≥ 75 mm).")

            aisle_width_mm = st.number_input(
                "Rack Aisle Width (pallet face to pallet face) [mm]",
                min_value=0,
                value=0,
                step=1,
                key="rack_aisle_width_mm",
                help="Minimum 2900 mm for XQE rack operation (overall aisle). Minimum 2840 mm pallet-to-pallet face.",
            )

            if aisle_width_mm and aisle_width_mm < 2840:
                st.error(f"❌ Minimum rack aisle width is 2840 mm (pallet face to pallet face). Current: {aisle_width_mm} mm.")
            elif aisle_width_mm:
                st.success(f"✅ Rack aisle width OK ({aisle_width_mm} mm).")

    if "Narrow Aisle" in application:
        st.info("Narrow Aisle (XNA121 / XNA151): recommended aisle width 1.78–2.0 m")

        aisle_width_m = st.number_input(
            "Actual Aisle Width [m]",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key="aisle_width_m"
        )

        xna_model = st.selectbox(
            "Preferred Model",
            ["XNA121 (up to 8.5m)", "XNA151 (up to 13m)"],
            key="xna_model"
        )

    if "Stacking/Conveyor" in application or "Narrow Aisle" in application:
        _height_max = 5.5 if "Stacking/Conveyor" in application else 0.0
        if "Narrow Aisle" in application:
            _xna_max = 13.0 if "XNA151" in (xna_model or "") else 8.5
            _height_max = max(_height_max, _xna_max)

        _cur = min(float(st.session_state.get("max_stacking_height_m") or 0.0), _height_max)
        if st.session_state.get("max_stacking_height_m") != _cur:
            st.session_state["max_stacking_height_m"] = _cur

        max_stacking_height_m = st.number_input(
            "Maximum Stacking Height [m]",
            min_value=0.0,
            max_value=_height_max,
            value=_cur,
            step=0.1,
            key="max_stacking_height_m"
        )

        # Dynamic range hint
        _range_parts = []
        if "Stacking/Conveyor" in application:
            if load_weight_kg > 1200:
                _range_parts.append("XQE: 0.1 – 3.5 m (load > 1200 kg)")
            elif load_weight_kg > 900:
                _range_parts.append("XQE: 0.1 – 4.5 m (load > 900 kg)")
            else:
                _range_parts.append("XQE: 0.1 – 5.5 m")
        if "Narrow Aisle" in application:
            if "XNA151" in (xna_model or ""):
                _range_parts.append("XNA151: 0.1 – 13.0 m")
            else:
                _range_parts.append("XNA121: 0.1 – 8.5 m")
        if _range_parts:
            st.markdown(
                '<div style="background:#eef6fb;border-left:4px solid #2196F3;padding:5px 10px;'
                'border-radius:4px;font-size:0.88em;margin-top:-8px;">'
                "📏 <b>Select a range:</b> " + " &nbsp;|&nbsp; ".join(_range_parts) +
                "</div>",
                unsafe_allow_html=True,
            )

        load_height_m = _parse_load_height_m(primary_pallet["load_dimensions"])
        auto_level = ""

        # XQE machine max lift height
        _xqe_max_h = 5.5 if "Stacking/Conveyor" in application else 999.0

        if load_height_m > 0:
            machine_max_levels = math.floor(_xqe_max_h / load_height_m)
            if max_stacking_height_m > 0:
                customer_max_levels = math.floor(max_stacking_height_m / load_height_m)
                auto_level = str(min(machine_max_levels, customer_max_levels))
                st.info(
                    f"Pallet height: {load_height_m:.2f} m  →  "
                    f"XQE max height {_xqe_max_h} m allows **{machine_max_levels} levels**. "
                    f"Your required height {max_stacking_height_m} m = {customer_max_levels} levels. "
                    f"Suggested level: **{auto_level}**."
                )
            else:
                auto_level = str(machine_max_levels)
                st.info(
                    f"Pallet height: {load_height_m:.2f} m  →  "
                    f"XQE can stack up to **{machine_max_levels} levels** (max height {_xqe_max_h} m)."
                )
        elif max_stacking_height_m > 0:
            st.caption("Enter pallet dimensions (L×W×H mm) above to auto-calculate max stacking levels.")

        stacking_level = st.text_input(
            "Level of Stacking",
            value=auto_level,
            key="stacking_level",
            help="Number of pallets stacked on top of each other.",
        )

        # Validate manually entered level against machine max
        if stacking_level and load_height_m > 0 and "Stacking/Conveyor" in application:
            try:
                _lvl = int(stacking_level)
                _total_h = _lvl * load_height_m
                if _total_h > _xqe_max_h:
                    st.error(
                        f"❌ {_lvl} levels × {load_height_m:.2f} m = {_total_h:.2f} m — "
                        f"exceeds XQE max lift height of {_xqe_max_h} m. "
                        f"Maximum {math.floor(_xqe_max_h / load_height_m)} levels for this pallet height."
                    )
                else:
                    st.success(
                        f"✅ {_lvl} levels × {load_height_m:.2f} m = {_total_h:.2f} m — within XQE max height of {_xqe_max_h} m."
                    )
            except ValueError:
                pass

        if "Stacking/Conveyor" in application:
            if load_weight_kg <= 900 and max_stacking_height_m > 5.5:
                st.error("XQE maximum stacking height is 5.5 m.")
            elif load_weight_kg > 900 and max_stacking_height_m > 5.5:
                st.error("At 900 kg XQE can go up to 5.5 m. Above that load, please verify with engineering.")
            elif load_weight_kg > 900 and max_stacking_height_m > 4.5:
                st.warning("Above 900 kg, stacking height may need to be reduced. Please verify with engineering.")

    if "Transport / Cross Docking" in application and cross_docking_aisle:
        is_valid, msg, color = validate_xpl201(cross_docking_aisle, load_weight_kg, primary_pallet.get("pallet_type", ""))
        if color == "red":
            st.error(msg)
        elif color == "orange":
            st.warning(msg)
        else:
            st.success(msg)

    if "Stacking/Conveyor" in application and load_weight_kg and max_stacking_height_m:
        is_valid, msg, color = validate_xqe122(load_weight_kg, max_stacking_height_m, aisle_width_mm)
        if color == "red":
            st.error(msg)
        elif color == "orange":
            st.warning(msg)
        else:
            st.success(msg)

    if "Narrow Aisle" in application and xna_model and aisle_width_m and max_stacking_height_m:
        is_valid, msg, color = validate_xna121_151(aisle_width_m, load_weight_kg, max_stacking_height_m, xna_model)
        if color == "red":
            st.error(msg)
        elif color == "orange":
            st.warning(msg)
        else:
            st.success(msg)

    if any(a in application for a in ["Transport / Cross Docking", "Stacking/Conveyor", "Narrow Aisle"]):
        st.markdown(f"### {t('inline_val_title')}")
        val_cols = st.columns(len([a for a in application if a in ["Transport / Cross Docking", "Stacking/Conveyor", "Narrow Aisle"]]) or 1)
        col_idx = 0

        if "Transport / Cross Docking" in application and cross_docking_aisle and load_weight_kg:
            is_v, msg, color = validate_xpl201(cross_docking_aisle, load_weight_kg, primary_pallet.get("pallet_type", ""))
            with val_cols[col_idx]:
                if color == "green":
                    st.success(f"**XPL201** ✅\n\n{msg}")
                elif color == "orange":
                    st.warning(f"**XPL201** ⚠️\n\n{msg}")
                else:
                    st.error(f"**XPL201** ❌\n\n{msg}")
            col_idx += 1

        if "Stacking/Conveyor" in application and load_weight_kg and max_stacking_height_m:
            is_v, msg, color = validate_xqe122(load_weight_kg, max_stacking_height_m, aisle_width_mm)
            with val_cols[col_idx]:
                if color == "green":
                    st.success(f"**XQE122** ✅\n\n{msg}")
                elif color == "orange":
                    st.warning(f"**XQE122** ⚠️\n\n{msg}")
                else:
                    st.error(f"**XQE122** ❌\n\n{msg}")
            col_idx += 1

        if "Narrow Aisle" in application and xna_model and aisle_width_m and max_stacking_height_m:
            is_v, msg, color = validate_xna121_151(aisle_width_m, load_weight_kg, max_stacking_height_m, xna_model)
            with val_cols[col_idx]:
                if color == "green":
                    st.success(f"**{xna_model}** ✅\n\n{msg}")
                elif color == "orange":
                    st.warning(f"**{xna_model}** ⚠️\n\n{msg}")
                else:
                    st.error(f"**{xna_model}** ❌\n\n{msg}")

    st.markdown("### Operational Basics")
    col_op1, col_op2 = st.columns(2)

    with col_op1:
        st.info("Pallets per hour and pallets per day are calculated automatically from the process capacities entered in Material Flow.")

        pallets_per_hour = ""
        pallets_per_day = ""

        shifts_per_day = st.number_input(
            "Shifts per Day",
            min_value=0,
            max_value=10,
            value=0,
            step=1,
            key="shifts_per_day"
        )

        temperature_range = st.selectbox(
            "Temperature Range (°C)",
            ["Select temperature range", "Below 0°C", "1-10°C", "10-20°C", "20-30°C", "30-40°C"],
            key="temperature_range"
        )

        if temperature_range == "Below 0°C":
            st.error("This project is not possible for temperature below 0°C.")

    with col_op2:
        hours_per_shift = st.number_input(
            "Hours per Shift",
            min_value=0.0,
            value=0.0,
            step=0.5,
            key="peak_hours"
        )

        special_layout = st.text_area(
            "Special Layout Requirements",
            height=100,
            key="special_layout",
            help="Mention any platform, uneven area, different aisle widths, one-way route, or special layout condition."
        )

        site_wifi_available = st.radio(
            "Is WiFi available on site?",
            ["Yes", "No"],
            horizontal=True,
            key="site_wifi_available"
        )

        if site_wifi_available == "Yes":
            st.info(
                "Please refer to the EP System Requirements document to verify AGV network, latency, and WiFi coverage requirements."
            )
            if os.path.exists(SYSTEM_REQUIREMENTS_PDF):
                with open(SYSTEM_REQUIREMENTS_PDF, "rb") as f:
                    st.download_button(
                        label="📄 Download EP System Requirements",
                        data=f.read(),
                        file_name=SYSTEM_REQUIREMENTS_PDF,
                        mime="application/pdf",
                        use_container_width=True,
                    )
            network_status = st.text_area(
                "Site Network Status / WiFi Coverage Notes",
                height=80,
                key="network_status",
                placeholder="e.g. Full coverage confirmed / partial coverage in zone B / survey pending",
            )
        else:
            st.warning("WiFi is not available on site. AGVs require a stable WiFi network to operate.")
            st.info("Share the EP System Requirements document with the customer's IT team.")
            if os.path.exists(SYSTEM_REQUIREMENTS_PDF):
                with open(SYSTEM_REQUIREMENTS_PDF, "rb") as f:
                    st.download_button(
                        label="📄 Download EP System Requirements",
                        data=f.read(),
                        file_name=SYSTEM_REQUIREMENTS_PDF,
                        mime="application/pdf",
                        use_container_width=True,
                    )
            network_status = ""

    clearance_required = st.checkbox(
        "Is there any clearance under platform / obstacles?",
        key="clearance_required"
    )

    clearance_height_m = 0.0
    if clearance_required:
        clearance_height_m = st.number_input(
            "Clearance Height Under Platform / Obstacles [m]",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key="clearance_height_m"
        )

    st.markdown("### Site Layout")
    st.caption(
        "Upload any combination of CAD drawings, floor plans, photos, or PDF layouts. "
        "Supported: DWG, DXF, NWD, PDF, PNG, JPG, JPEG, TIFF, BMP, SVG, ZIP"
    )
    cad_files = st.file_uploader(
        "Upload site layout files (CAD, floor plan, images, PDF)",
        type=["dwg", "dxf", "nwd", "pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp", "svg", "zip"],
        key="cad_layout_file",
        accept_multiple_files=True,
    )

    # Use first file as primary for backward-compat (cad_file key)
    cad_file = cad_files[0] if cad_files else None

    if cad_files:
        st.markdown(f"**{len(cad_files)} file(s) uploaded:**")
        preview_cols = st.columns(min(len(cad_files), 4))
        for i, f in enumerate(cad_files):
            with preview_cols[i % 4]:
                ext = f.name.rsplit(".", 1)[-1].lower()
                if ext in ("png", "jpg", "jpeg", "bmp", "tiff", "tif"):
                    st.image(f, caption=f.name, use_container_width=True)
                else:
                    st.markdown(
                        f"<div style='border:1px solid #d9d9e3;border-radius:8px;padding:14px;"
                        f"text-align:center;font-size:12px;color:#555;'>"
                        f"📄 {f.name}</div>",
                        unsafe_allow_html=True,
                    )

    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_mobile": customer_mobile,
        "project_name": project_name,
        "project_location": project_location,
        "warehouse_area": warehouse_area,
        "survey_date": survey_date.strftime("%Y-%m-%d"),
        "application": application,
        "task_description": task_description,
        "temperature_range": temperature_range,
        "pallets": pallets,
        "pallet_type": primary_pallet["pallet_type"],
        "other_pallet_type": primary_pallet["other_pallet_type"],
        "other_pallet_pickable": primary_pallet["other_pallet_pickable"],
        "load_dimensions": primary_pallet["load_dimensions"],
        "pallet_width_mm": primary_pallet["pallet_width_mm"],
        "xpl_sub_type": xpl_sub_type,
        "cross_docking_aisle": cross_docking_aisle,
        "pickup_type": pickup_type,
        "pickup_type_other": pickup_type_other,
        "stacking_type": stacking_type,
        "stacking_type_other": stacking_type_other,
        "storage_layout": storage_layout,
        "storage_locations": storage_locations,
        "box_distance_mm": box_distance_mm,
        "aisle_width_mm": aisle_width_mm,
        "conveyor_height": conveyor_height,
        "conveyor_picture": conveyor_picture,
        "load_at_edge": load_at_edge,
        "distance_from_edge": distance_from_edge,
        "aisle_width_m": aisle_width_m,
        "xna_model": xna_model,
        "load_weight_kg": load_weight_kg,
        "max_stacking_height_m": max_stacking_height_m,
        "stacking_level": stacking_level,
        "pallets_per_hour": pallets_per_hour,
        "pallets_per_day": pallets_per_day,
        "shifts_per_day": shifts_per_day,
        "peak_hours": hours_per_shift,
        "special_layout": special_layout,
        "site_wifi_available": site_wifi_available,
        "network_status": network_status,
        "clearance_required": clearance_required,
        "clearance_height_m": clearance_height_m,
        "cad_file": cad_file,
        "cad_files": cad_files,
    }