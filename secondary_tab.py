import streamlit as st

FLOW_OPTIONS = ["Inbound", "Production", "Buffer Storage", "Rack Storage", "Floor Storage", "Outbound", "Other"]
STEP_HINTS = {
    "Inbound": "Receiving / unloading area where material enters the site.",
    "Production": "Processing or production area where the main operation happens.",
    "Buffer Storage": "Short-term holding area used to balance flow and avoid congestion.",
    "Rack Storage": "Storage in racking locations.",
    "Floor Storage": "Storage directly on the floor or in floor lanes.",
    "Outbound": "Dispatch / shipping area where material leaves the site.",
    "Other": "A customer-specific process or location.",
}


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
    st.markdown("Create one flow for each independent material route. Each flow has its own steps, throughput, distances, pictures, and captions.")
    num_flows = int(st.number_input("Number of Material Flows", min_value=1, max_value=20, value=1, step=1, key="num_material_flows"))

    material_flows, route_details, route_distances, route_images = [], [], [], []
    route_summary_lines, step_details_lines = [], []

    for flow_index in range(num_flows):
        prefix = f"material_flow_{flow_index}"
        default_name = f"Material Flow {flow_index + 1}"
        with st.expander(default_name, expanded=True):
            flow_name = st.text_input("Flow Name", value=default_name, key=f"{prefix}_name", placeholder="Example: Raw material to Line 1")
            num_steps = int(st.number_input("Number of Steps", min_value=2, max_value=20, value=3, step=1, key=f"{prefix}_num_steps"))
            sequence = []
            for step_index in range(num_steps):
                col1, col2 = st.columns([1, 1.4])
                with col1:
                    step_type = st.selectbox(f"Step {step_index + 1} Type", FLOW_OPTIONS, key=f"{prefix}_step_type_{step_index}")
                with col2:
                    step_name = st.text_input(
                        f"Step {step_index + 1} Name", value=step_type if step_type != "Other" else "",
                        key=f"{prefix}_step_name_{step_index}", placeholder="Name the exact area or process",
                    )
                sequence.append(step_name.strip() or step_type)
                st.caption(STEP_HINTS.get(step_type, ""))

            flow_routes = []
            st.markdown("#### Route details")
            for route_index in range(num_steps - 1):
                source_step, target_step = sequence[route_index:route_index + 2]
                route_key = f"{prefix}_route_{route_index}"
                st.markdown(f"**{source_step} → {target_step}**")
                col1, col2, col3 = st.columns([1, 1, 1.2])
                with col1:
                    pallets_per_hour = st.number_input("Pallets/hour", min_value=0, value=0, step=1, key=f"{route_key}_pallets_per_hour")
                with col2:
                    avg_distance = st.number_input("Average Distance [m]", min_value=0.0, value=0.0, step=1.0, key=f"{route_key}_avg_distance")
                with col3:
                    flow_type = st.selectbox(
                        "Flow Type", ["Simultaneous / continuous", "On request / intermittent", "No - not handled by EP automation"],
                        key=f"{route_key}_flow_type",
                    )
                uploaded_files = st.file_uploader(
                    f"Pictures / layout for {source_step} → {target_step}", type=["jpg", "jpeg", "png", "pdf"],
                    accept_multiple_files=True, key=f"{route_key}_images",
                )
                photo_items = []
                for photo_index, uploaded_file in enumerate(uploaded_files or []):
                    caption = st.text_input(
                        f"Caption for {uploaded_file.name}", key=f"{route_key}_caption_{photo_index}",
                        placeholder="Describe the location, direction, obstacle, or relevant detail",
                    )
                    photo_items.append({"file": uploaded_file, "caption": caption})

                route = {
                    "flow_index": flow_index, "flow_name": flow_name, "from": source_step, "to": target_step,
                    "pallets_per_hour": pallets_per_hour, "avg_distance_m": avg_distance, "flow_type": flow_type,
                    "photos": photo_items, "source_image": uploaded_files,
                }
                flow_routes.append(route)
                route_details.append(route)
                route_images.append(photo_items)
                if avg_distance > 0:
                    route_distances.append(avg_distance)
                route_label = f"{flow_name}: {source_step} → {target_step}"
                route_summary_lines.append(route_label)
                details = []
                if flow_type == "No - not handled by EP automation":
                    details.append("outside EP automation scope")
                else:
                    if avg_distance > 0:
                        details.append(f"{_format_number(avg_distance)} m")
                    if pallets_per_hour > 0:
                        details.append(f"{_format_number(pallets_per_hour)} pallets/hour")
                    if flow_type == "On request / intermittent":
                        details.append("on request")
                step_details_lines.append(route_label + (": " + ", ".join(details) if details else ""))

            material_flows.append({"name": flow_name, "sequence": sequence, "flow_steps": " → ".join(sequence), "routes": flow_routes})

    st.markdown("### Material Flow Summary")
    summary_rows = [{
        "Material Flow": flow["name"], "From": route["from"], "To": route["to"],
        "Pallets/hour": route["pallets_per_hour"], "Distance [m]": route["avg_distance_m"], "Flow Type": route["flow_type"],
    } for flow in material_flows for route in flow["routes"]]
    if summary_rows:
        st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    job_to_do_flow = st.text_input("Job-To-Do / Process Name", key="job_to_do_flow", placeholder="e.g. Inbound put-away, production feeding")
    material_flow_text = st.text_area("Material Flow Details", height=150, key="material_flow_text", placeholder="Describe triggers, priorities, exceptions, and interactions between flows.")
    special_comments = st.text_area("Special comments / direct flows / notes", height=100, key="special_comments")
    cad_file = st.file_uploader("Upload CAD / Layout File(s)", type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg"], key="cad_file", accept_multiple_files=True)

    flow_steps = "\n".join(f"{flow['name']}: {flow['flow_steps']}" for flow in material_flows)
    return {
        "material_flows": material_flows, "flow_sequence": material_flows[0]["sequence"] if material_flows else [],
        "flow_steps": flow_steps, "route_details": route_details, "route_summary": "\n".join(route_summary_lines),
        "material_flow_text": material_flow_text, "special_comments": special_comments, "distances": route_distances,
        "photos": route_images, "flow_pairs_text": "\n".join(route_summary_lines),
        "step_details_text": "\n".join(step_details_lines), "material_step_details_text": "\n".join(step_details_lines),
        "cad_file": cad_file, "job_to_do_flow": job_to_do_flow,
    }
