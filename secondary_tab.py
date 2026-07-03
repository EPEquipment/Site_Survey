import streamlit as st


FLOW_OPTIONS = [
    "Inbound",
    "Production",
    "Buffer Storage",
    "Rack Storage",
    "Floor Storage",
    "Outbound",
]

STEP_HINTS = {
    "Inbound": "Receiving / unloading area where material enters the site.",
    "Production": "Processing or production area where the main operation happens.",
    "Buffer Storage": "Short-term holding area used to balance flow and avoid congestion.",
    "Rack Storage": "Storage in racking locations.",
    "Floor Storage": "Storage directly on the floor or in floor lanes.",
    "Outbound": "Dispatch / shipping area where material leaves the site.",
}

NEXT_STEP_OPTIONS = {
    "Inbound": ["Production", "Buffer Storage", "Rack Storage", "Floor Storage", "Outbound"],
    "Production": ["Buffer Storage", "Rack Storage", "Floor Storage", "Outbound"],
    "Buffer Storage": ["Production", "Rack Storage", "Floor Storage", "Outbound"],
    "Rack Storage": ["Production", "Buffer Storage", "Floor Storage", "Outbound"],
    "Floor Storage": ["Production", "Buffer Storage", "Rack Storage", "Outbound"],
    "Outbound": ["Production", "Buffer Storage", "Rack Storage", "Floor Storage"],
}


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


def build_material_flow_inputs():
    st.subheader("2. Material Flow")

    st.markdown("### Material Flow Sequence")
    st.markdown(
        """
> Define the route in the same order as the real operation.

- Step 1: **Inbound** = receiving / unloading
- Step 2: **Production** = process area
- Step 3: **Buffer Storage / Rack Storage / Floor Storage** = temporary or final storage
- Final step: **Outbound** = dispatch / shipping

You can create as many steps as needed. The next-step options are guided by the previous step.
"""
    )

    num_steps = st.number_input(
        "Number of Steps in Material Flow",
        min_value=2,
        value=3,
        step=1,
        key="num_flow_steps",
    )

    flow_sequence = []
    num_steps = int(num_steps)

    for i in range(1, num_steps + 1):
        if i == 1:
            options = FLOW_OPTIONS
        else:
            previous_step = flow_sequence[-1]
            options = NEXT_STEP_OPTIONS.get(previous_step, FLOW_OPTIONS) or FLOW_OPTIONS

        current_value = st.session_state.get(f"flow_step_{i}")
        default_index = options.index(current_value) if current_value in options else 0

        step_value = st.selectbox(
            f"Step {i}",
            options,
            index=default_index,
            key=f"flow_step_{i}",
        )

        flow_sequence.append(step_value)
        st.caption(f"Step {i}: {step_value} — {STEP_HINTS.get(step_value, '')}")

    flow_steps = " → ".join(flow_sequence)

    st.markdown("### Flow Details Between Steps")
    st.caption(
        "Enter only the route capacity and average travel distance here. "
        "Use 'No - not handled by EP automation' for any step that is outside EP automation scope."
    )

    route_details = []
    route_distances = []
    route_images = []
    route_summary_lines = []
    step_details_lines = []

    for i in range(len(flow_sequence) - 1):
        source_step = flow_sequence[i]
        target_step = flow_sequence[i + 1]

        st.markdown(f"#### {source_step} → {target_step}")

        col1, col2, col3 = st.columns([1, 1, 1.2])

        with col1:
            pallets_per_hour = st.number_input(
                f"Pallets/hour: {source_step} → {target_step}",
                min_value=0,
                value=0,
                step=1,
                key=f"route_pallets_per_hour_{i}",
            )

        with col2:
            avg_distance = st.number_input(
                f"Average Distance [m]: {source_step} → {target_step}",
                min_value=0.0,
                value=0.0,
                step=1.0,
                key=f"route_avg_distance_{i}",
            )

        with col3:
            default_flow_type = "On request / intermittent" if target_step == "Outbound" else "Simultaneous / continuous"
            flow_type_options = [
                "Simultaneous / continuous",
                "On request / intermittent",
                "No - not handled by EP automation",
            ]
            flow_type = st.selectbox(
                f"Flow Type: {source_step} → {target_step}",
                flow_type_options,
                index=flow_type_options.index(default_flow_type),
                key=f"route_flow_type_{i}",
            )

        source_image = st.file_uploader(
            f"Upload Image(s) / Layout for {source_step} → {target_step}",
            type=["jpg", "jpeg", "png", "pdf"],
            key=f"route_source_image_{i}",
            accept_multiple_files=True,
        )

        route = {
            "from": source_step,
            "to": target_step,
            "pallets_per_hour": pallets_per_hour,
            "avg_distance_m": avg_distance,
            "flow_type": flow_type,
            "source_image": source_image,
        }
        route_details.append(route)
        route_images.append(source_image)

        if avg_distance > 0:
            route_distances.append(avg_distance)

        route_summary_lines.append(f"{source_step} → {target_step}")

        detail_parts = []
        if flow_type == "No - not handled by EP automation":
            detail_parts.append("outside EP automation scope")
        else:
            if avg_distance > 0:
                detail_parts.append(f"{_format_number(avg_distance)} m")
            if pallets_per_hour > 0:
                detail_parts.append(f"with a capacity of {_format_number(pallets_per_hour)} pallets per hour")
            if flow_type == "On request / intermittent":
                detail_parts.append("on request")

        if detail_parts:
            step_details_lines.append(f"From {source_step} to {target_step}: " + ", ".join(detail_parts) + ".")
        else:
            step_details_lines.append(f"From {source_step} to {target_step}.")

    st.markdown("### Material Flow Summary")

    job_to_do_flow = st.text_input(
        "Job-To-Do / Process Name",
        value="",
        placeholder="e.g. Inbound put-away, production feeding, outbound replenishment",
        key="job_to_do_flow",
    )

    material_flow_text = st.text_area(
        "Material Flow Details",
        height=180,
        placeholder=(
            "Describe the actual process in words.\n"
            "Example:\n"
            "- Material arrives at inbound.\n"
            "- It is moved to rack storage.\n"
            "- Production replenishment happens on request.\n"
            "- Outbound is triggered by customer request."
        ),
        key="material_flow_text",
    )

    special_comments = st.text_area(
        "Special comments / direct flows / notes",
        height=120,
        placeholder="Add exceptions, temporary storage logic, shared zones, or customer-specific notes.",
        key="special_comments",
    )

    cad_file = st.file_uploader(
        "Upload CAD / Layout File(s)",
        type=["pdf", "dwg", "dxf", "png", "jpg", "jpeg"],
        key="cad_file",
        accept_multiple_files=True,
    )

    return {
        "flow_sequence": flow_sequence,
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
    }