import pandas as pd
import os
import requests
from datetime import datetime
from huggingface_hub import InferenceClient
# Initialize Hugging Face client
client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.3",
    token="placeholder"
)
# Define paths
base_path = "dataforrag"
# Load all CSV files
def load_all_csvs(base_path):
    csv_data = {}
    # Define file mappings
    directories = {
        "goverment": ["SGE_projects.csv", "SGE_products.csv", "SGE_suppliers.csv"],
        "medical": ["medical_products.csv", "medical_suppliers.csv", "medical_projects.csv"],
        "gps": ["GPS_products.csv", "GPS_suppliers.csv", "GPS_projects.csv"]
    }
    # Root-level files
    root_files = ["complaints-2025-03-26_03_39.csv"]
    # Try different encodings
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    # Load directory files
    for directory, files in directories.items():
        dir_path = os.path.join(base_path, directory)
        if os.path.exists(dir_path):
            for file in files:
                file_path = os.path.join(dir_path, file)
                if os.path.exists(file_path):
                    key = f"{directory.replace('goverment', 'sge')}_{file.split('_')[1].split('.')[0].lower()}"
                    for encoding in encodings:
                        try:
                            csv_data[key] = pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip')
                            print(f"Loaded {key}")
                            break
                        except Exception:
                            continue
    # Load root files
    for file in root_files:
        file_path = os.path.join(base_path, file)
        if os.path.exists(file_path):
            key = "complaints"
            for encoding in encodings:
                try:
                    csv_data[key] = pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip')
                    print(f"Loaded {key}")
                    break
                except Exception:
                    continue
    return csv_data
# Weather API function
def get_weather_forecast(city, api_key="placeholder"):
    if not isinstance(city, str) or not city.strip():
        return None
    city = city.strip()
    try:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={city}&days=14&aqi=no&alerts=no"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # print("got weather data")
            # Extract basic location info
            location = data.get("location", {})
            city_name = location.get("name")
            country = location.get("country")
            # Process and analyze forecast
            forecast_days = []
            has_extreme_weather = False
            extreme_weather_count = 0
            for forecast in data.get("forecast", {}).get("forecastday", []):
                day = forecast.get("date")
                day_data = forecast.get("day", {})
                # Extract key metrics
                max_temp = day_data.get("maxtemp_c")
                min_temp = day_data.get("mintemp_c")
                avg_temp = day_data.get("avgtemp_c")
                total_precip = day_data.get("totalprecip_mm")
                max_wind = day_data.get("maxwind_kph")
                condition = day_data.get("condition", {}).get("text")
                # Check for extreme weather
                extreme_weather = False
                extreme_type = None
                if avg_temp > 35:
                    extreme_weather = True
                    extreme_type = "extreme heat"
                elif avg_temp < 0:
                    extreme_weather = True
                    extreme_type = "extreme cold"
                elif total_precip > 20:
                    extreme_weather = True
                    extreme_type = "heavy rain"
                elif max_wind > 40:
                    extreme_weather = True
                    extreme_type = "strong winds"
                elif any(word in condition.lower() for word in ["storm", "hurricane", "flood", "cyclone", "tornado"]):
                    extreme_weather = True
                    extreme_type = "severe storm"
                if extreme_weather:
                    has_extreme_weather = True
                    extreme_weather_count += 1
                forecast_days.append({
                    "day": day,
                    "avg_temp": avg_temp,
                    "total_precip": total_precip,
                    "max_wind": max_wind,
                    "condition": condition,
                    "extreme_weather": extreme_weather,
                    "extreme_type": extreme_type
                })
                # print(forecast_days)
            return {
                "city": city_name,
                "country": country,
                "forecast": forecast_days,
                "has_extreme_weather": has_extreme_weather,
                "extreme_weather_days": extreme_weather_count
            }
        elif response.status_code == 400 and city == "Tehuacain":
            return get_weather_forecast("Tehuacán", api_key)
        else:
            return None
    except Exception as e:
        print(f"Weather API error for {city}: {str(e)}")
        return None
