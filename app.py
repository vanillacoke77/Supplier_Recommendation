import streamlit as st
import pandas as pd
from datetime import datetime
from supplier_backend import recommend_suppliers  # Import from converted .py file

# Set page config
st.set_page_config(
    page_title="Supplier Recommendation System",
    page_icon="🛒",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
        .supplier-card {
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            background-color: #f8f9fa;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .supplier-score {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .factor-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            margin: 2px;
        }
        .positive { background-color: #e8f5e9; color: #2e7d32; }
        .negative { background-color: #ffebee; color: #c62828; }
        .neutral { background-color: #e3f2fd; color: #1565c0; }
        .stProgress > div > div > div > div {
            background-color: #4CAF50;
        }
    </style>
""", unsafe_allow_html=True)

# Main form
def main():
    st.title("🛒 Supplier Recommendation System")
    st.markdown("Find the best suppliers based on multiple risk factors")

    with st.form("supplier_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            product_category = st.selectbox(
                "Product Category",
                ["GPS", "Medical", "Government", "Electronics", "Other"],
                index=0
            )
            product_name = st.text_input("Product Name", placeholder="GPS Device X200")
        
        with col2:
            location_option = st.radio(
                "Location Input",
                ["Enter manually", "Auto-detect (US only)"],
                index=0
            )
            
            if location_option == "Enter manually":
                city = st.text_input("City", value="New York")
                country = st.text_input("Country", value="United States")
                source_location = f"{city}, {country}"
            else:
                source_location = "New York, United States"  # Default for demo
        
        submitted = st.form_submit_button("Find Suppliers")

    if submitted:
        if not product_name:
            st.error("Please enter a product name")
            return
        
        with st.spinner("Analyzing suppliers..."):
            try:
                result = recommend_suppliers(
                    product_category=product_category,
                    product_name=product_name,
                    source_location=source_location
                )
                
                display_results(result)
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.stop()

def display_results(result):
    top_suppliers = result.get("top_suppliers", [])
    explanation = result.get("explanation", "No explanation provided")
    
    st.success(f"Found {len(top_suppliers)} recommended suppliers")
    
    # Display suppliers
    for i, supplier in enumerate(top_suppliers, 1):
        with st.expander(f"{i}. {supplier['supplier_name']} (Score: {supplier['score']:.1f})", expanded=i==1):
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.metric("Overall Score", f"{supplier['score']:.1f}/100")
                st.caption(f"Domain: {supplier.get('domain', 'N/A')}")
                st.caption(f"Location: {supplier.get('city', 'N/A')}, {supplier.get('country', 'N/A')}")
                st.caption(f"Complaints: {supplier.get('complaint_count', 0)}")
            
            with col2:
                factors = supplier.get('factors', {})
                cols = st.columns(6)
                with cols[0]: st.metric("Weather", factors.get('weather_factor', 0), help="Weather risk factor")
                with cols[1]: st.metric("Tariffs", factors.get('tariff_factor', 0), help="Tariff impact")
                with cols[2]: st.metric("Match", factors.get('product_match_factor', 0), help="Product match")
                with cols[3]: st.metric("Complaints", factors.get('complaint_factor', 0), help="Complaint history")
                with cols[4]: st.metric("Distance", factors.get('distance_factor', 0), help="Proximity score")
                with cols[5]: st.metric("Expiration", factors.get('expiration_factor', 0), help="Product freshness")
    
    # Explanation
    st.markdown("### Recommendation Analysis")
    st.markdown(explanation)
    
    # Download button
    csv = pd.DataFrame(top_suppliers).to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Results (CSV)",
        data=csv,
        file_name=f"suppliers_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()