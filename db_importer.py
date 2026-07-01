import csv
import sqlite3
import os

def import_csv_to_sqlite():
    csv_path = 'cardekho_dataset.csv'
    db_path = 'cardekho_cars.db'
    
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return False
        
    print("Reading CSV dataset with built-in csv module...")
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        
        # Clean header spacing
        cleaned_headers = [h.strip() for h in headers]
        
        # Detect if first column is an index (empty name or starts with Unnamed)
        has_index_col = (cleaned_headers[0] == '') or (cleaned_headers[0].startswith('Unnamed'))
        start_idx = 1 if has_index_col else 0
        
        # Drop table if exists to replace it, then create table with explicit column types
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS cars (
            car_name TEXT,
            brand TEXT,
            model TEXT,
            vehicle_age INTEGER,
            km_driven INTEGER,
            seller_type TEXT,
            fuel_type TEXT,
            transmission_type TEXT,
            mileage REAL,
            engine INTEGER,
            max_power REAL,
            seats INTEGER,
            selling_price INTEGER
        );
        """
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DROP TABLE IF EXISTS cars;")
        cursor.execute(create_table_sql)
        
        insert_sql = """
        INSERT INTO cars (
            car_name, brand, model, vehicle_age, km_driven, seller_type, 
            fuel_type, transmission_type, mileage, engine, max_power, seats, selling_price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        rows_to_insert = []
        for row in reader:
            if not row:
                continue
                
            # Slice row data past the index column
            data = row[start_idx:]
            
            # Pad or truncate row to ensure exactly 13 values
            if len(data) < 13:
                data = data + [None] * (13 - len(data))
            else:
                data = data[:13]
                
            # Cast datatypes carefully
            car_name = str(data[0]) if data[0] not in (None, '') else None
            brand = str(data[1]) if data[1] not in (None, '') else None
            model = str(data[2]) if data[2] not in (None, '') else None
            
            try:
                vehicle_age = int(data[3]) if data[3] not in (None, '', 'null') else None
            except ValueError:
                vehicle_age = None
                
            try:
                km_driven = int(data[4]) if data[4] not in (None, '', 'null') else None
            except ValueError:
                km_driven = None
                
            seller_type = str(data[5]) if data[5] not in (None, '') else None
            fuel_type = str(data[6]) if data[6] not in (None, '') else None
            transmission_type = str(data[7]) if data[7] not in (None, '') else None
            
            try:
                mileage = float(data[8]) if data[8] not in (None, '', 'null') else None
            except ValueError:
                mileage = None
                
            try:
                engine = int(data[9]) if data[9] not in (None, '', 'null') else None
            except ValueError:
                engine = None
                
            try:
                max_power = float(data[10]) if data[10] not in (None, '', 'null') else None
            except ValueError:
                max_power = None
                
            try:
                seats = int(data[11]) if data[11] not in (None, '', 'null') else None
            except ValueError:
                seats = None
                
            try:
                selling_price = int(data[12]) if data[12] not in (None, '', 'null') else None
            except ValueError:
                selling_price = None
                
            rows_to_insert.append((
                car_name, brand, model, vehicle_age, km_driven, seller_type,
                fuel_type, transmission_type, mileage, engine, max_power, seats, selling_price
            ))
            
        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()
        print(f"Database successfully built with {len(rows_to_insert)} records!")
        
        # Create database indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand ON cars(brand);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price ON cars(selling_price);")
        conn.commit()
        conn.close()
        
    return True

if __name__ == '__main__':
    import_csv_to_sqlite()