# WTO country codes and HS product codes
wto_country_codes = {
    "United States": "C840",
    "China": "C156",
    "India": "C356",
    "Germany": "C276",
    "United Kingdom": "C826"
}
def get_hs_code_for_product(product_name, product_category):
    """Determine HS code for a product using LLM with improved fallback"""
    # Define default HS codes mapping with more comprehensive categories
    default_hs_codes = {
        "GPS": "8526",  # Radar, radio navigation, and remote control equipment
        "Navigation": "8526",  # Radar, radio navigation, and remote control equipment
        "Medical": "9018",  # Medical/surgical/dental/veterinary instruments
        "Pharmaceutical": "3004",  # Medicaments
        "Electronics": "8517",  # Telephone and communication equipment
        "Computer": "8471",  # Computing machinery
        "Software": "8523",  # Storage media
        "Automobile": "8703",  # Motor vehicles
        "Machinery": "8479",  # Machinery with individual functions
        "Textile": "6001",  # Textile fabrics
        "Food": "2106",  # Food preparations
        "Chemical": "3824",  # Chemical products
        "Metal": "7326",  # Articles of iron or steel
        "Plastic": "3926",  # Articles of plastics
        "Wood": "4421",  # Articles of wood
        "Furniture": "9403",  # Other furniture
        "Lighting": "9405",  # Lamps and lighting fittings
        "Tool": "8207",  # Interchangeable tools
        "Toy": "9503",  # Toys and models
        "Sports": "9506"   # Sports equipment
    }
    # Try to get HS code from LLM
    prompt = f"""
    As a trade expert, provide the most appropriate HS (Harmonized System) code
    for the following product:
    Product Name: {product_name}
    Product Category: {product_category}
    Return only the 4-digit HS code without any explanation.
    """
    try:
        response = client.text_generation(
            prompt,
            max_new_tokens=20,
            temperature=0.1
        )
        # Extract just the numeric code
        import re
        hs_code_match = re.search(r'\d{4}', response)
        if hs_code_match:
            hs_code = hs_code_match.group(0)
            print(f"LLM determined HS code for {product_name}: {hs_code}")
            return hs_code
    except Exception as e:
        print(f"Error getting HS code from LLM: {str(e)}")
    # If LLM fails, try to match category or product name with default codes
    print(f"LLM failed to provide HS code, using fallback for {product_category}")
    # Check for direct category match
    if product_category in default_hs_codes:
        return default_hs_codes[product_category]
    # Check for partial category match
    for category, code in default_hs_codes.items():
        if category.lower() in product_category.lower() or product_category.lower() in category.lower():
            print(f"Partial category match: {category} -> {code}")
            return code
        # Also check product name for keywords
        if category.lower() in product_name.lower():
            print(f"Product name match: {category} -> {code}")
            return code
    # Default fallback based on product category with best guess
    if "gps" in product_category.lower() or "navigation" in product_name.lower():
        return "8526"
    elif "medical" in product_category.lower() or "health" in product_name.lower():
        return "9018"
    elif "electronic" in product_category.lower() or "device" in product_name.lower():
        return "8517"
    else:
        print(f"No match found, using default code 8526 for {product_name}")
        return "8526"  # Default to GPS equipment as final fallback
