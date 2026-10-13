import os
import re
import json
import zipfile
import base64
from io import BytesIO
from datetime import datetime

import streamlit as st
from docxtpl import DocxTemplate
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from translations import t, LANGUAGES

TEMPLATE_PATH = "template.docx"
LOGO_PATH = "Picture2.png"

XPL_PDF_CANDIDATES = [
    "1.9_XPL_Layout_planning_Specification.pdf",
    "1.9_XPL_Layout_Planning_Specification.pdf",
]

# Resource catalogue grouped by section.
# Each entry: (label, filename, mime, description, icon [, candidate_key])
RESOURCES = {
    "Layout References": [
        (
            "XQE122 Layout Requirements",
            "1.1_Layout_Requirment_XQE_.pdf",
            "application/pdf",
            "Aisle planning, clearances, floor stacking and rack stacking specifications for the XQE122 stacking AMR.",
            "📐",
        ),
        (
            "XNA Layout Requirements (Draft)",
            "1.3_Layout_Requirment_XNA.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "Draft layout and aisle planning specification for XNA121 / XNA151 narrow-aisle AMRs.",
            "📐",
            None,
            True,  # coming_soon
        ),
        (
            "XPL201 Layout Planning Specification (Draft)",
            None,  # resolved at runtime from candidates
            "application/pdf",
            "Aisle planning and layout specification for the XPL201 pallet mover AMR.",
            "📐",
            "XPL_PDF_CANDIDATES",
            True,  # coming_soon
        ),
    ],

    "System Requirements": [
        (
            "EP System Requirements",
            "5_System Requirments.pdf",
            "application/pdf",
            "Network, WiFi, IT infrastructure and connectivity requirements for EP AGV fleet deployment.",
            "🛜",
        ),
        (
            "AGV Pallet Compatibility Reference",
            "2_AGV - Pallet Compatibility Reference.pdf",
            "application/pdf",
            "Pallet and load compatibility requirements for XQE / XPL / XNA / XSC AGV models — covers transport, stacking, custom sizes, and load condition checks.",
            "🪵",
        ),
    ],
}


def find_existing_file(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _append_report_photos(document, route_details, conveyor_pictures, conveyor_captions):
    """Append uploaded raster images to the Word report with their survey context."""
    image_extensions = {"png", "jpg", "jpeg", "bmp", "tif", "tiff"}
    sections = []
    for route in route_details or []:
        photos = route.get("photos") or []
        if photos:
            sections.append((
                route.get("flow_name", "Material Flow"),
                f"{route.get('from', '')} → {route.get('to', '')}",
                photos,
            ))
    conveyor_items = [
        {"file": picture, "caption": conveyor_captions[i] if i < len(conveyor_captions) else ""}
        for i, picture in enumerate(conveyor_pictures or [])
    ]
    if conveyor_items:
        sections.append(("Conveyor", "Conveyor interface", conveyor_items))
    if not sections:
        return

    document.add_page_break()
    title = document.add_paragraph()
    title_run = title.add_run("Site Survey Photographs")
    title_run.bold = True
    title_run.font.size = Pt(16)
    for flow_name, route_name, photo_items in sections:
        flow_heading = document.add_paragraph()
        flow_heading_run = flow_heading.add_run(flow_name)
        flow_heading_run.bold = True
        flow_heading_run.font.size = Pt(13)
        document.add_paragraph(route_name)
        for photo_item in photo_items:
            uploaded_file = photo_item.get("file")
            if not uploaded_file:
                continue
            extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
            if extension not in image_extensions:
                document.add_paragraph(f"Attachment: {uploaded_file.name} (not embeddable as an image)")
                continue
            try:
                picture_paragraph = document.add_paragraph()
                picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                picture_paragraph.add_run().add_picture(BytesIO(uploaded_file.getvalue()), width=Inches(6.0))
                caption = (photo_item.get("caption") or uploaded_file.name).strip()
                caption_paragraph = document.add_paragraph()
                caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption_run = caption_paragraph.add_run(caption)
                caption_run.italic = True
                caption_run.font.size = Pt(9)
            except Exception as exc:
                document.add_paragraph(f"Could not embed {uploaded_file.name}: {exc}")


@st.dialog("ZIP download started")
def zip_download_popup():
    st.success("✅ Your ZIP report has been downloaded successfully.")
    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#1a73e8,#0b5394);border-radius:12px;
                    padding:18px 22px;margin:12px 0;text-align:center;">
          <div style="font-size:22px;margin-bottom:6px;">📩</div>
          <div style="color:white;font-weight:700;font-size:16px;margin-bottom:4px;">
            Share this report with the EP EU Team
          </div>
          <div style="color:#cfe2ff;font-size:13px;">
            Please email the downloaded ZIP to your EP Equipment contact so the team<br>
            can review the requirements and prepare your solution proposal.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("If the browser blocked the automatic download, use the fallback download button below.")


def trigger_auto_download(file_bytes: bytes, filename: str, mime: str = "application/zip"):
    b64 = base64.b64encode(file_bytes).decode()
    import streamlit.components.v1 as components
    components.html(
        f"""
        <html>
          <body>
            <a id="auto-download-link" download="{filename}" href="data:{mime};base64,{b64}"></a>
            <script>
              const link = document.getElementById("auto-download-link");
              if (link) {{
                link.click();
              }}
            </script>
          </body>
        </html>
        """,
        height=1,
    )


def clean_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if str(v).strip())
    return value


