import streamlit as st


FLOW_TYPES = [
    "Simultaneous / continuous",
    "On request / intermittent",
    "No - not handled by EP automation",
]


def _format_number(value):
    if value in (None, ""):
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(numeric)) if numeric.is_integer() else f"{numeric:.2f}".rstrip("0").rstrip(".")


def build_material_flow_inputs():
    st.subheader("2. Material Flow")
    st.markdown(
        "Add one row for every material movement. Enter the location names exactly as they "
        "are used at the customer site; location numbers are not required."
    )

    route_count = int(st.number_input(
        "Number of Material Flow Routes",
        min_value=1,
        max_value=50,
        value=1,
        step=1,
        key="num_material_flows",
    ))

    route_details = []
    route_distances = []
    route_images = []
    route_summary_lines = []
    step_details_lines = []

    for route_index in range(route_count):
        prefix = f"material_flow_route_{route_index}"
        with st.expander(f"Material Flow {route_index + 1}", expanded=True):
            from_col, to_col = st.columns(2)
            with from_col:
                from_location = st.text_input(
                    "From Location Name",
                    key=f"{prefix}_from",
                    placeholder="Example: Inbound",
                )
            with to_col:
                to_location = st.text_input(
                    "To Location Name",
                    key=f"{prefix}_to",
                    placeholder="Example: Storage",
                )

            capacity_col, distance_col, type_col = st.columns([1, 1, 1.4])
            with capacity_col:
                pallets_per_hour = st.number_input(
                    "Number of Pallets/Hour",
                    min_value=0.0,
                    value=0.0,
                    step=0.25,
                    key=f"{prefix}_pallets_per_hour",
                )
            with distance_col:
                avg_distance = st.number_input(
                    "Average Distance [m]",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"{prefix}_avg_distance",
                )
            with type_col:
                flow_type = st.selectbox(
                    "Flow Type",
                    FLOW_TYPES,
                    key=f"{prefix}_flow_type",
                )

            uploaded_files = st.file_uploader(
                "Pictures / Layout for this Material Flow",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key=f"{prefix}_images",
            )
            photo_items = []
            for photo_index, uploaded_file in enumerate(uploaded_files or []):
                caption = st.text_input(
                    f"Caption for {uploaded_file.name}",
                    key=f"{prefix}_caption_{photo_index}",
                    placeholder="Describe the route, location, obstacle, or relevant detail",
                )
                photo_items.append({"file": uploaded_file, "caption": caption})

        from_name = from_location.strip()
        to_name = to_location.strip()
        route_name = f"Material Flow {route_index + 1}"
        route = {
            "flow_index": route_index,
            "flow_name": route_name,
            "from": from_name,
            "to": to_name,
            "pallets_per_hour": pallets_per_hour,
            "avg_distance_m": avg_distance,
            "flow_type": flow_type,
            "photos": photo_items,
            "source_image": uploaded_files,
        }
        route_details.append(route)
        route_images.append(photo_items)
        if avg_distance > 0:
            route_distances.append(avg_distance)

        route_label = f"{from_name or 'From location'} → {to_name or 'To location'}"
        route_summary_lines.append(route_label)
        detail_parts = []
        if flow_type == "No - not handled by EP automation":
            detail_parts.append("outside EP automation scope")
        else:
            if pallets_per_hour > 0:
                detail_parts.append(f"{_format_number(pallets_per_hour)} pallets/hour")
            if avg_distance > 0:
                detail_parts.append(f"{_format_number(avg_distance)} m average distance")
            if flow_type == "On request / intermittent":
                detail_parts.append("on request")
        step_details_lines.append(route_label + (": " + ", ".join(detail_parts) if detail_parts else ""))

    st.markdown("### Material Flow Summary")
    summary_rows = [{
        "From Location": route["from"],
        "To Location": route["to"],
        "Pallets/Hour": route["pallets_per_hour"],
        "Average Distance [m]": route["avg_distance_m"],
        "Flow Type": route["flow_type"],
    } for route in route_details]
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    total_pallets_per_hour = sum(
        float(route["pallets_per_hour"] or 0)
        for route in route_details
        if route["flow_type"] != "No - not handled by EP automation"
    )
    st.metric("Total Pallets/Hour", _format_number(total_pallets_per_hour))

    job_to_do_flow = st.text_input(
        "Job-To-Do / Process Name",
        key="job_to_do_flow",
        placeholder="Example: Production supply and finished-goods transport",
    )
    material_flow_text = st.text_area(
        "Material Flow Details",
        height=150,
        key="material_flow_text",
        placeholder="Describe triggers, priorities, exceptions, and interactions between flows.",
    )
    special_comments = st.text_area(
        "Special comments / direct flows / notes",
        height=100,
        key="special_comments",
    )
    cad_file = st.file_uploader(
        "Upload CAD / Layout File(s)",
        type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg"],
        key="cad_file",
        accept_multiple_files=True,
    )

    material_flows = [{
        "name": route["flow_name"],
        "sequence": [route["from"], route["to"]],
        "flow_steps": f"{route['from']} → {route['to']}",
        "routes": [route],
    } for route in route_details]
    flow_steps = "\n".join(
        f"{route['from']} → {route['to']}" for route in route_details
    )

    return {
        "material_flows": material_flows,
        "flow_sequence": material_flows[0]["sequence"] if material_flows else [],
        "flow_steps": flow_steps,
        "route_details": route_details,
        "route_summary": "\n".join(route_summary_lines),
        "material_flow_text": material_flow_text,
        "special_comments": special_comments,
        "distances": route_distances,
        "photos": route_images,
        "flow_pairs_text": "\n".join(route_summary_lines),
        "step_details_text": "\n".join(step_details_lines),
        "material_step_details_text": "\n".join(step_details_lines),
        "cad_file": cad_file,
        "job_to_do_flow": job_to_do_flow,
        "total_pallets_per_hour": total_pallets_per_hour,
    }
