"""
Detect urban growth by comparing NDVI across time periods
"""

import psycopg2
import os
from datetime import datetime

def analyze_urban_growth(city_name):
    """
    Compare urban growth metrics across different time periods
    """
    
    print(f"📊 Analyzing urban growth for: {city_name}")
    
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="postgis"
    )
    
    cur = conn.cursor()
    
    # Get time-series data
    cur.execute("""
        SELECT year, month, urban_percentage, mean_ndvi
        FROM urban_growth_metrics
        WHERE city = %s
        ORDER BY year, month
    """, (city_name,))
    
    results = cur.fetchall()
    
    if len(results) < 2:
        print("⚠️  Need at least 2 time periods for comparison")
        return
    
    print(f"\n🏙️  Urban Growth Analysis for {city_name}")
    print("=" * 60)
    
    baseline = results[0]
    latest = results[-1]
    
    growth_rate = latest[2] - baseline[2]  # urban_percentage change
    ndvi_change = latest[3] - baseline[3]  # mean_ndvi change
    
    years_elapsed = latest[0] - baseline[0]
    annual_growth = growth_rate / years_elapsed if years_elapsed > 0 else 0
    
    print(f"\n📅 Time Period: {baseline[0]}-{baseline[1]:02d} to {latest[0]}-{latest[1]:02d}")
    print(f"⏱️  Duration: {years_elapsed} years")
    print(f"\n📈 Urban Area Growth:")
    print(f"   Baseline ({baseline[0]}): {baseline[2]:.2f}%")
    print(f"   Latest ({latest[0]}): {latest[2]:.2f}%")
    print(f"   Change: +{growth_rate:.2f} percentage points")
    print(f"   Annual Growth Rate: {annual_growth:.2f}% per year")
    
    print(f"\n🌳 Vegetation Index (NDVI) Change:")
    print(f"   Baseline: {baseline[3]:.3f}")
    print(f"   Latest: {latest[3]:.3f}")
    print(f"   Change: {ndvi_change:.3f} ({'decrease' if ndvi_change < 0 else 'increase'})")
    
    # Store analysis results
    cur.execute("""
        CREATE TABLE IF NOT EXISTS urban_growth_analysis (
            id SERIAL PRIMARY KEY,
            city VARCHAR(100),
            start_year INTEGER,
            end_year INTEGER,
            growth_rate FLOAT,
            annual_growth_rate FLOAT,
            ndvi_change FLOAT,
            analysis_date TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cur.execute("""
        INSERT INTO urban_growth_analysis 
        (city, start_year, end_year, growth_rate, annual_growth_rate, ndvi_change)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (city_name, baseline[0], latest[0], growth_rate, annual_growth, ndvi_change))
    
    conn.commit()
    cur.close()
    conn.close()
    
    # Generate insights
    if annual_growth > 2:
        print(f"\n⚠️  HIGH GROWTH ALERT: {city_name} is experiencing rapid urbanization")
    elif annual_growth > 1:
        print(f"\n📍 MODERATE GROWTH: {city_name} shows steady urban expansion")
    else:
        print(f"\n✅ STABLE: {city_name} shows minimal urban growth")
    
    if ndvi_change < -0.1:
        print(f"🌲 ENVIRONMENTAL IMPACT: Significant vegetation loss detected")
    
    return {
        'city': city_name,
        'growth_rate': growth_rate,
        'annual_growth': annual_growth,
        'ndvi_change': ndvi_change,
        'years': years_elapsed
    }

if __name__ == "__main__":
    analyze_urban_growth("Bangalore")