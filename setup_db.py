import sqlite3
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime

# Configuration
CSV_PATH = "data/data.csv"
DB_PATH = "data/campaigns.db"


def create_database():
    """Load CSV data into SQLite database with proper schema and indexes."""
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    print("=" * 60)
    print("Facebook Ad Campaign Database Setup")
    print("=" * 60)
    
    # Check if CSV exists
    if not Path(CSV_PATH).exists():
        print(f"Error: CSV file not found at {CSV_PATH}")
        print("Please ensure data.csv is in the data/ directory")
        sys.exit(1)
    
    print(f"\n📂 Loading data from {CSV_PATH}...")
    
    try:
        # Read CSV
        df = pd.read_csv(CSV_PATH)
        print(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns")
        
        # Data cleaning and preprocessing
        print("\n🔧 Preprocessing data...")
        
        # Convert date columns to proper format (DD/MM/YYYY → YYYY-MM-DD)
        df['reporting_start'] = pd.to_datetime(
            df['reporting_start'], 
            format='%d/%m/%Y',
            errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        
        df['reporting_end'] = pd.to_datetime(
            df['reporting_end'], 
            format='%d/%m/%Y',
            errors='coerce'
        ).dt.strftime('%Y-%m-%d')
        
        # Handle missing values in conversion columns
        df['total_conversion'] = df['total_conversion'].fillna(0)
        df['approved_conversion'] = df['approved_conversion'].fillna(0)
        
        # Ensure correct data types
        df['impressions'] = df['impressions'].fillna(0).astype(int)
        df['clicks'] = df['clicks'].astype(int)
        df['spent'] = df['spent'].round(2)
        
        print(f"   • Converted date formats")
        print(f"   • Filled {df['total_conversion'].isna().sum()} missing conversion values")
        print(f"   • Cleaned numeric columns")
        
        # Connect to SQLite
        print(f"\n💾 Creating SQLite database at {DB_PATH}...")
        conn = sqlite3.connect(DB_PATH)
        
        # Write to database
        df.to_sql(
            'facebook_ads', 
            conn, 
            if_exists='replace', 
            index=False,
            dtype={
                'ad_id': 'INTEGER PRIMARY KEY',
                'reporting_start': 'TEXT',
                'reporting_end': 'TEXT',
                'campaign_id': 'TEXT',
                'fb_campaign_id': 'TEXT',
                'age': 'TEXT',
                'gender': 'TEXT',
                'interest1': 'INTEGER',
                'interest2': 'INTEGER',
                'interest3': 'INTEGER',
                'impressions': 'INTEGER',
                'clicks': 'INTEGER',
                'spent': 'REAL',
                'total_conversion': 'REAL',
                'approved_conversion': 'REAL'
            }
        )
        
        # Create indexes for better query performance
        print("\n📊 Creating indexes for optimized queries...")
        cursor = conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_reporting_start ON facebook_ads(reporting_start)",
            "CREATE INDEX IF NOT EXISTS idx_campaign_id ON facebook_ads(campaign_id)",
            "CREATE INDEX IF NOT EXISTS idx_age_gender ON facebook_ads(age, gender)",
            "CREATE INDEX IF NOT EXISTS idx_spent ON facebook_ads(spent)",
            "CREATE INDEX IF NOT EXISTS idx_conversions ON facebook_ads(total_conversion)"
        ]
        
        for idx_query in indexes:
            cursor.execute(idx_query)
            index_name = idx_query.split("INDEX IF NOT EXISTS ")[1].split(" ON")[0]
            print(f"   • Created index: {index_name}")
        
        conn.commit()
        
        # Verify data
        print("\n✅ Verifying database...")
        cursor.execute("SELECT COUNT(*) FROM facebook_ads")
        count = cursor.fetchone()[0]
        print(f"   • Total records in database: {count}")
        
        cursor.execute("SELECT MIN(reporting_start), MAX(reporting_end) FROM facebook_ads")
        date_range = cursor.fetchone()
        print(f"   • Date range: {date_range[0]} to {date_range[1]}")
        
        cursor.execute("SELECT COUNT(DISTINCT age) as age_groups, COUNT(DISTINCT gender) as genders FROM facebook_ads")
        demographics = cursor.fetchone()
        print(f"   • Demographics: {demographics[0]} age groups, {demographics[1]} genders")
        
        cursor.execute("SELECT SUM(spent), SUM(clicks), SUM(total_conversion) FROM facebook_ads")
        totals = cursor.fetchone()
        print(f"   • Total spent: ${totals[0]:,.2f}")
        print(f"   • Total clicks: {totals[1]:,}")
        print(f"   • Total conversions: {int(totals[2]):,}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Database setup completed successfully!")
        print("=" * 60)
        print(f"\nYou can now run: chainlit run app.py")
        
    except Exception as e:
        print(f"\n❌ Error during database setup: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    create_database()
