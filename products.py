# products.py – Full specs from XPL and XQE Layout Planning PDFs (Euro Pallets)

PRODUCT_SPECS = {
    "XPL201": {
        "description": "For fast transport / cross docking, many point pick up to many point drop, "
                       "floor storage no stacking, up to 2000 kg.",
        "load_capacity_kg": 2000,
        "max_lift_height_m": 0.0,
        "aisle_requirements": {
            "driving_one_way": 1.8,          # m (conservative from most PDFs)
            "driving_two_way": 3.6,
            "turning_one_way": 2.3,
            "turning_two_way": 3.8,
            "loading_one_way_one_side": 3.0,
            "loading_one_way_both_sides": 3.5,
            "loading_two_way_one_side": 4.0,
            "loading_two_way_both_sides": "4.5 – 5.6",
            "note": "More aisle space allows higher driving speed, larger safety detection fields, "
                    "faster pallet throughput, easier commissioning and tuning."
        },
        "pallet_gap_mm": "200-300",
        "charging_station": {
            "length_m": 3.6,
            "width_m": 1.5,
            "side_clearance_m": 0.3,
            "rear_clearance_m": 0.5,
            "overhead_note": "No reflective or glass surfaces above"
        },
        "speed_mps": "1.5 / 2.0",
        "dimensions_mm": "1915 × 835 × 2175",
        "battery": "24V / 205Ah",
        "safety_features": "Advanced safety LiDARs, cameras, sensors; obstacle detection with stop or reroute."
    },

    "XQE122": {
        "description": "For stacking on floor, picking from conveyor, stacking on racks up to 5.5 m, "
                       "1200 kg up to 4.5 m, 1500 kg up to 3.5 m.",
        "load_capacity": {
            "1200_kg_max_height_m": 4.5,
            "1500_kg_max_height_m": 3.5,
            "absolute_max_height_m": 5.5,
            "absolute_min_height_m": 0
        },
        "aisle_requirements": {
            "straight_one_way": 2.5,
            "straight_two_way": 4.1,
            "turning_radius_reference_mm": 500,
            "note": "More aisle space improves speed, safety detection, throughput, and tuning. "
                    "See turning radius diagram for 500 mm reference."
        },
        "rack_pallet_distance_m": 0.1,
        "dense_stacking_clearance_m": 0.2,
        "charging_station": {
            "length_m": 3.6,
            "width_m": 1.5,
            "side_clearance_m": 0.3,
            "rear_clearance_m": 0.5,
            "overhead_note": "No reflective or glass surfaces above"
        }
    },

    "XNA121": {
        "description": "For narrow aisle 1800 mm dual racks both sides, 1200 kg up to 8.5 m.",
        "load_capacity_kg": 1200,
        "max_lift_height_m": 8.5,
        "min_aisle_width_m": 1.65,
        "aisle_one_sided_m": 1.844,
        "speed_mps": 1.0,
        "weight_kg": 6500
    },

    "XNA151": {
        "description": "For narrow aisle 1800 mm dual racks both sides, 1500 kg up to 13 m.",
        "load_capacity_kg": 1500,
        "max_lift_height_m": 13.0,
        "min_aisle_width_m": 1.65
    }
}  # handling added