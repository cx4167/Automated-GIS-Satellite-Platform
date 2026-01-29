import matplotlib.pyplot as plt
import psycopg2
import os

def plot_urban_growth(city_name):
    conn = psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="postgis"
    )
    
    cur = conn.cursor()
    cur.execute("""
        SELECT year, urban_percentage 
        FROM urban_growth_metrics
        WHERE city = %s
        ORDER BY year
    """, (city_name,))
    
    data = cur.fetchall()
    years = [row[0] for row in data]
    urban_pct = [row[1] for row in data]
    
    plt.figure(figsize=(10, 6))
    plt.plot(years, urban_pct, marker='o', linewidth=2, markersize=8)
    plt.title(f'Urban Growth in {city_name}', fontsize=16, fontweight='bold')
    plt.xlabel('Year', fontsize=12)
    plt.ylabel('Urban Area (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'/tmp/{city_name}_growth.png', dpi=300)
    print(f"📊 Chart saved: /tmp/{city_name}_growth.png")
    
    cur.close()
    conn.close()