def _format_number(value):
    if value in (None, ""):
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.2f}".rstrip("0").rstrip(".")


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_json_safe(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    # numpy 2.x scalars no longer subclass int/float — convert via .item()
    if hasattr(value, "item") and callable(value.item) and not isinstance(value, (str, bytes)):
        try:
            return _to_json_safe(value.item())
        except Exception:
            pass
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    return None


def _json_fallback(obj):
    """Last-resort JSON encoder for any type _to_json_safe didn't catch."""
    if hasattr(obj, "item") and callable(obj.item):
        try:
            return obj.item()
        except Exception:
            pass
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        return None
    return str(obj)


def _is_forbidden_session_key(key: str) -> bool:
    forbidden_prefixes = [
        "download_",
        "route_source_image_",
        "route_layout_",
        "res_dl_",
    ]
    forbidden_exact = {
        "_session_uploader",
        "cad_layout_file",
        "conveyor_picture",
        "cad_file",
        "load_session_btn",
    }

    if key in forbidden_exact:
        return True

    for prefix in forbidden_prefixes:
        if key.startswith(prefix):
            return True

    return False


def normalize_loaded_session(data: dict) -> dict:
    normalized = {}

    for k, v in (data or {}).items():
        if _is_forbidden_session_key(k):
            continue
        normalized[k] = v

    flow_steps = []
    for i in range(1, 10):
        step_value = normalized.get(f"flow_step_{i}")
        if step_value:
            flow_steps.append(step_value)

    if flow_steps:
        normalized["flow_sequence"] = flow_steps
        normalized["flow_steps"] = flow_steps
        normalized["num_flow_steps"] = len(flow_steps)

    if normalized.get("pallet_type_1") and not normalized.get("pallet_type"):
        normalized["pallet_type"] = normalized.get("pallet_type_1")

    if normalized.get("load_dimensions_1") and not normalized.get("load_dimensions"):
        normalized["load_dimensions"] = normalized.get("load_dimensions_1")

    if normalized.get("pallet_width_mm_1") and not normalized.get("pallet_width_mm"):
        normalized["pallet_width_mm"] = normalized.get("pallet_width_mm_1")

    if normalized.get("other_pallet_type_1") and not normalized.get("other_pallet_type"):
        normalized["other_pallet_type"] = normalized.get("other_pallet_type_1")

    if normalized.get("other_pallet_pickable_1") and not normalized.get("other_pallet_pickable"):
        normalized["other_pallet_pickable"] = normalized.get("other_pallet_pickable_1")

    if normalized.get("num_flow_steps") and not normalized.get("route_count"):
        normalized["route_count"] = normalized.get("num_flow_steps")

    return normalized


def rebuild_route_details_from_session():
    route_count = int(st.session_state.get("num_flow_steps", 0) or 0)
    route_details = []

    for i in range(max(route_count - 1, 0)):
        src = st.session_state.get(f"flow_step_{i+1}", "")
        dst = st.session_state.get(f"flow_step_{i+2}", "")
        if not (src and dst):
            continue

        route_details.append({
            "from": src,
            "to": dst,
            "pallets_per_hour": st.session_state.get(f"route_pallets_per_hour_{i}", 0),
            "avg_distance_m": st.session_state.get(f"route_avg_distance_{i}", 0.0),
            "flow_type": st.session_state.get(f"route_flow_type_{i}", "Simultaneous / continuous"),
        })

    if route_details:
        st.session_state["route_details"] = route_details


def _build_operational_metrics(route_details):
    process_lines = []
    notes = []
    simultaneous_total = 0.0

    for route in route_details or []:
        from_step = route.get("from", "")
        to_step = route.get("to", "")
        capacity = _to_float(route.get("pallets_per_hour"))
        flow_type = route.get("flow_type", "Simultaneous / continuous")

        if not (from_step and to_step):
            continue

        if flow_type == "No - not handled by EP automation":
            line = f"{from_step} → {to_step}: outside EP automation scope"
        else:
            line = f"{from_step} → {to_step}: {_format_number(capacity)} pallets/hour"
            if flow_type == "On request / intermittent":
                line += " (on request)"
            else:
                simultaneous_total += capacity

        process_lines.append(line)

    if any(route.get("flow_type") == "On request / intermittent" for route in (route_details or [])):
        notes.append("Some routes are triggered only on request.")
    if any(route.get("flow_type") == "No - not handled by EP automation" for route in (route_details or [])):
        notes.append("Routes outside EP automation scope are excluded from EP throughput and fleet calculations.")

    return {
        "pallets_per_hour": "\n".join(process_lines),
        "pallets_per_hour_total": simultaneous_total,
        "pallets_per_day": "",
        "operational_efficiency_note": "\n".join(notes),
    }


st.set_page_config(page_title="EP Equipment – Smart Products Site Survey", layout="wide")

for key, default in {
    "report_ready": False,
    "generated_report_buffer": None,
    "generated_safe_name": "customer",
    "generated_timestamp": "",
    "auto_zip_download_done": False,
    "zip_popup_open": False,
    "lang": "en",
    "app_mode": "expert",
    "guided_step": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

_INTERNAL_KEYS = {
    "report_ready", "generated_report_buffer", "generated_safe_name",
    "generated_timestamp", "auto_zip_download_done", "zip_popup_open",
    "lang", "app_mode", "guided_step", "agree_generate_report",
    # Generated binary blobs — not restorable from a session file
    "generated_cad_files", "generated_cad_file_bytes", "generated_cad_file_name",
    "generated_conveyor_picture_bytes", "generated_conveyor_picture_name",
    "generated_conveyor_pictures", "generated_photos",
}

with st.sidebar:
    lang_name = st.selectbox(
        t("language_label"),
        list(LANGUAGES.keys()),
        index=list(LANGUAGES.values()).index(st.session_state.get("lang", "en")),
        key="_lang_selector",
    )
    st.session_state["lang"] = LANGUAGES[lang_name]

    mode_choice = st.radio(
        t("mode_label"),
        [t("mode_expert"), t("mode_guided")],
        horizontal=True,
        key="_mode_radio",
    )
    st.session_state["app_mode"] = "guided" if mode_choice == t("mode_guided") else "expert"

    st.divider()

    _save_data = {}
    for _k, _v in st.session_state.items():
        if _k in _INTERNAL_KEYS or _k.startswith("_") or _is_forbidden_session_key(_k):
            continue
        _safe = _to_json_safe(_v)
        if _safe is not None or _v is None:
            _save_data[_k] = _safe

    _session_name_raw = st.text_input(
        "Session file name",
        value=st.session_state.get("_session_file_name", "ep_session"),
        placeholder="e.g. Ritick or CustomerABC",
        key="_session_name_input",
    )
    st.session_state["_session_file_name"] = _session_name_raw
    _session_filename = re.sub(r"[^\w\-]", "_", _session_name_raw.strip()) or "ep_session"

    st.download_button(
        t("save_session_btn"),
        data=json.dumps(_save_data, ensure_ascii=False, indent=2, default=_json_fallback),
        file_name=f"{_session_filename}.json",
        mime="application/json",
        use_container_width=True,
    )

    _uploaded_session = st.file_uploader(
        t("load_session_label"),
        type="json",
        key="_session_uploader",
    )
    if _uploaded_session is not None:
        if st.button("Load Session Now", use_container_width=True, key="load_session_btn"):
            try:
                _loaded = json.loads(_uploaded_session.getvalue().decode("utf-8"))
                _loaded = normalize_loaded_session(_loaded)

                for _k, _v in _loaded.items():
                    st.session_state[_k] = _v

                rebuild_route_details_from_session()
                st.success(t("session_loaded"))
                st.rerun()

            except Exception as e:
                st.error(f"Failed to load session file: {e}")

    st.divider()

    st.markdown(f"**{t('sidebar_summary_title')}**")
    _e = t("sum_empty")
    st.markdown(f"👤 **{t('sum_customer')}:** {st.session_state.get('customer_name') or _e}")
    st.markdown(f"📦 **{t('sum_application')}:** {', '.join(st.session_state.get('application') or []) or _e}")
    _ptype = st.session_state.get('pallet_type_1') or st.session_state.get('pallet_type') or _e
    st.markdown(f"🪵 **{t('sum_pallet')}:** {_ptype}")
    _wkg = st.session_state.get('load_weight_kg')
    st.markdown(f"⚖️ **{t('sum_weight')}:** {f'{_wkg} kg' if _wkg else _e}")
    _aisle = st.session_state.get('cross_docking_aisle') or st.session_state.get('aisle_width_m') or _e
    st.markdown(f"↔️ **{t('sum_aisle')}:** {f'{_aisle} m' if _aisle != _e else _e}")
    _flow = st.session_state.get('num_flow_steps')
    st.markdown(f"🔄 **{t('sum_flow')}:** {f'{_flow} steps' if _flow else _e}")
    _integ = st.session_state.get('integration_required') or _e
    st.markdown(f"🔗 **{t('sum_integration')}:** {_integ}")

col_logo, col_title = st.columns([1, 5])

with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=220)

with col_title:
    st.title(t("app_title"))

st.markdown(t("app_subtitle"))

from header_tab import build_header_inputs
from secondary_tab import build_material_flow_inputs
from data_flow_tab import build_data_flow_inputs
from site_conditions_tab import build_site_conditions_inputs

_app_mode = st.session_state.get("app_mode", "expert")

if _app_mode == "guided":
    _steps = [t("tab1_label"), t("tab2_label"), t("tab3_label"), t("tab4_label")]
    _step = st.session_state.get("guided_step", 0)

    st.progress((_step + 1) / len(_steps))
    _nav_l, _nav_m, _nav_r = st.columns([1, 4, 1])
    with _nav_l:
        if _step > 0 and st.button(t("btn_back"), use_container_width=True):
            st.session_state["guided_step"] = _step - 1
            st.rerun()
    with _nav_m:
        st.markdown(f"<center><b>{t('step_of', current=_step+1, total=len(_steps))}: {_steps[_step]}</b></center>", unsafe_allow_html=True)
    with _nav_r:
        if _step < len(_steps) - 1 and st.button(t("btn_next"), use_container_width=True):
            st.session_state["guided_step"] = _step + 1
            st.rerun()

    with st.expander(_steps[0], expanded=(_step == 0)):
        header_data = build_header_inputs()
    with st.expander(_steps[1], expanded=(_step == 1)):
        material_flow_data = build_material_flow_inputs()
    with st.expander(_steps[2], expanded=(_step == 2)):
        data_flow_data = build_data_flow_inputs(
            route_details=material_flow_data.get("route_details", []),
            selected_apps=header_data.get("application", []),
        )
    with st.expander(_steps[3], expanded=(_step == 3)):
        site_data = build_site_conditions_inputs()

else:
    tab1, tab2, tab3, tab4 = st.tabs(
        [t("tab1_label"), t("tab2_label"), t("tab3_label"), t("tab4_label")]
    )

    with tab1:
        header_data = build_header_inputs()
    with tab2:
        material_flow_data = build_material_flow_inputs()
    with tab3:
        data_flow_data = build_data_flow_inputs(
            route_details=material_flow_data.get("route_details", []),
            selected_apps=header_data.get("application", []),
        )
    with tab4:
        site_data = build_site_conditions_inputs()

all_data = {
    **header_data,
    **material_flow_data,
    **data_flow_data,
    **site_data,
}

selected_apps = all_data.get("application", [])
route_details = material_flow_data.get("route_details", [])
distances = [
    _to_float(route.get("avg_distance_m"))
    for route in route_details
    if _to_float(route.get("avg_distance_m")) > 0
]
all_data["avg_transport_m"] = round(sum(distances) / len(distances), 2) if distances else ""

st.header("📚 Resources & Reference Documents")
st.caption("Download technical specifications, layout guides, and customer documents for EP equipment.")

_dl_idx = 0
for _section, _items in RESOURCES.items():
    st.markdown(f"**{_section}**")
    _res_cols = st.columns(3)
    for _col_pos, _res in enumerate(_items):
        _label = _res[0]
        _fname = _res[1]
        _mime = _res[2]
        _desc = _res[3]
        _icon = _res[4]
        _candidate_key = _res[5] if len(_res) > 5 else None
        _coming_soon = _res[6] if len(_res) > 6 else False

        if _candidate_key == "XPL_PDF_CANDIDATES":
            _fname = find_existing_file(XPL_PDF_CANDIDATES)

        with _res_cols[_col_pos % 3]:
            st.markdown(
                f"""
                <div style="border:1px solid #e0e0e0;border-radius:12px;padding:16px 14px 10px 14px;
                            background:#fafafa;min-height:140px;margin-bottom:8px;">
                  <div style="font-size:28px;margin-bottom:6px;">{_icon}</div>
                  <div style="font-weight:700;font-size:14px;margin-bottom:6px;color:#1a1a2e;">{_label}</div>
                  <div style="font-size:12px;color:#555;margin-bottom:10px;">{_desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if _coming_soon:
                st.caption("🔜 Coming soon")
            elif _fname and os.path.exists(_fname):
                with open(_fname, "rb") as _f:
                    st.download_button(
                        label="Download",
                        data=_f.read(),
                        file_name=os.path.basename(_fname),
                        mime=_mime,
                        use_container_width=True,
                        key=f"res_dl_{_dl_idx}",
                    )
            else:
                st.caption("📋 Coming soon")
            _dl_idx += 1

st.markdown("### Generate Report")
st.info(
    "By generating the report, you agree that if any changes are required in the layout, "
    "the final solution must follow the standard requirement."
)

agree = st.checkbox(t("agree_label"), key="agree_generate_report")
temperature_blocked = all_data.get("temperature_range") == "Below 0°C"

if st.button(t("generate_btn"), type="primary", disabled=(not agree or temperature_blocked)):
    required_fields = ["customer_name", "customer_email", "customer_mobile", "application"]
    missing = [field for field in required_fields if not all_data.get(field)]

    if missing:
        st.error(f"Missing required fields: {', '.join(missing)}")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("Preparing report data...")
            progress_bar.progress(10)

            context = {k: clean_value(v) for k, v in all_data.items()}

            operational_metrics = _build_operational_metrics(route_details)
            context["pallets_per_hour"] = operational_metrics["pallets_per_hour"]
            context["pallets_per_day"] = operational_metrics["pallets_per_day"]
            context["pallets_per_hour_total"] = operational_metrics["pallets_per_hour_total"]
            context["operational_efficiency_note"] = operational_metrics["operational_efficiency_note"]

            pallets = all_data.get("pallets", [])
            if pallets:
                primary_pallet = pallets[0]
                context["pallet_type"] = primary_pallet.get("pallet_type", "")
                context["other_pallet_type"] = primary_pallet.get("other_pallet_type", "")
                context["other_pallet_pickable"] = primary_pallet.get("other_pallet_pickable", "")
                context["load_dimensions"] = primary_pallet.get("load_dimensions", "")
                raw_width = primary_pallet.get("pallet_width_mm", 0)
                context["pallet_width_mm"] = raw_width if raw_width else ""
            else:
                primary_pallet = {}
                context["pallet_type"] = ""
                context["other_pallet_type"] = ""
                context["other_pallet_pickable"] = ""
                context["load_dimensions"] = ""
                context["pallet_width_mm"] = ""

            # cad_files from header tab (already a list)
            _header_cad_files = all_data.get("cad_files") or []
            # cad_file from secondary/material-flow tab (now a list)
            _secondary_cad_raw = all_data.get("cad_file")
            _secondary_cad_files = _secondary_cad_raw if isinstance(_secondary_cad_raw, list) else ([_secondary_cad_raw] if _secondary_cad_raw else [])
            cad_files = _header_cad_files + _secondary_cad_files
            cad_file = cad_files[0] if cad_files else None
            # conveyor_picture is now a list
            conveyor_picture = all_data.get("conveyor_picture") or []
            if not isinstance(conveyor_picture, list):
                conveyor_picture = [conveyor_picture] if conveyor_picture else []
            photos = material_flow_data.get("photos", [])

            context["cad_filename"] = ", ".join(f.name for f in cad_files) if cad_files else ""
            context["conveyor_picture_name"] = ", ".join(f.name for f in conveyor_picture) if conveyor_picture else ""
            job_to_do_val = material_flow_data.get("job_to_do_flow") or all_data.get("task_description", "")
            context["job_to_do"] = job_to_do_val

            if not all_data.get("clearance_required"):
                context["clearance_height_m"] = ""

            def add_line(lines, label, value, suffix=""):
                if value not in (None, "", [], 0, 0.0):
                    lines.append(f"{label}: {value}{suffix}")

            aisle_lines = []
            if "Transport / Cross Docking" in selected_apps and all_data.get("cross_docking_aisle"):
                aisle_lines.append(f"XPL available aisle width: {all_data.get('cross_docking_aisle')} m")
            if "Stacking/Conveyor" in selected_apps and all_data.get("aisle_width_mm"):
                aisle_lines.append(f"XQE available aisle width: {all_data.get('aisle_width_mm')} mm")
            if "Narrow Aisle" in selected_apps and all_data.get("aisle_width_m"):
                aisle_lines.append(f"XNA available aisle width: {all_data.get('aisle_width_m')} m")
            context["aisle_width_text"] = "\n".join(aisle_lines)

            load_weight_lines = []
            if all_data.get("load_weight_kg"):
                if "Transport / Cross Docking" in selected_apps:
                    load_weight_lines.append(f"XPL load weight: {all_data.get('load_weight_kg')} kg")
                if "Stacking/Conveyor" in selected_apps:
                    load_weight_lines.append(f"XQE load weight: {all_data.get('load_weight_kg')} kg")
                if "Narrow Aisle" in selected_apps:
                    load_weight_lines.append(f"XNA load weight: {all_data.get('load_weight_kg')} kg")
            context["load_weight_text"] = "\n".join(load_weight_lines)

            stacking_height_lines = []
            if all_data.get("max_stacking_height_m"):
                if "Stacking/Conveyor" in selected_apps:
                    stacking_height_lines.append(f"XQE maximum stacking height: {all_data.get('max_stacking_height_m')} m")
                if "Narrow Aisle" in selected_apps:
                    stacking_height_lines.append(f"XNA maximum stacking height: {all_data.get('max_stacking_height_m')} m")
            context["stacking_height_text"] = "\n".join(stacking_height_lines)

            stacking_level_lines = []
            if all_data.get("stacking_level") not in (None, "", 0):
                if "Stacking/Conveyor" in selected_apps:
                    stacking_level_lines.append(f"XQE stacking level: {all_data.get('stacking_level')}")
                if "Narrow Aisle" in selected_apps:
                    stacking_level_lines.append(f"XNA stacking level: {all_data.get('stacking_level')}")
            context["stacking_level_text"] = "\n".join(stacking_level_lines)

            context["clearance_height_text"] = (
                f"Clearance height under platform / obstacles: {all_data.get('clearance_height_m')} m"
                if all_data.get("clearance_required") and all_data.get("clearance_height_m")
                else ""
            )

            storage_location_lines = []
            if "Stacking/Conveyor" in selected_apps and all_data.get("storage_locations"):
                storage_location_lines.append(f"XQE storage locations: {all_data.get('storage_locations')}")
            elif "Stacking/Conveyor" in selected_apps and all_data.get("storage_layout"):
                storage_location_lines.append(f"XQE storage layout / locations: {all_data.get('storage_layout')}")
            context["storage_locations_text"] = "\n".join(storage_location_lines)

            application_lines = []

            if "Transport / Cross Docking" in selected_apps:
                application_lines.append("XPL - Transport / Cross Docking:")
                add_line(application_lines, "Application type", all_data.get("xpl_sub_type"))

            if "Stacking/Conveyor" in selected_apps:
                application_lines.append("")
                application_lines.append("XQE - Stacking / Conveyor:")
                add_line(application_lines, "Pickup type", all_data.get("pickup_type"))
                add_line(application_lines, "Pickup type (other)", all_data.get("pickup_type_other"))
                add_line(application_lines, "Stacking type", all_data.get("stacking_type"))
                add_line(application_lines, "Stacking type (other)", all_data.get("stacking_type_other"))
                add_line(application_lines, "Storage layout description", all_data.get("storage_layout"))
                add_line(application_lines, "Storage locations", all_data.get("storage_locations"))

            if "Narrow Aisle" in selected_apps:
                application_lines.append("")
                application_lines.append("XNA - Narrow Aisle:")
                add_line(application_lines, "Preferred model", all_data.get("xna_model"))

            context["application_specific_text"] = "\n".join([line for line in application_lines if line is not None]).strip()

            summary_lines = []
            if "Transport / Cross Docking" in selected_apps:
                xpl_parts = []
                if all_data.get("xpl_sub_type"):
                    xpl_parts.append(f"Type: {all_data.get('xpl_sub_type')}")
                if all_data.get("cross_docking_aisle"):
                    xpl_parts.append(f"Aisle: {all_data.get('cross_docking_aisle')} m")
                if all_data.get("load_weight_kg"):
                    xpl_parts.append(f"Load: {all_data.get('load_weight_kg')} kg")
                if xpl_parts:
                    summary_lines.append("XPL summary: " + " | ".join(xpl_parts))

            if "Stacking/Conveyor" in selected_apps:
                xqe_parts = []
                if all_data.get("pickup_type"):
                    xqe_parts.append(f"Pickup: {all_data.get('pickup_type')}")
                if all_data.get("stacking_type"):
                    xqe_parts.append(f"Stacking: {all_data.get('stacking_type')}")
                if all_data.get("max_stacking_height_m"):
                    xqe_parts.append(f"Height: {all_data.get('max_stacking_height_m')} m")
                if all_data.get("load_weight_kg"):
                    xqe_parts.append(f"Load: {all_data.get('load_weight_kg')} kg")
                if xqe_parts:
                    summary_lines.append("XQE summary: " + " | ".join(xqe_parts))

            if "Narrow Aisle" in selected_apps:
                xna_parts = []
                if all_data.get("xna_model"):
                    xna_parts.append(f"Model: {all_data.get('xna_model')}")
                if all_data.get("aisle_width_m"):
                    xna_parts.append(f"Aisle: {all_data.get('aisle_width_m')} m")
                if all_data.get("max_stacking_height_m"):
                    xna_parts.append(f"Height: {all_data.get('max_stacking_height_m')} m")
                if all_data.get("load_weight_kg"):
                    xna_parts.append(f"Load: {all_data.get('load_weight_kg')} kg")
                if xna_parts:
                    summary_lines.append("XNA summary: " + " | ".join(xna_parts))

            context["xqe_xpl_xna_summary_text"] = "\n".join(summary_lines)

            integration_support_lines = []
            if all_data.get("data_flow_additional_notes"):
                integration_support_lines.append(f"Additional integration / positioning notes: {all_data.get('data_flow_additional_notes')}")
            context["integration_support_text"] = "\n".join(integration_support_lines)

            context["ground_gaps_text"] = (
                f"Ground gaps / depressions: {all_data.get('ground_gaps_mm')} mm"
                if all_data.get("ground_gaps_mm") not in (None, "", 0, 0.0)
                else ""
            )
            context["special_demand"] = all_data.get("special_demand", "")
            context["transport_distance_text"] = material_flow_data.get("flow_pairs_text", "")
            context["material_step_details_text"] = material_flow_data.get("step_details_text", "")
            context["special_comments"] = all_data.get("special_comments", "")

            context["system_architecture_text"] = all_data.get("system_architecture_text", "")
            context["integration_route_text"] = all_data.get("integration_route_text", "")
            context["data_flow_diagram_text"] = all_data.get("data_flow_diagram_text", "")
            context["task_flow_text"] = all_data.get("task_flow_text", "")
            context["connected_systems_text"] = all_data.get("connected_systems_text", "")
            context["status_feedback_text"] = all_data.get("status_feedback_text", "")
            context["key_data_exchange_text"] = all_data.get("key_data_exchange_text", "")

            if pallets:
                pallet_lines = []
                for idx, pallet in enumerate(pallets, start=1):
                    pallet_label = pallet.get("pallet_type", "")
                    if pallet_label == "Other" and pallet.get("other_pallet_type"):
                        pallet_label = pallet.get("other_pallet_type")
                    parts = [f"Pallet {idx}: {pallet_label}"]
                    if pallet.get("load_dimensions"):
                        parts.append(f"Dimensions: {pallet.get('load_dimensions')}")
                    if pallet.get("load_type"):
                        parts.append(f"Load type: {pallet.get('load_type')}")
                    if pallet.get("load_weight_kg"):
                        parts.append(f"Weight: {pallet.get('load_weight_kg')} kg")
                    if pallet.get("has_overhang") == "Yes":
                        parts.append(
                            f"Overhang: left {pallet.get('overhang_left_mm', 0)} mm, "
                            f"right {pallet.get('overhang_right_mm', 0)} mm"
                        )
                    else:
                        parts.append("Overhang: No")
                    raw_w = pallet.get("pallet_width_mm", 0)
                    if raw_w:
                        parts.append(f"Fork entry/depth: {raw_w} mm")
                    if pallet.get("other_pallet_pickable"):
                        parts.append(f"Can be picked by normal pallet truck: {pallet.get('other_pallet_pickable')}")
                    pallet_lines.append(", ".join(parts))
                context["pallets_summary"] = "\n".join(pallet_lines)
            else:
                context["pallets_summary"] = ""

            pallet_lines_disp = []
            ptype = primary_pallet.get("pallet_type", "")
            if ptype:
                pallet_lines_disp.append(f"Pallet type: {ptype}")
            if ptype == "Other":
                if primary_pallet.get("other_pallet_type"):
                    pallet_lines_disp.append(f"Type description: {primary_pallet.get('other_pallet_type')}")
                if primary_pallet.get("other_pallet_pickable"):
                    pallet_lines_disp.append(f"Can be picked by normal pallet truck: {primary_pallet.get('other_pallet_pickable')}")
            if primary_pallet.get("load_dimensions"):
                pallet_lines_disp.append(f"Dimensions (L×W×H): {primary_pallet.get('load_dimensions')}")
            if primary_pallet.get("load_type"):
                pallet_lines_disp.append(f"Load type: {primary_pallet.get('load_type')}")
            if primary_pallet.get("load_weight_kg"):
                pallet_lines_disp.append(f"Load weight: {primary_pallet.get('load_weight_kg')} kg")
            if primary_pallet.get("has_overhang") == "Yes":
                pallet_lines_disp.append(
                    f"Load overhang: left {primary_pallet.get('overhang_left_mm', 0)} mm; "
                    f"right {primary_pallet.get('overhang_right_mm', 0)} mm"
                )
            else:
                pallet_lines_disp.append("Load overhang: No")
            raw_w = primary_pallet.get("pallet_width_mm", 0)
            if raw_w:
                pallet_lines_disp.append(f"Fork entry/depth: {raw_w} mm")
            if len(pallets) > 1:
                pallet_lines_disp.append(f"All pallets:\n{context['pallets_summary']}")
            context["pallet_display_text"] = "\n".join(pallet_lines_disp)

            wifi_lines = []
            if all_data.get("site_wifi_available"):
                wifi_lines.append(f"Wi-Fi available: {all_data.get('site_wifi_available')}")
            if all_data.get("network_status"):
                wifi_lines.append(f"Network status: {all_data.get('network_status')}")
            if all_data.get("network_coverage"):
                wifi_lines.append(f"Coverage details: {all_data.get('network_coverage')}")
            context["wifi_info_text"] = "\n".join(wifi_lines)

            avg_t = context.get("avg_transport_m", "")
            context["avg_transport_text"] = f"{avg_t} m" if avg_t not in (None, "", 0, 0.0) else ""

            op_lines = []
            if all_data.get("shifts_per_day") not in (None, 0, ""):
                op_lines.append(f"Shifts per day: {all_data.get('shifts_per_day')}")
            if all_data.get("peak_hours") not in (None, 0, 0.0, ""):
                op_lines.append(f"Hours per shift: {all_data.get('peak_hours')}")
            if operational_metrics["pallets_per_hour"]:
                op_lines.append(f"Pallets per hour:\n{operational_metrics['pallets_per_hour']}")
            context["operational_text"] = "\n".join(op_lines)

            mf_lines = []
            if all_data.get("flow_steps") or material_flow_data.get("flow_steps"):
                mf_lines.append(f"Flow sequence: {material_flow_data.get('flow_steps', '')}")
            if material_flow_data.get("step_details_text"):
                mf_lines.append(f"Step details:\n{material_flow_data.get('step_details_text')}")
            if material_flow_data.get("material_flow_text"):
                mf_lines.append(f"Process description:\n{material_flow_data.get('material_flow_text')}")
            if all_data.get("special_comments"):
                mf_lines.append(f"Notes:\n{all_data.get('special_comments')}")
            context["material_flow_display_text"] = "\n".join(mf_lines)

            cad_lines = []
            if cad_files:
                cad_lines.append(f"CAD / layout file(s) attached: {', '.join(f.name for f in cad_files)}")
            if conveyor_picture:
                cad_lines.append(f"Conveyor picture(s) attached: {', '.join(f.name for f in conveyor_picture)}")
            context["cad_info_text"] = "\n".join(cad_lines)

            cp_lines = []
            if all_data.get("charging_status"):
                cp_lines.append(f"Charging area: {all_data.get('charging_status')}")
            if all_data.get("parking_area"):
                cp_lines.append(f"Parking / rest area: {all_data.get('parking_area')}")
            context["charging_parking_text"] = "\n".join(cp_lines)

            si_lines = []
            if all_data.get("special_demand"):
                si_lines.append(all_data.get("special_demand"))
            if all_data.get("special_comments"):
                si_lines.append(f"Additional notes: {all_data.get('special_comments')}")
            context["special_info_text"] = "\n".join(si_lines)

            jd_lines = []
            if selected_apps:
                jd_lines.append(f"Application(s): {', '.join(selected_apps)}")
            if job_to_do_val:
                jd_lines.append(f"Job-To-Do: {job_to_do_val}")
            context["job_to_do_text"] = "\n".join(jd_lines)

            if all_data.get("integration_required") == "Yes":
                df_lines = []
                if all_data.get("system_architecture_text"):
                    df_lines.append(all_data.get("system_architecture_text"))
                if all_data.get("integration_route_text"):
                    df_lines.append(f"Data flow:\n{all_data.get('integration_route_text')}")
                if all_data.get("connections_details"):
                    df_lines.append(all_data.get("connections_details"))
                context["data_flow_display_text"] = "\n\n".join(df_lines)
            else:
                context["data_flow_display_text"] = "EP DAS / WMS → EP USP Fleet Manager → AGV Fleet"

            status_text.text("Calculating recommendations...")
            progress_bar.progress(25)

            from product_validators import validate_xpl201, validate_xqe122, validate_xna121_151

            recommendations = []
            fleet_estimates = []
            validation_summary = []

            pallets_hr = _to_float(context.get("pallets_per_hour_total"))
            avg_dist = _to_float(all_data.get("avg_transport_m"))

            if "Transport / Cross Docking" in selected_apps and all_data.get("cross_docking_aisle"):
                aisle = all_data.get("cross_docking_aisle", 0)
                weight = all_data.get("load_weight_kg", 0)
                is_valid, msg, color = validate_xpl201(aisle, weight, all_data.get("pallet_type", ""))
                validation_summary.append(f"XPL201 ({all_data.get('xpl_sub_type', 'N/A')}): {msg} ({color})")
                if is_valid or color == "orange":
                    speed = 1.75
                    cycle_time = (avg_dist * 2 / speed) + 30 if avg_dist else 30
                    fleet_size = max(1, round((pallets_hr * cycle_time / 3600) * 1.2)) if pallets_hr else 1
                    recommendations.append(f"XPL201 - {all_data.get('xpl_sub_type', 'Transport')} - Fast floor-level transport up to 2000 kg")
                    fleet_estimates.append(f"XPL201: ~{fleet_size} vehicles")

            if "Stacking/Conveyor" in selected_apps and all_data.get("load_weight_kg") and all_data.get("max_stacking_height_m"):
                is_valid, msg, color = validate_xqe122(
                    all_data.get("load_weight_kg", 0),
                    all_data.get("max_stacking_height_m", 0),
                    all_data.get("aisle_width_mm", 0),
                )
                validation_summary.append(f"XQE122: {msg} ({color})")
                if is_valid or color == "orange":
                    speed = 1.0
                    cycle_time = (avg_dist * 2 / speed) + 45 if avg_dist else 45
                    fleet_size = max(1, round((pallets_hr * cycle_time / 3600) * 1.2)) if pallets_hr else 1
                    recommendations.append("XQE122 - Stacking / conveyor handling")
                    fleet_estimates.append(f"XQE122: ~{fleet_size} vehicles")

            if "Narrow Aisle" in selected_apps and all_data.get("aisle_width_m") and all_data.get("xna_model"):
                model = all_data.get("xna_model", "XNA121 (up to 8.5m)")
                is_valid, msg, color = validate_xna121_151(
                    all_data.get("aisle_width_m", 0),
                    all_data.get("load_weight_kg", 0),
                    all_data.get("max_stacking_height_m", 0),
                    model
                )
                validation_summary.append(f"{model}: {msg} ({color})")
                if is_valid or color == "orange":
                    speed = 1.0
                    cycle_time = (avg_dist * 2 / speed) + 60 if avg_dist else 60
                    fleet_size = max(1, round((pallets_hr * cycle_time / 3600) * 1.2)) if pallets_hr else 1
                    recommendations.append(f"{model} - Narrow aisle stacking")
                    fleet_estimates.append(f"{model}: ~{fleet_size} vehicles")

            context["recommendation"] = "\n\n".join(recommendations) if recommendations else ""
            context["fleet_recommendation"] = "\n".join(fleet_estimates) if fleet_estimates else ""
            context["validation_summary"] = "\n".join(validation_summary) if validation_summary else ""

            xqe_rec_parts = [r for r in recommendations if "XQE" in r]
            xqe_rec_parts += [e for e in fleet_estimates if "XQE" in e]
            xqe_rec_parts += [v.split(": ", 1)[-1].rsplit(" (", 1)[0] for v in validation_summary if "XQE" in v]
            context["recommendation_text"] = "\n".join(xqe_rec_parts) if xqe_rec_parts else ""

            xpl_rec_parts = [r for r in recommendations if "XPL" in r]
            xpl_rec_parts += [e for e in fleet_estimates if "XPL" in e]
            xpl_rec_parts += [v.split(": ", 1)[-1].rsplit(" (", 1)[0] for v in validation_summary if "XPL" in v]
            context["xpl_recommendation"] = "\n".join(xpl_rec_parts) if xpl_rec_parts else ""

            if all_data.get("ep_wms_used") == "Yes":
                context["dasp_info"] = "EP WMS / DAS included as coordination layer above EP USP Fleet Manager."
            else:
                context["dasp_info"] = ""

            status_text.text("Generating Word report...")
            progress_bar.progress(50)

            if not os.path.exists(TEMPLATE_PATH):
                raise FileNotFoundError(f"Template file not found: {TEMPLATE_PATH}")

            doc = DocxTemplate(TEMPLATE_PATH)
            doc.render(context)
            _append_report_photos(
                doc.docx,
                route_details,
                conveyor_picture,
                all_data.get("conveyor_picture_captions", []),
            )

            report_buffer = BytesIO()
            doc.save(report_buffer)
            report_buffer.seek(0)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = all_data.get("customer_name", "customer").strip().replace(" ", "_").lower()

            st.session_state["generated_report_buffer"] = report_buffer.getvalue()
            st.session_state["generated_cad_files"] = [
                {"name": f.name, "bytes": f.getvalue()} for f in cad_files if f
            ]
            st.session_state["generated_cad_file_bytes"] = cad_file.getvalue() if cad_file else None
            st.session_state["generated_cad_file_name"] = cad_file.name if cad_file else ""

            st.session_state["generated_conveyor_pictures"] = [
                {"name": f.name, "bytes": f.getvalue()} for f in conveyor_picture
            ]
            _first_cp = conveyor_picture[0] if conveyor_picture else None
            st.session_state["generated_conveyor_picture_bytes"] = _first_cp.getvalue() if _first_cp else None
            st.session_state["generated_conveyor_picture_name"] = _first_cp.name if _first_cp else ""

            generated_photos = []
            for photo_entry in photos:
                for photo_item in photo_entry or []:
                    photo = photo_item.get("file") if isinstance(photo_item, dict) else photo_item
                    if photo:
                        generated_photos.append({"name": photo.name, "bytes": photo.getvalue()})
            st.session_state["generated_photos"] = generated_photos
            st.session_state["generated_safe_name"] = safe_name
            st.session_state["generated_timestamp"] = timestamp
            st.session_state["auto_zip_download_done"] = False
            st.session_state["zip_popup_open"] = False
            st.session_state["report_ready"] = True

            status_text.text("Report ready.")
            progress_bar.progress(100)

            st.success("Report generated successfully.")

            st.subheader("Dashboard Summary")
            st.table(
                {
                    "Key Metric": [
                        "Recommended Products",
                        "Fleet Estimate",
                        "Validation Summary",
                    ],
                    "Value": [
                        context["recommendation"],
                        context["fleet_recommendation"],
                        context["validation_summary"],
                    ],
                }
            )

        except Exception as e:
            progress_bar.progress(0)
            status_text.text("Failed.")
            st.error(f"Error during report generation: {str(e)}")

if st.session_state.get("report_ready"):
    report_bytes = st.session_state.get("generated_report_buffer")
    cad_file_bytes = st.session_state.get("generated_cad_file_bytes")
    cad_file_name = st.session_state.get("generated_cad_file_name", "")

    conveyor_picture_bytes = st.session_state.get("generated_conveyor_picture_bytes")
    conveyor_picture_name = st.session_state.get("generated_conveyor_picture_name", "")

    photos = st.session_state.get("generated_photos", [])
    safe_name = st.session_state.get("generated_safe_name", "customer")
    timestamp = st.session_state.get("generated_timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))

    final_zip_buffer = BytesIO()
    docx_filename = f"site_survey_{safe_name}_{timestamp}.docx"
    zip_filename = f"site_survey_{safe_name}_{timestamp}.zip"

    with zipfile.ZipFile(final_zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if report_bytes:
            zip_file.writestr(docx_filename, report_bytes)

        for i, photo in enumerate(photos):
            if photo and photo.get("bytes"):
                original_name = photo.get("name", f"material_flow_photo_{i+1}.png")
                zip_file.writestr(original_name, photo["bytes"])

        _conveyor_pics = st.session_state.get("generated_conveyor_pictures") or []
        if _conveyor_pics:
            for _cp in _conveyor_pics:
                if _cp.get("bytes") and _cp.get("name"):
                    zip_file.writestr(_cp["name"], _cp["bytes"])
        elif conveyor_picture_bytes and conveyor_picture_name:
            zip_file.writestr(conveyor_picture_name, conveyor_picture_bytes)

        _cad_files = st.session_state.get("generated_cad_files") or []
        if _cad_files:
            for _cf in _cad_files:
                if _cf.get("bytes") and _cf.get("name"):
                    zip_file.writestr(f"layouts/{_cf['name']}", _cf["bytes"])
        elif cad_file_bytes and cad_file_name:
            zip_file.writestr(cad_file_name, cad_file_bytes)

    final_zip_buffer.seek(0)
    final_zip_bytes = final_zip_buffer.getvalue()

    if not st.session_state.get("auto_zip_download_done"):
        st.session_state["auto_zip_download_done"] = True
        st.session_state["zip_popup_open"] = True
        trigger_auto_download(final_zip_bytes, zip_filename, "application/zip")
        st.rerun()

    if st.session_state.get("zip_popup_open"):
        st.session_state["zip_popup_open"] = False
        zip_download_popup()

    st.download_button(
        label="Download Final ZIP (fallback)",
        data=final_zip_bytes,
        file_name=zip_filename,
        mime="application/zip",
        key="download_final_zip",
    )
