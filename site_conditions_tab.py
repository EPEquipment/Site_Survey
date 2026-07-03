import streamlit as st


def build_site_conditions_inputs():
    st.subheader("4. Site Conditions & Safety")

    st.markdown("**Please provide only the site and support details needed for the project review.**")

    col1, col2 = st.columns(2)

    with col1:
        other_agvs = st.text_input(
            "Presence of Other AGVs / AMRs / Automated Equipment",
            placeholder="e.g. existing AGVs, conveyors, AS/RS, or other automated systems.",
            key="other_agvs"
        )

        other_traffic = st.text_input(
            "Presence of Trucks / Forklifts / Pedestrians",
            placeholder="Describe traffic density, peak times, and shared areas.",
            key="other_traffic"
        )

    with col2:
        parking_area = st.text_area(
            "Vehicle Parking & Rest Area Description",
            height=90,
            placeholder="e.g. dedicated parking / waiting zones, number of spots, and location.",
            key="parking_area"
        )

        charging_status = st.text_area(
            "Charging Area Status / Requirements",
            height=90,
            placeholder="e.g. existing chargers, power availability, required charger area, fire safety notes.",
            key="charging_status"
        )

    special_demand = st.text_area(
        "Special Demand / Customization Details",
        height=110,
        placeholder=(
            "e.g. explosion-proof requirement, low/high temperature needs, remote monitoring, "
            "semi-/fully automatic operation, custom appearance/logo, or other special demands."
        ),
        key="special_demand"
    )

    return {
        "other_agvs": other_agvs,
        "other_traffic": other_traffic,
        "parking_area": parking_area,
        "charging_status": charging_status,
        "charging_stations": charging_status,
        "special_demand": special_demand,
        # kept as blank compatibility keys so the report does not break if the template still references them
        "ramp_gradient_deg": "",
        "battery_heating": "",
        "network_coverage": "",
        "ground_gaps_mm": "",
    }