# Tariff API function
def get_tariff_data(country_code, product_id, api_key="placeholder"):
    url = f"https://api.wto.org/qrs/qrs?reporter_member_code={country_code}&in_force_only=true&product_ids={product_id}"
    headers = {
        "Cache-Control": "no-cache",
        "Ocp-Apim-Subscription-Key": api_key
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # print("got tarifff data", response.json())
            return response.json()
    except Exception as e:
        print(f"Tariff API error: {str(e)}")
    return None
# Extract supplier data
def extract_supplier_features(csv_data):
    all_suppliers = []
    # Map of dataset keys to domains
    domain_map = {
        "gps_suppliers": "GPS",
        "medical_suppliers": "Medical",
        "sge_suppliers": "Government"
    }
    # Extract suppliers from each domain
    for key, domain in domain_map.items():
        if key in csv_data:
            suppliers_df = csv_data[key].copy()
            suppliers_df["domain"] = domain
            all_suppliers.append(suppliers_df)
    return all_suppliers
# Analyze complaints
def analyze_complaints(csv_data, company_name):
    if "complaints" not in csv_data:
        return {"complaint_count": 0, "complaint_severity": 0}
    complaints_df = csv_data["complaints"]
    company_complaints = complaints_df[complaints_df["Company"] == company_name]
    if company_complaints.empty:
        return {"complaint_count": 0, "complaint_severity": 0}
    # Count complaints
    complaint_count = len(company_complaints)
    # Define severity scores by issue type
    severity_mapping = {
        "Managing an account": 3,
        "Closing an account": 4,
        "Deposits and withdrawals": 5,
        "Problem with a purchase": 7,
        "Billing dispute": 6,
        "Product not received": 8,
        "Defective product": 9
    }
    # Calculate average severity
    severity_scores = [severity_mapping.get(issue, 5) for issue in company_complaints["Issue"]]
    avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0
    return {
        "complaint_count": complaint_count,
        "complaint_severity": avg_severity
    }
# Calculate supplier scores
def calculate_supplier_scores(supplier_list, csv_data, product_category, product_name, source_location):
    scores = []
    # Get HS code dynamically
    product_hs = get_hs_code_for_product(product_name, product_category)
    for suppliers_df in supplier_list:
        for _, supplier in suppliers_df.iterrows():
            supplier_id = supplier.get("ID")
            supplier_name = supplier.get("Name", "Unknown")
            domain = supplier.get("domain", "Unknown")
            # Base score and factors - reduce the base score to allow for more differentiation
            base_score = 50
            factors = {
                "complaint_factor": 0,
                "weather_factor": 0,
                "tariff_factor": 0,
                "product_match_factor": 0,
                "expiration_factor": 0,
                "distance_factor": 0  # New factor for distance
            }
            # Factor 1: Complaints (keep as is)
            complaint_info = analyze_complaints(csv_data, supplier_name)
            complaint_count = complaint_info["complaint_count"]
            complaint_severity = complaint_info["complaint_severity"]
            if complaint_count == 0:
                factors["complaint_factor"] = 10
            else:
                factors["complaint_factor"] = -min(20, (complaint_count * complaint_severity / 10))
            # Factor 2: Weather risks (improved)
            supplier_city = supplier.get("City") or supplier.get("city")
            supplier_country = supplier.get("Country") or supplier.get("country") or supplier.get("State") or supplier.get("state")
            # Handle missing location data
            if pd.isna(supplier_city):
                supplier_city = None
            if pd.isna(supplier_country):
                supplier_country = "United States"  # Default assumption
            supplier_location = None
            if supplier_city and isinstance(supplier_city, str) and len(supplier_city.strip()) > 0:
                # Check if city field looks valid (not containing company terms)
                company_terms = ["llc", "inc", "incorporated", "company", "corp", "corporation"]
                if not any(keyword in supplier_city.lower() for keyword in company_terms):
                    supplier_location = f"{supplier_city}, {supplier_country}" if supplier_country else supplier_city
                    print(f"Checking weather for: {supplier_location}")
                    weather_data = get_weather_forecast(supplier_location)
                    if weather_data and weather_data.get("has_extreme_weather"):
                        extreme_days = weather_data.get("extreme_weather_days", 0)
                        factors["weather_factor"] = -min(15, extreme_days * 3)
                    else:
                        factors["weather_factor"] = 5
                else:
                    factors["weather_factor"] = 0  # Neutral if city appears invalid
            else:
                # Penalize slightly for missing location data
                factors["weather_factor"] = -5
            # Factor 3: Tariffs (keep as is)
            wto_code = wto_country_codes.get(supplier_country, "C840")
            tariff_data = get_tariff_data(wto_code, product_hs)
            if tariff_data:
                high_tariff = any(item.get("duty_rate", 0) > 10 for item in tariff_data.get("items", []))
                factors["tariff_factor"] = -10 if high_tariff else 5
            else:
                factors["tariff_factor"] = 0  # Neutral if no tariff data
            # Factor 4: Product category match (keep as is)
            if domain.lower() == product_category.lower():
                factors["product_match_factor"] = 15
            else:
                # Add slight penalty for domain mismatch
                factors["product_match_factor"] = -5
            # Factor 5: Check for expired products (SGE specific) (keep as is)
            if domain == "Government" and "sge_products" in csv_data:
                sge_products = csv_data["sge_products"]
                supplier_products = sge_products[sge_products["Supplier ID"] == supplier_id]
                if not supplier_products.empty and "Expire Date" in supplier_products.columns:
                    expired_count = 0
                    today = datetime.now()
                    for _, product in supplier_products.iterrows():
                        if pd.notna(product["Expire Date"]):
                            try:
                                expire_date = datetime.strptime(product["Expire Date"], "%Y-%m-%d")
                                if expire_date < today:
                                    expired_count += 1
                            except:
                                pass
                    if expired_count > 0:
                        factors["expiration_factor"] = -min(15, expired_count * 5)
            # Factor 6: Distance from source (new)
            if supplier_location and source_location:
                distance = calculate_distance(source_location, supplier_location)
                # Scale: 0-5000km: 10 points, 5000-10000km: 5 points, >10000km: 0 points
                if distance is not None:
                    if distance < 5000:
                        factors["distance_factor"] = 10
                    elif distance < 10000:
                        factors["distance_factor"] = 5
                    else:
                        factors["distance_factor"] = 0
                else:
                    # Penalize if distance calculation failed
                    factors["distance_factor"] = -5
            else:
                # Penalize for missing location data
                factors["distance_factor"] = -5
            # Calculate final score (clamped between 0-100)
            # Add randomness to break ties (0-2 points)
            import random
            randomness = random.uniform(0, 2)
            final_score = base_score + sum(factors.values()) + randomness
            final_score = max(0, min(100, final_score))
            # Add to scores list
            scores.append({
                "supplier_id": supplier_id,
                "supplier_name": supplier_name,
                "domain": domain,
                "score": final_score,
                "factors": factors,
                "city": supplier_city,
                "country": supplier_country,
                "complaint_count": complaint_count,
                "location": supplier_location
            })
    # Sort by score (descending)
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores
def generate_recommendation_explanation(top_suppliers, product_info):
    context = f"""
    Product Category: {product_info['category']}
    Product Name: {product_info['name']}
    Client Location: {product_info['source_location']}
    Top 5 Recommended Suppliers:
    """
    for i, supplier in enumerate(top_suppliers[:5], 1):
        context += f"""
        {i}. {supplier['supplier_name']} (Score: {supplier['score']:.1f})
           - Domain: {supplier['domain']}
           - Location: {supplier.get('city', 'N/A')}, {supplier.get('country', 'N/A')}
           - Complaints: {supplier['complaint_count']}
           - Factors: Weather ({supplier['factors']['weather_factor']}),
                     Tariffs ({supplier['factors']['tariff_factor']}),
                     Product Match ({supplier['factors']['product_match_factor']}),
                     Expiration ({supplier['factors']['expiration_factor']}),
                     Complaints ({supplier['factors']['complaint_factor']}),
                     Distance ({supplier['factors']['distance_factor']})
        """
    prompt = f"""
    You are an expert procurement AI assistant. Based on the following information about recommended suppliers for a product,
    provide a detailed explanation of why these suppliers are recommended, including:
    1. Strengths of each supplier
    2. Any potential risks or concerns
    3. Overall assessment of the top recommendation
    4. Distance considerations from the client location to the supplier
    Make sure to reference specific factors like complaint history, tariffs, weather risks, product matching, and geographical distance.
    {context}
    Provide your explanation in a structured format with clear reasoning for each recommendation.
    """
    response = client.text_generation(
        prompt,
        max_new_tokens=2048,
        temperature=0.7,
        repetition_penalty=1.1,
        top_p=0.9
    )
    return response
def get_user_location():
    """Get the user's location based on IP address"""
    try:
        # Use ipinfo.io to get location information
        response = requests.get("https://ipinfo.io/json")
        if response.status_code == 200:
            data = response.json()
            city = data.get("city")
            country = data.get("country")
            if city and country:
                return f"{city}, {country}"
    except Exception as e:
        print(f"Error getting user location: {str(e)}")
    # If automatic detection fails, prompt the user
    print("Could not automatically detect your location.")
    city = input("Please enter your city: ")
    country = input("Please enter your country: ")
    return f"{city}, {country}"
def calculate_distance(source, destination):
    """Calculate the distance between two locations using the Distance Matrix API"""
    try:
        # Use the Nominatim API to get coordinates
        import requests
        def get_coordinates(location):
            try:
                url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json"
                headers = {"User-Agent": "SupplierRecommendationSystem/1.0"}
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return float(data[0]["lat"]), float(data[0]["lon"])
            except Exception as e:
                print(f"Error getting coordinates for {location}: {str(e)}")
            return None
        # Get coordinates for source and destination
        source_coords = get_coordinates(source)
        dest_coords = get_coordinates(destination)
        if source_coords and dest_coords:
            from math import radians, sin, cos, sqrt, atan2
            # Haversine formula to calculate distance
            R = 6371  # Earth radius in kilometers
            lat1, lon1 = radians(source_coords[0]), radians(source_coords[1])
            lat2, lon2 = radians(dest_coords[0]), radians(dest_coords[1])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            return distance
    except Exception as e:
        print(f"Error calculating distance: {str(e)}")
    return None
def recommend_suppliers(product_category, product_name, source_location=None, csv_data=None):
    if csv_data is None:
        csv_data = load_all_csvs(base_path)
    # If source location is not provided, try to determine it
    if source_location is None:
        source_location = get_user_location()
    print(f"Source location: {source_location}")
    supplier_list = extract_supplier_features(csv_data)
    supplier_scores = calculate_supplier_scores(supplier_list, csv_data, product_category, product_name, source_location)
    top_suppliers = supplier_scores[:5]
    product_info = {
        "category": product_category,
        "name": product_name,
        "source_location": source_location
    }
    explanation = generate_recommendation_explanation(top_suppliers, product_info)
    return {
        "top_suppliers": top_suppliers,
        "explanation": explanation
    }
# Example usage
def main():
    csv_data = load_all_csvs(base_path)
    # Get product info from user
    print("Enter product information:")
    product_category = input("Product Category (e.g., GPS, Medical, Electronics): ")
    product_name = input("Product Name: ")
    # Get or detect source location
    use_auto = input("Automatically detect your location? (y/n): ").lower()
    if use_auto == 'y':
        source_location = get_user_location()
    else:
        city = input("Enter your city: ")
        country = input("Enter your country: ")
        source_location = f"{city}, {country}"
    result = recommend_suppliers(product_category, product_name, source_location, csv_data)
    print("\nTop 5 Recommended Suppliers:")
    for i, supplier in enumerate(result["top_suppliers"], 1):
        print(f"{i}. {supplier['supplier_name']} (Score: {supplier['score']:.1f})")
        print(f"   Location: {supplier.get('city', 'N/A')}, {supplier.get('country', 'N/A')}")
        print(f"   Factors: Weather ({supplier['factors']['weather_factor']}), " +
              f"Tariffs ({supplier['factors']['tariff_factor']}), " +
              f"Product Match ({supplier['factors']['product_match_factor']}), " +
              f"Expiration ({supplier['factors']['expiration_factor']}), " +
              f"Complaints ({supplier['factors']['complaint_factor']}), " +
              f"Distance ({supplier['factors']['distance_factor']})")
    print("\nExplanation:")
    print(result["explanation"])
if __name__ == "__main__":
    main()
