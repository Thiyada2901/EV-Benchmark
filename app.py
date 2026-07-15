import streamlit as st
import pandas as pd
import numpy as np

# --- Set Streamlit Theme (Orange-White) ---
st.set_page_config(
    page_title="EV Benchmarking App",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    /* Main background color */
    .stApp { background-color: #FFFFFF; } /* White */
    /* Sidebar background color */
    .st-emotion-cache-1ldk86k { background-color: #FFF0E0; } /* Light Peach */
    .st-emotion-cache-1ldk86k .st-emotion-cache-vk3370 { background-color: #FFDAB9; } /* Peach Puff for sidebar header */

    /* Primary button color (orange) */
    .stButton>button { background-color: #FFA500; color: white; border: none; }
    .stButton>button:hover { background-color: #FF8C00; color: white; }

    /* Text color */
    body { color: #333333; } /* Dark Grey */
    h1, h2, h3, h4, h5, h6 { color: #FF7F50; } /* Coral */

    /* Expander background */
    .streamlit-expanderHeader { background-color: #FFEFD5; } /* PapayaWhip */
    .streamlit-expanderContent { background-color: #FFFFFF; } /* White */

    /* Custom CSS for similarity badges */
    .similarity-badge {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        width: 42px; /* Adjust size as needed */
        height: 42px;
        border-radius: 50%;
        color: white;
        font-weight: bold;
        font-size: 0.85em;
        background-color: grey; /* Default */
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .similarity-badge-green { background-color: #28a745; } /* Green */
    .similarity-badge-darkyellow { background-color: #ffc107; color: black; } /* Dark Yellow */
    .similarity-badge-lightyellow { background-color: #fff3cd; color: black; } /* Light Yellow */

    /* Custom CSS for smaller table font */
    .small-table{
        font-size:14px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# --- Add Thanachart Insurance Logo to the top right of the title ---
col1, col2 = st.columns([0.8, 0.2]) # Adjust ratios as needed
with col1:
    st.title("EV benchmark for Thanachart insurance")
with col2:
    try:
        st.image('thanachart_logo.jpg', width=150)
    except FileNotFoundError:
        st.warning("Thanachart Insurance logo (thanachart_logo.jpg) not found. Please upload the image file.")

st.write("ค้นหารถยนต์ไฟฟ้าที่คล้ายคลึงกันตามคุณสมบัติที่คุณเลือก")

# --- Session State Initializations ---
# Page navigation
if "page" not in st.session_state:
    st.session_state["page"] = "result"

if "results" not in st.session_state:
    st.session_state["results"] = None

if "selected_car_index" not in st.session_state:
    st.session_state["selected_car_index"] = None

if "input" not in st.session_state:
    st.session_state["input"] = None

# Store EV input values
default_values = {
    "input_body_type": "",

    # Market
    "input_sales_price": 2000000,

    # Vehicle dimension
    "input_length": 5000,
    "input_width": 1900,
    "input_height": 1400,
    "input_wheelbase": 2900,

    # Vehicle characteristic
    "input_ground_clearance": 172,
    "input_battery_capacity": 75.0,

    "input_battery_manufacturer": "",

    "input_motor_power": 220,
    "input_motor_torque": 420,

    "input_driving_range": 500,
    "input_vehicle_weight" :2100,

    "input_battery_material": "",
    "range_type_choice": "Rang(WLTP)"
}


for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- โหลดข้อมูล (ควรอยู่ในไฟล์ Streamlit โดยตรงเมื่อใช้งานจริง) ---
try:
    df = pd.read_excel('database.xlsx')
    df.columns = df.columns.str.strip()

    # Create Combined_Range column: Prioritize WLTP, then NEDC
    df['Combined_Range'] = df.apply(lambda row: row['Rang(WLTP)'] if pd.notna(row.get('Rang(WLTP)')) else row.get('Rang(NEDC)'), axis=1)
    df['Combined_Range'] = pd.to_numeric(df['Combined_Range'], errors='coerce').fillna(0)

    # Strip whitespace from categorical columns
    for col in ['body_type', 'Battery Manufacturer', 'Battery Material']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
except FileNotFoundError:
    st.error("Error: 'database.xlsx' not found. Please make sure the file is in the same directory as app.py.")
    st.stop()
except Exception as e:
    st.error(f"An error occurred while loading data: {e}")
    st.stop()

# เตรียมข้อมูล: กำจัดแถวที่มีค่าว่างในคอลัมน์สำคัญที่อาจส่งผลต่อการดึงตัวเลือก
df_cleaned_for_options = df.dropna(subset=['body_type', 'Battery Manufacturer', 'Battery Material'])

# *** สำคัญ: แก้ชื่อคอลัมน์ตรงนี้ให้ตรงกับไฟล์ Excel จริงของคุณ ***
FEATURE_WEIGHTS = {
    "Vehicle Sales Price (in THB)": 0.163,
    "Battery Capacity(kWh)": 0.163,
    "Electric Motor (Motor power) (kW)": 0.163,
    "Combined_Range": 0.109, # Using Combined_Range for consistency
    # "Accel_0-100(s)": 0.08, # Removed as this column is not present in the DataFrame
    "Motor Torque": 0.076,
    "Vehicle weight": 0.076,
    "ความยาว(mm)": 0.054,
    "ความกว้าง(mm)": 0.054,
    "ความสูง(mm)": 0.054,
    "ระยะฐานล้อ(mm)": 0.054,
    "Ground Clearance": 0.033
}

CATEGORICAL_FEATURES = {
    "body_type": 0.3,
    "Battery Manufacturer": 0.4,
    "Battery Material": 0.3
}

def normalize_features(df_input, features):
    df_norm = df_input.copy()
    for col in features:
        # Convert column to numeric, coercing errors to NaN, then fill NaN with 0
        df_norm[col] = pd.to_numeric(df_norm[col], errors='coerce').fillna(0)
        min_val, max_val = df_norm[col].min(), df_norm[col].max()
        if max_val - min_val == 0:
            df_norm[col] = 0.5
        else:
            df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
    return df_norm

def calculate_similarity(input_specs, database_df,
                         numerical_weights=FEATURE_WEIGHTS,
                         categorical_weights=CATEGORICAL_FEATURES,
                         w_market_segment=0.33,
                         w_vehicle_char=0.33,
                         w_pricing_cost=0.34,
                         alpha_num_cat=0.7,
                         top_n=5,
                         debug=False):

    # Define features for each category using the global weights
    market_segment_num_feats = {f: numerical_weights[f] for f in ['Vehicle Sales Price (in THB)'] if f in numerical_weights}
    market_segment_cat_feats = {f: categorical_weights[f] for f in ['body_type'] if f in categorical_weights}

    # Updated to use 'Combined_Range' for processing
    vehicle_char_num_feats = {f: numerical_weights[f] for f in ['ความกว้าง(mm)', 'ความยาว(mm)', 'ความสูง(mm)', 'ระยะฐานล้อ(mm)', 'Battery Capacity(kWh)', 'Electric Motor (Motor power) (kW)', 'Motor Torque', 'Combined_Range', 'Vehicle weight', 'Ground Clearance'] if f in numerical_weights}
    vehicle_char_cat_feats = {f: categorical_weights[f] for f in ['Battery Manufacturer', 'Battery Material'] if f in categorical_weights}

    pricing_cost_num_feats = {f: numerical_weights[f] for f in ['Vehicle Sales Price (in THB)'] if f in numerical_weights}
    # No explicit categorical features for pricing_cost based on the user's breakdown
    pricing_cost_cat_feats = {}

    # --- Helper function to calculate sub-similarity for a given set of features ----
    def _calculate_sub_similarity(sub_numerical_weights, sub_categorical_weights):
        sub_numerical_features = list(sub_numerical_weights.keys())
        sub_categorical_features = list(sub_categorical_weights.keys())

        # Numerical part
        sub_numerical_scores = [0] * len(database_df) # Default to 0 if no numerical features or input issues
        if sub_numerical_features:
            combined_numerical_subset = database_df.copy()
            for col in sub_numerical_features:
                # Only include columns actually present in the database_df for normalization
                if col not in combined_numerical_subset.columns:
                    # st.warning(f"DEBUG: Column '{col}' not found for numerical subset. Skipping.")
                    continue # Skip if column not in database_df
                combined_numerical_subset[col] = pd.to_numeric(combined_numerical_subset[col], errors='coerce').fillna(0)

            input_row_numerical_subset = {k: v for k, v in input_specs.items() if k in sub_numerical_features}
            if input_row_numerical_subset:
                # Ensure all numerical features for this sub-category are in the input row, fill with 0 if missing
                for f in sub_numerical_features:
                    if f not in input_row_numerical_subset:
                        input_row_numerical_subset[f] = 0.0 # Use 0.0 for numerical consistency

                # Add temporary ID for input row before concatenating
                input_row_for_concat = input_row_numerical_subset.copy()
                input_row_for_concat['__TEMP_ID__'] = '__INPUT__'

                combined_numerical_subset_with_input = pd.concat([combined_numerical_subset, pd.DataFrame([input_row_for_concat])], ignore_index=True)
                combined_norm_subset = normalize_features(combined_numerical_subset_with_input, sub_numerical_features)

                input_norm_subset = combined_norm_subset[combined_norm_subset["__TEMP_ID__"] == "__INPUT__"].iloc[0]
                db_norm_subset = combined_norm_subset[combined_norm_subset["__TEMP_ID__"] != "__INPUT__"].reset_index(drop=True)

                sub_numerical_scores = []
                for idx, row in db_norm_subset.iterrows():

                    if debug and idx < 10:
                        st.write("========== DEBUG ==========")
                        # Corrected debug output to avoid KeyError when indexing Series with a list
                        st.write(
                            pd.Series({
                                "Brand": database_df.iloc[idx]["Brand"],
                                "model_name": database_df.iloc[idx]["model_name"],
                                "variant_name": database_df.iloc[idx]["variant_name"]
                            })
                        )
                        diff = (
                            row[sub_numerical_features]
                            -
                            input_norm_subset[sub_numerical_features]
                        )
                        st.write("Feature Difference")
                        st.dataframe(
                            diff.to_frame("difference")
                        )

                    # Refactored dist_sq calculation for readability
                    dist_sq = 0
                    if sub_numerical_features:
                        for f in sub_numerical_features:
                            if f in row.index and f in input_norm_subset.index and f in sub_numerical_weights:
                                dist_sq += sub_numerical_weights[f] * (row[f] - input_norm_subset[f]) ** 2

                    distance = np.sqrt(dist_sq)
                   # ป้องกัน floating point error
                    if distance < 1e-10:
                        similarity_pct = 100.0
                    else:
                        similarity_pct = max(0, (1 - distance)) * 100
                    sub_numerical_scores.append(similarity_pct)
            else:
                 sub_numerical_scores = [0] * len(database_df)

        # Categorical part
        sub_categorical_scores = [0] * len(database_df) # Default to 0
        total_sub_cat_weight = sum(sub_categorical_weights.values())

        if total_sub_cat_weight > 0:
            sub_categorical_scores = []
            for idx, db_row in database_df.iterrows():
                cat_sim_sum = 0
                for cat_feat, weight in sub_categorical_weights.items():
                    if cat_feat in input_specs and cat_feat in db_row:
                        # Ensure consistency by stripping spaces from both input and database values
                        if str(input_specs[cat_feat]).strip().lower() == str(db_row[cat_feat]).strip().lower():
                            cat_sim_sum += weight
                sub_categorical_scores.append((cat_sim_sum / total_sub_cat_weight) * 100)

        # Combine numerical and categorical for this sub-category
        combined_sub_scores = []
        for i in range(len(database_df)):
            score = (alpha_num_cat * sub_numerical_scores[i]) + ((1 - alpha_num_cat) * sub_categorical_scores[i])
            combined_sub_scores.append(score)
        return combined_sub_scores

    # --- Calculate scores for each main category ---
    market_segment_scores = _calculate_sub_similarity(market_segment_num_feats, market_segment_cat_feats)
    vehicle_char_scores = _calculate_sub_similarity(vehicle_char_num_feats, vehicle_char_cat_feats)
    pricing_cost_scores = _calculate_sub_similarity(pricing_cost_num_feats, pricing_cost_cat_feats)

    # --- Combine the main category scores ---
    final_combined_scores = []
    for i in range(len(database_df)):
        score = (w_market_segment * market_segment_scores[i]) + \
                (w_vehicle_char * vehicle_char_scores[i]) + \
                (w_pricing_cost * pricing_cost_scores[i])
        final_combined_scores.append(score)

    result = database_df.copy()
    result["Similarity_Score"] = final_combined_scores
    # Add individual scores for detail view
    result["Market_Score"] = market_segment_scores
    result["Vehicle_Score"] = vehicle_char_scores
    result["Pricing_Score"] = pricing_cost_scores

    # ===============================
    # Exact Match Protection
    # ===============================
    for idx, row in result.iterrows():

        exact_match = True

        # ---------- Numerical ----------
        numerical_features_to_check = [
            f for f in numerical_weights.keys()
            if f in input_specs
        ]

        for col in numerical_features_to_check:

            db_value = pd.to_numeric(row[col], errors="coerce")
            input_value = pd.to_numeric(input_specs[col], errors="coerce")

            if pd.isna(db_value) or pd.isna(input_value):
                exact_match = False
                break

            if not np.isclose(db_value, input_value, rtol=1e-5, atol=0.01):
                exact_match = False
                break

        # ---------- Categorical ----------
        if exact_match:

            for col in categorical_weights.keys():

                # ถ้าผู้ใช้ไม่ได้กรอก categorical ตัวนี้
                # จะถือว่าไม่ใช่ exact match
                if col not in input_specs:
                    exact_match = False
                    break

                db_value = str(row[col]).strip().lower()
                input_value = str(input_specs[col]).strip().lower()

                if db_value != input_value:
                    exact_match = False
                    break

        if exact_match:
            result.loc[idx, "Similarity_Score"] = 100.0

    result = result.sort_values("Similarity_Score", ascending=False).reset_index(drop=True)
    result["Similarity_Score"] = result["Similarity_Score"].round(1)
    return result.head(top_n)

# Helper function to generate HTML for similarity badge
def get_similarity_badge_html(score):
    if score >= 80:
        color_class = "similarity-badge-green"
    elif 50 <= score < 80:
        color_class = "similarity-badge-darkyellow"
    else:
        color_class = "similarity-badge-lightyellow"
    return f'<div class="similarity-badge {color_class}">{score:.1f}%</div>'

# Helper function for styling difference in detail view
def highlight_diff(val):
    if pd.isna(val):
        return ''
    if abs(val) < 5:
        return "background-color:#d4edda" # Greenish
    elif abs(val) < 20:
        return "background-color:#fff3cd" # Yellowish
    else:
        return "background-color:#f8d7da" # Reddish

def restore_new_ev_input():
    if st.session_state["input"] is None:
        return

    input_data = st.session_state["input"]

    mapping = {
        "ความยาว(mm)": "input_length",
        "ความกว้าง(mm)": "input_width",
        "ความสูง(mm)": "input_height",
        "ระยะฐานล้อ(mm)": "input_wheelbase",
        "Ground Clearance": "input_ground_clearance",
        "Battery Capacity(kWh)": "input_battery_capacity",
        "Electric Motor (Motor power) (kW)": "input_motor_power",
        "Motor Torque": "input_motor_torque",
        "Vehicle Sales Price (in THB)": "input_sales_price",
        "Vehicle weight": "input_vehicle_weight",
        "Combined_Range": "input_driving_range",
    }

    for feature, key in mapping.items():
        if feature in input_data:
            st.session_state[key] = input_data[feature]


    # categorical
    if "body_type" in input_data:
        st.session_state["input_body_type"] = input_data["body_type"]

    if "Battery Manufacturer" in input_data:
        st.session_state["input_battery_manufacturer"] = input_data["Battery Manufacturer"]

    if "Battery Material" in input_data:
        st.session_state["input_battery_material"] = input_data["Battery Material"]

# Function to display detail page
def show_detail():
    if st.session_state["results"] is None:
        st.warning("ไม่มีข้อมูลผลการค้นหา")
        return

    if st.session_state["selected_car_index"] is None:
        st.warning("ยังไม่ได้เลือกรถ")
        return

    results = st.session_state["results"]
    input_data = st.session_state["input"]
    selected_index = st.session_state["selected_car_index"]

    results = results.reset_index(drop=True)

    if selected_index >= len(results):
        st.error("ไม่พบข้อมูลรถ")
        return

    car = results.iloc[selected_index]

    if st.button("⬅ กลับ Top 5"):
        restore_new_ev_input()
        st.session_state["page"] = "result"
        st.session_state["selected_car_index"] = None
        st.rerun()

    st.title(
        f"{car['Brand']} {car['model_name']} ({car['variant_name']})"
    )

    st.metric(
        "Similarity Score",
        f"{car['Similarity_Score']}%"
    )

    st.subheader(
        "Score Breakdown"
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Market",
        f"{car['Market_Score']:.1f}%"
    )

    c2.metric(
        "Vehicle",
        f"{car['Vehicle_Score']:.1f}%"
    )

    c3.metric(
        "Pricing",
        f"{car['Pricing_Score']:.1f}%"
    )

    st.subheader(
        "Factor Difference"
    )

    compare_features = list(
        FEATURE_WEIGHTS.keys()
    )

    detail = []

    for feature in compare_features:
        if feature in input_data and feature in car:
            input_value = input_data[feature]
            db_value = car[feature]

            # Convert to numeric for comparison, handling potential errors
            input_value_numeric = pd.to_numeric(input_value, errors='coerce')
            db_value_numeric = pd.to_numeric(db_value, errors='coerce')

            if pd.isna(db_value_numeric) or pd.isna(input_value_numeric):
                continue # Skip if either value is NaN after conversion

            diff = db_value_numeric - input_value_numeric

            detail.append(
                {
                    "Feature": feature,
                    "Input": input_value,
                    "Database": db_value,
                    "Difference": diff
                }
            )

    detail_df = pd.DataFrame(detail)

    if not detail_df.empty:
        st.dataframe(
            detail_df.style.map(highlight_diff, subset=['Difference']),
            use_container_width=True
        )
    else:
        st.info("No numerical features available for detailed comparison.")

    st.subheader("Categorical Factor Comparison")
    categorical_detail = []
    for feature in CATEGORICAL_FEATURES.keys():
        input_value = input_data.get(feature, "N/A")
        db_value = car.get(feature, "N/A")

        categorical_detail.append(
            {
                "Feature": feature,
                "Input Value": str(input_value).strip(),
                "Database Value": str(db_value).strip()
            }
        )
    categorical_df = pd.DataFrame(categorical_detail)
    if not categorical_df.empty:
        st.dataframe(categorical_df, use_container_width=True)
    else:
        st.info("No categorical features available for detailed comparison.")


# --- Streamlit UI for Input ---
# Conditional rendering based on session state page
if st.session_state["page"] == "result":
    st.sidebar.header("คุณสมบัติรถยนต์ EV ที่ต้องการ")

    with st.sidebar.expander("1. Market Segment", expanded=True):
        body_type_options = [''] + sorted(df_cleaned_for_options['body_type'].astype(str).unique().tolist())
        input_body_type = st.selectbox(
            "ประเภทตัวถัง (body_type)",
            body_type_options,
            key="input_body_type"
        )
        input_sales_price = st.number_input(
            "ราคาขายรถยนต์ (Vehicle Sales Price (in THB))",
            min_value=0,
            step=10000,
            key="input_sales_price"
        )

    with st.sidebar.expander("2. Vehicle Characteristics", expanded=True):
        input_length = st.number_input(
            "ความยาว(mm)",
            min_value=0,
            step=10,
            key="input_length"
        )
        input_width = st.number_input(
            "ความกว้าง(mm)",
            min_value=0,
            step=10,
            key="input_width"
        )
        input_height = st.number_input(
            "ความสูง(mm)",
            min_value=0,
            step=10,
            key="input_height"
        )
        input_wheelbase = st.number_input(
            "ระยะฐานล้อ(mm)",
            min_value=0,
            step=10,
            key="input_wheelbase"
        )
        input_ground_clearance = st.number_input(
            "Ground Clearance",
            min_value=0,
            step=5,
            key="input_ground_clearance"
        )
        input_battery_capacity = st.number_input(
            "Battery Capacity(kWh)",
            min_value=0.0,
            step=0.1,
            key="input_battery_capacity"
        )

        battery_manuf_options = [''] + sorted(df_cleaned_for_options['Battery Manufacturer'].astype(str).unique().tolist())
        input_battery_manufacturer = st.selectbox(
            "ผู้ผลิตแบตเตอรี่ (Battery Manufacturer)",
            battery_manuf_options,
            key="input_battery_manufacturer"
        )

        input_motor_power = st.number_input(
            "กำลังมอเตอร์ (Electric Motor (Motor power) (kW))",
            min_value=0,
            step=10,
            key="input_motor_power"
        )
        input_motor_torque = st.number_input(
            "แรงบิดมอเตอร์ (Motor Torque)",
            min_value=0,
            step=10,
            key="input_motor_torque"
        )

        # New UI for selecting Range Type and inputting Range Value
        # The radio button specifies which type of range the user is entering, but the value is stored as 'Combined_Range'
        range_type_choice = st.radio(
            "เลือกประเภทระยะการขับขี่ (ค่าที่กรอกจะถูกใช้เป็น Combined_Range)",
            ['Rang(WLTP)', 'Rang(NEDC)'],
            key="range_type_choice"
        )
        input_driving_range = st.number_input(
            f"ระยะการขับขี่ ({st.session_state['range_type_choice']})",
            min_value=0,
            step=10,
            key="input_driving_range"
        )

        input_vehicle_weight = st.number_input(
            "น้ำหนักรถยนต์ (Vehicle weight)",
            min_value=0,
            step=10,
            key="input_vehicle_weight"
        )

        # Apply .str.strip() here to clean Battery Material options
        battery_material_options = [''] + sorted(df_cleaned_for_options['Battery Material'].astype(str).str.strip().unique().tolist())
        input_battery_material = st.selectbox(
            "วัสดุแบตเตอรี่ (Battery Material)",
            battery_material_options,
            key="input_battery_material"
        )

    # Create a dictionary for the new EV from user inputs
    new_ev_input = {
        "ความยาว(mm)": st.session_state["input_length"],
        "ความกว้าง(mm)": st.session_state["input_width"],
        "ความสูง(mm)": st.session_state["input_height"],
        "ระยะฐานล้อ(mm)": st.session_state["input_wheelbase"],
        "Ground Clearance": st.session_state["input_ground_clearance"],
        "Battery Capacity(kWh)": st.session_state["input_battery_capacity"],
        "Electric Motor (Motor power) (kW)": st.session_state["input_motor_power"],
        "Motor Torque": st.session_state["input_motor_torque"],
        "Vehicle Sales Price (in THB)": st.session_state["input_sales_price"],
        "Vehicle weight": st.session_state["input_vehicle_weight"],
        "Combined_Range": st.session_state["input_driving_range"], # Always assign to Combined_Range
    }

    # Add categorical features if selected
    if st.session_state["input_body_type"]: new_ev_input["body_type"] = st.session_state["input_body_type"]
    if st.session_state["input_battery_manufacturer"]: new_ev_input["Battery Manufacturer"] = st.session_state["input_battery_manufacturer"]
    # Ensure the input battery material is also stripped of spaces for matching
    if st.session_state["input_battery_material"]: new_ev_input["Battery Material"] = st.session_state["input_battery_material"].strip()

    if st.sidebar.button("ค้นหารถยนต์ที่คล้ายกัน", key="search_button"):

        results_df = calculate_similarity(
            new_ev_input,
            df,
            top_n=5,
            debug=False
        )

        results_df['Rank'] = range(1, len(results_df)+1)

        results_df['Similarity_Score_HTML'] = (
            results_df['Similarity_Score']
            .apply(get_similarity_badge_html)
        )

        st.session_state["results"] = results_df
        st.session_state["input"] = new_ev_input
        st.session_state["page"] = "result"
        st.session_state["selected_car_index"] = None

    if st.sidebar.button("รีเซ็ตข้อมูลรถใหม่"):
        # Delete input field keys from session state to force re-initialization
        for key in default_values.keys():
            if key in st.session_state:
                del st.session_state[key]
        # Explicitly set range_type_choice to its default as it's a radio button
        st.session_state["range_type_choice"] = "Rang(WLTP)"
        # Clear results and navigation state
        st.session_state["results"] = None
        st.session_state["input"] = None
        st.session_state["page"] = "result"
        st.session_state["selected_car_index"] = None
        st.rerun()

    if st.session_state["results"] is not None:
        results_df = st.session_state["results"]
        # Header
        header_cols = st.columns([0.5, 1, 1.6, 1.6, 0.8, 0.4])

        with header_cols[0]:
            st.markdown("**Rank**")
        with header_cols[1]:
            st.markdown("**Brand**")
        with header_cols[2]:
            st.markdown("**Model**")
        with header_cols[3]:
            st.markdown("**Variant**")
        with header_cols[4]:
            st.markdown("**Similarity**")
        with header_cols[5]:
            st.markdown("**Detail**")

        st.markdown(
            "<hr style='margin:2px 0;'>",
            unsafe_allow_html=True
        )

        for idx, row in results_df.iterrows():

            cols = st.columns([0.5, 1, 1.6, 1.6, 0.8, 0.4])

            with cols[0]:
                st.markdown(f"<div class='small-table'>{row['Rank']}</div>", unsafe_allow_html=True)

            with cols[1]:
                st.markdown(f"<div class='small-table'>{row['Brand']}</div>", unsafe_allow_html=True)

            with cols[2]:
                st.markdown(f"<div class='small-table'>{row['model_name']}</div>", unsafe_allow_html=True)

            with cols[3]:
                st.markdown(f"<div class='small-table'>{row['variant_name']}</div>", unsafe_allow_html=True)

            with cols[4]:
                st.markdown(
                    row["Similarity_Score_HTML"],
                    unsafe_allow_html=True
                )

            with cols[5]:
                if st.button("🔍", key=f"detail_button_{idx}"):
                    st.session_state["selected_car_index"] = idx
                    st.session_state["page"] = "detail"
                    st.rerun()

            st.markdown(
                "<hr style='margin:2px 0;'>",
                unsafe_allow_html=True
            )

elif st.session_state["page"] == "detail":
    show_detail()
