import psycopg2

try:
    conn = psycopg2.connect("postgresql://postgres:Everest%408848@db.uojlphzskpklpsezamjz.supabase.co:5432/postgres")
    print("Connection successful!")
    conn.close()
except Exception as e:
    print("Connection failed:", e)

