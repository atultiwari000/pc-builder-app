import psycopg2
from psycopg2.extras import RealDictCursor
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.db import connection

def get_db_connection():
    """
    Establish and return a new PostgreSQL database connection using Django settings.
    
    Returns:
        connection: A new psycopg2 connection object to the configured PostgreSQL database.
    """
    return psycopg2.connect(
        host=settings.DATABASES['default']['HOST'],
        database=settings.DATABASES['default']['NAME'],
        user=settings.DATABASES['default']['USER'],
        password=settings.DATABASES['default']['PASSWORD'],
        port=settings.DATABASES['default']['PORT']
    )

@api_view(['GET'])
def get_vendors(request):
    """
    Retrieve a list of all vendors from the database, ordered by name.
    
    Returns:
        Response: A JSON array of vendor objects, each containing 'id' and 'name'. Returns an error response with HTTP 500 status if a database error occurs.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, name
                FROM vendors
                ORDER BY name
            """)
            columns = [col[0] for col in cursor.description]
            vendors = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return Response(vendors)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_cpus(request):
    """
    Retrieve a list of CPUs with optional filtering by socket type, price range, and vendor.
    
    Accepts query parameters for `socket_type`, `min_price`, `max_price`, and `vendor_id` to filter results. Returns a JSON array of CPU records, each including all CPU fields and the associated vendor name. On error, returns a JSON error message with HTTP 500 status.
    """
    try:
        socket_type = request.GET.get('socket_type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        query = """
            SELECT c.*, v.name as vendor_name
            FROM cpus c
            JOIN vendors v ON c.vendor_id = v.id
            WHERE c.is_active = TRUE
        """
        params = []
        if socket_type:
            query += " AND c.socket_type = %s"
            params.append(socket_type)
        if min_price:
            query += " AND c.price >= %s"
            params.append(float(min_price))
        if max_price:
            query += " AND c.price <= %s"
            params.append(float(max_price))
        if vendor_id:
            query += " AND c.vendor_id = %s"
            params.append(int(vendor_id))
        query += " ORDER BY c.price"
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return Response([dict(zip(columns, row)) for row in cursor.fetchall()])
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


