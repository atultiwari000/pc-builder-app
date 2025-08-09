import psycopg2
from psycopg2.extras import RealDictCursor
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from django.db import connection

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.DATABASES['default']['HOST'],
        database=settings.DATABASES['default']['NAME'],
        user=settings.DATABASES['default']['USER'],
        password=settings.DATABASES['default']['PASSWORD'],
        port=settings.DATABASES['default']['PORT']
    )

# ========================================
# VENDOR ENDPOINTS
# ========================================

@api_view(['GET'])
def get_vendors(request):
    """
    Retrieve a list of all vendors ordered by name.
    
    Returns:
        Response: A JSON response containing a list of vendors with their IDs and names, or an error message with HTTP 500 status on failure.
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

# ========================================
# OPTIONS WITH COMPATIBILITY
# ========================================

@api_view(['GET'])
def get_options_with_compatibility(request):
    """Return options for a target type annotated with compatibility against selected parts.
    Query params:
      - type: one of cpu, motherboard, ram, gpu, storage, psu, case, cooler
      - selected_*_id: ids of currently selected parts (e.g., selected_cpu_id=1)
    """
    try:
        target_type = request.GET.get('type')
        if target_type not in ['cpu', 'motherboard', 'ram', 'gpu', 'storage', 'psu', 'case', 'cooler']:
            return Response({'error': 'Invalid or missing type'}, status=status.HTTP_400_BAD_REQUEST)

        # Read selected ids
        sel = {
            'cpu': request.GET.get('selected_cpu_id'),
            'motherboard': request.GET.get('selected_motherboard_id'),
            'ram': request.GET.get('selected_ram_id'),
            'gpu': request.GET.get('selected_gpu_id'),
            'storage': request.GET.get('selected_storage_id'),
            'psu': request.GET.get('selected_psu_id'),
            'case': request.GET.get('selected_case_id'),
            'cooler': request.GET.get('selected_cooler_id'),
        }
        # Cast to ints or None
        for k, v in list(sel.items()):
            sel[k] = int(v) if v and v.isdigit() else None

        # Fetch selected part specs
        selected_specs = {}
        with connection.cursor() as cursor:
            if sel['cpu']:
                cursor.execute("SELECT id, socket_type, tdp FROM cpus WHERE id=%s", [sel['cpu']])
                row = cursor.fetchone()
                if row:
                    selected_specs['cpu'] = {'id': row[0], 'socket_type': row[1], 'tdp': row[2]}
            if sel['motherboard']:
                cursor.execute("SELECT id, socket_type, form_factor, ram_type, ram_slots, max_ram_speed, sata_ports, m2_slots, m2_pcie_slots FROM motherboards WHERE id=%s", [sel['motherboard']])
                row = cursor.fetchone()
                if row:
                    selected_specs['motherboard'] = {
                        'id': row[0], 'socket_type': row[1], 'form_factor': row[2], 'ram_type': row[3],
                        'ram_slots': row[4], 'max_ram_speed': row[5], 'sata_ports': row[6],
                        'm2_slots': row[7], 'm2_pcie_slots': row[8]
                    }
            if sel['ram']:
                cursor.execute("SELECT id, ram_type, speed, modules_in_kit FROM ram_modules WHERE id=%s", [sel['ram']])
                row = cursor.fetchone()
                if row:
                    selected_specs['ram'] = {'id': row[0], 'ram_type': row[1], 'speed': row[2], 'modules_in_kit': row[3]}
            if sel['gpu']:
                cursor.execute("SELECT id, length_mm, tdp, recommended_psu_watts FROM gpus WHERE id=%s", [sel['gpu']])
                row = cursor.fetchone()
                if row:
                    selected_specs['gpu'] = {'id': row[0], 'length_mm': row[1], 'tdp': row[2], 'recommended_psu_watts': row[3]}
            if sel['storage']:
                cursor.execute("SELECT id, interface, form_factor FROM storage_devices WHERE id=%s", [sel['storage']])
                row = cursor.fetchone()
                if row:
                    selected_specs['storage'] = {'id': row[0], 'interface': row[1], 'form_factor': row[2]}
            if sel['psu']:
                cursor.execute("SELECT id, wattage FROM power_supplies WHERE id=%s", [sel['psu']])
                row = cursor.fetchone()
                if row:
                    selected_specs['psu'] = {'id': row[0], 'wattage': row[1]}
            if sel['case']:
                cursor.execute("SELECT id, max_gpu_length_mm, max_cooler_height_mm, motherboard_form_factors FROM cases WHERE id=%s", [sel['case']])
                row = cursor.fetchone()
                if row:
                    selected_specs['case'] = {'id': row[0], 'max_gpu_length_mm': row[1], 'max_cooler_height_mm': row[2], 'motherboard_form_factors': row[3]}
            if sel['cooler']:
                cursor.execute("SELECT id, height_mm, socket_support FROM cpu_coolers WHERE id=%s", [sel['cooler']])
                row = cursor.fetchone()
                if row:
                    selected_specs['cooler'] = {'id': row[0], 'height_mm': row[1], 'socket_support': row[2]}

            # Fetch all candidates for target_type
            table = {
                'cpu': 'cpus', 'motherboard': 'motherboards', 'ram': 'ram_modules', 'gpu': 'gpus',
                'storage': 'storage_devices', 'psu': 'power_supplies', 'case': 'cases', 'cooler': 'cpu_coolers'
            }[target_type]

            cursor.execute(f"SELECT * FROM {table} WHERE is_active = TRUE")
            columns = [col[0] for col in cursor.description]
            candidates = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Compute compatibility per target type
        def compat_true():
            return True

        annotated = []
        for item in candidates:
            compatible = True
            # cpu needs to match selected motherboard socket if present
            if target_type == 'cpu' and selected_specs.get('motherboard'):
                compatible = (item.get('socket_type') == selected_specs['motherboard']['socket_type'])
            # motherboard must satisfy selected cpu socket, case form_factor, ram type/slots/speed
            elif target_type == 'motherboard':
                if selected_specs.get('cpu'):
                    compatible = compatible and (item.get('socket_type') == selected_specs['cpu']['socket_type'])
                if compatible and selected_specs.get('case'):
                    forms = selected_specs['case']['motherboard_form_factors'] or []
                    compatible = compatible and (item.get('form_factor') in forms)
                if compatible and selected_specs.get('ram'):
                    compatible = compatible and (item.get('ram_type') == selected_specs['ram']['ram_type'])
                    if compatible and item.get('ram_slots') is not None and selected_specs['ram'].get('modules_in_kit') is not None:
                        compatible = compatible and (selected_specs['ram']['modules_in_kit'] <= item['ram_slots'])
                    if compatible and item.get('max_ram_speed') is not None and selected_specs['ram'].get('speed') is not None:
                        compatible = compatible and (selected_specs['ram']['speed'] <= item['max_ram_speed'])
            # ram must match selected motherboard
            elif target_type == 'ram' and selected_specs.get('motherboard'):
                m = selected_specs['motherboard']
                compatible = (item.get('ram_type') == m['ram_type'])
                if compatible and m.get('ram_slots') is not None and item.get('modules_in_kit') is not None:
                    compatible = compatible and (item['modules_in_kit'] <= m['ram_slots'])
                if compatible and m.get('max_ram_speed') is not None and item.get('speed') is not None:
                    compatible = compatible and (item['speed'] <= m['max_ram_speed'])
            # gpu vs case (length) and psu (wattage) with optional cpu tdp
            elif target_type == 'gpu':
                if selected_specs.get('case'):
                    compatible = compatible and (item.get('length_mm') is None or item['length_mm'] <= selected_specs['case']['max_gpu_length_mm'])
                if compatible and selected_specs.get('psu'):
                    cpu_tdp = selected_specs.get('cpu', {}).get('tdp', 0) or 0
                    gpu_tdp = item.get('tdp') or 0
                    required = max((cpu_tdp + gpu_tdp + 100), item.get('recommended_psu_watts') or 0)
                    compatible = compatible and (selected_specs['psu']['wattage'] >= required)
            # storage vs motherboard interface/slots
            elif target_type == 'storage' and selected_specs.get('motherboard'):
                m = selected_specs['motherboard']
                iface = item.get('interface')
                form = item.get('form_factor')
                if iface == 'SATA':
                    compatible = (m.get('sata_ports', 0) > 0)
                elif iface == 'PCIe' and form == 'M.2':
                    compatible = (m.get('m2_pcie_slots', 0) > 0) or (m.get('m2_slots', 0) > 0)
                else:
                    compatible = True
            # psu vs cpu/gpu required wattage
            elif target_type == 'psu' and (selected_specs.get('cpu') or selected_specs.get('gpu')):
                cpu_tdp = selected_specs.get('cpu', {}).get('tdp', 0) or 0
                gpu_tdp = selected_specs.get('gpu', {}).get('tdp', 0) or 0
                gpu_rec = selected_specs.get('gpu', {}).get('recommended_psu_watts', 0) or 0
                required = max((cpu_tdp + gpu_tdp + 100), gpu_rec)
                compatible = (item.get('wattage', 0) >= required)
            # case vs motherboard form factor, gpu length, cooler height
            elif target_type == 'case':
                if selected_specs.get('motherboard'):
                    forms = item.get('motherboard_form_factors') or []
                    compatible = compatible and (selected_specs['motherboard']['form_factor'] in forms)
                if compatible and selected_specs.get('gpu') and item.get('max_gpu_length_mm'):
                    compatible = compatible and (selected_specs['gpu']['length_mm'] <= item['max_gpu_length_mm'])
                if compatible and selected_specs.get('cooler') and item.get('max_cooler_height_mm'):
                    compatible = compatible and (selected_specs['cooler']['height_mm'] <= item['max_cooler_height_mm'])
            # cooler vs case height and cpu socket
            elif target_type == 'cooler':
                if selected_specs.get('case') and item.get('height_mm') and selected_specs['case'].get('max_cooler_height_mm'):
                    compatible = compatible and (item['height_mm'] <= selected_specs['case']['max_cooler_height_mm'])
                if compatible and selected_specs.get('cpu'):
                    sockets = item.get('socket_support') or []
                    compatible = compatible and (selected_specs['cpu']['socket_type'] in sockets)
            # default: if no related selection, keep as compatible

            item_out = {
                'id': item.get('id'),
                'name': item.get('name'),
                'model': item.get('model'),
                'price': float(item.get('price') or 0),
                'compatible': bool(compatible),
            }
            annotated.append(item_out)

        return Response(annotated)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# CPU ENDPOINTS
# ========================================

@api_view(['GET'])
def get_cpus(request):
    """
    Retrieve all active CPUs with optional filtering by socket type, price range, and vendor.
    
    Parameters:
    	socket_type (str, optional): Filter CPUs by socket type.
    	min_price (float, optional): Minimum price to include.
    	max_price (float, optional): Maximum price to include.
    	vendor_id (int, optional): Filter CPUs by vendor ID.
    
    Returns:
    	Response: A JSON response containing a list of CPUs with vendor names, ordered by price.
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
            cpus = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(cpus)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_cpu_by_id(request, cpu_id):
    """Get specific CPU by ID"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.*, v.name as vendor_name
                FROM cpus c
                JOIN vendors v ON c.vendor_id = v.id
                WHERE c.id = %s AND c.is_active = TRUE
            """, [cpu_id])
            
            columns = [col[0] for col in cursor.description]
            cpu = dict(zip(columns, cursor.fetchone())) if cursor.fetchone() else None

        if not cpu:
            return Response({'error': 'CPU not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(cpu)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# MOTHERBOARD ENDPOINTS
# ========================================

@api_view(['GET'])
def get_motherboards(request):
    """
    Retrieve all active motherboards with optional filters for socket type, form factor, RAM type, price range, and vendor.
    
    Returns:
        Response: A list of motherboards with vendor names, ordered by price. Returns an error response with HTTP 500 status on failure.
    """
    try:
        socket_type = request.GET.get('socket_type')
        form_factor = request.GET.get('form_factor')
        ram_type = request.GET.get('ram_type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        
        query = """
            SELECT m.*, v.name as vendor_name
            FROM motherboards m
            JOIN vendors v ON m.vendor_id = v.id
            WHERE m.is_active = TRUE
        """
        params = []
        
        if socket_type:
            query += " AND m.socket_type = %s"
            params.append(socket_type)
        
        if form_factor:
            query += " AND m.form_factor = %s"
            params.append(form_factor)
        
        if ram_type:
            query += " AND m.ram_type = %s"
            params.append(ram_type)
        
        if min_price:
            query += " AND m.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND m.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND m.vendor_id = %s"
            params.append(int(vendor_id))
        
        query += " ORDER BY m.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            motherboards = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(motherboards)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# RAM ENDPOINTS
# ========================================

@api_view(['GET'])
def get_ram_modules(request):
    """
    Retrieve all active RAM modules with optional filtering by RAM type, speed, price, and vendor.
    
    Accepts query parameters for `ram_type`, `min_speed`, `max_speed`, `min_price`, `max_price`, and `vendor_id` to filter results. Returns a list of RAM modules joined with vendor names, ordered by price.
    """
    try:
        ram_type = request.GET.get('ram_type')
        capacity = request.GET.get('capacity')
        min_speed = request.GET.get('min_speed')
        max_speed = request.GET.get('max_speed')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        
        query = """
            SELECT r.*, v.name as vendor_name
            FROM ram_modules r
            JOIN vendors v ON r.vendor_id = v.id
            WHERE r.is_active = TRUE
        """
        params = []
        
        if ram_type:
            query += " AND r.ram_type = %s"
            params.append(ram_type)
        
        # capacity removed in lean schema
        
        if min_speed:
            query += " AND r.speed >= %s"
            params.append(int(min_speed))
        
        if max_speed:
            query += " AND r.speed <= %s"
            params.append(int(max_speed))
        
        if min_price:
            query += " AND r.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND r.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND r.vendor_id = %s"
            params.append(int(vendor_id))
        
        query += " ORDER BY r.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            ram_modules = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(ram_modules)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# GPU ENDPOINTS
# ========================================

@api_view(['GET'])
def get_gpus(request):
    """
    Retrieve all active GPUs with optional filtering by price and vendor.
    
    Accepts optional query parameters for minimum and maximum price, and vendor ID. Returns a list of GPUs joined with vendor name, ordered by price.
    """
    try:
        min_memory = request.GET.get('min_memory')
        max_memory = request.GET.get('max_memory')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        ray_tracing = request.GET.get('ray_tracing')
        
        query = """
            SELECT g.*, v.name as vendor_name
            FROM gpus g
            JOIN vendors v ON g.vendor_id = v.id
            WHERE g.is_active = TRUE
        """
        params = []
        
        # memory_size removed in lean schema
        
        if min_price:
            query += " AND g.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND g.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND g.vendor_id = %s"
            params.append(int(vendor_id))
        
        # ray_tracing removed in lean schema
        
        query += " ORDER BY g.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            gpus = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(gpus)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# STORAGE ENDPOINTS
# ========================================

@api_view(['GET'])
def get_storage_devices(request):
    """
    Retrieve all active storage devices with optional filters for type, interface, price range, and vendor.
    
    Parameters:
        request: The HTTP request containing optional query parameters for filtering:
            - storage_type: Filter by storage device type.
            - interface: Filter by storage interface.
            - min_price: Minimum price filter.
            - max_price: Maximum price filter.
            - vendor_id: Filter by vendor ID.
    
    Returns:
        Response: A JSON list of storage devices with vendor names, ordered by price. Returns an error message with HTTP 500 status on failure.
    """
    try:
        storage_type = request.GET.get('storage_type')
        interface = request.GET.get('interface')
        min_capacity = request.GET.get('min_capacity')
        max_capacity = request.GET.get('max_capacity')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        
        query = """
            SELECT s.*, v.name as vendor_name
            FROM storage_devices s
            JOIN vendors v ON s.vendor_id = v.id
            WHERE s.is_active = TRUE
        """
        params = []
        
        if storage_type:
            query += " AND s.storage_type = %s"
            params.append(storage_type)
        
        if interface:
            query += " AND s.interface = %s"
            params.append(interface)
        
        # capacity removed in lean schema
        
        if min_price:
            query += " AND s.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND s.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND s.vendor_id = %s"
            params.append(int(vendor_id))
        
        query += " ORDER BY s.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            storage_devices = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(storage_devices)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# POWER SUPPLY ENDPOINTS
# ========================================

@api_view(['GET'])
def get_power_supplies(request):
    """
    Retrieve all active power supplies with optional filtering by wattage, price, and vendor.
    
    Filters can be applied using query parameters: `min_wattage`, `max_wattage`, `min_price`, `max_price`, and `vendor_id`. Results are ordered by wattage descending and then by price.
    
    Returns:
        Response: A JSON list of power supplies with vendor names, or an error message with HTTP 500 status on failure.
    """
    try:
        min_wattage = request.GET.get('min_wattage')
        max_wattage = request.GET.get('max_wattage')
        efficiency_rating = request.GET.get('efficiency_rating')
        modular_type = request.GET.get('modular_type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        
        query = """
            SELECT p.*, v.name as vendor_name
            FROM power_supplies p
            JOIN vendors v ON p.vendor_id = v.id
            WHERE p.is_active = TRUE
        """
        params = []
        
        if min_wattage:
            query += " AND p.wattage >= %s"
            params.append(int(min_wattage))
        
        if max_wattage:
            query += " AND p.wattage <= %s"
            params.append(int(max_wattage))
        
        # efficiency_rating, modular_type removed in lean schema
        
        if min_price:
            query += " AND p.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND p.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND p.vendor_id = %s"
            params.append(int(vendor_id))
        
        query += " ORDER BY p.wattage DESC, p.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            power_supplies = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(power_supplies)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# CASE ENDPOINTS
# ========================================

@api_view(['GET'])
def get_cases(request):
    """
    Retrieve all active PC cases with optional filters for form factor, GPU length, price range, vendor, and side panel type.
    
    Returns:
        Response: A list of case objects with vendor names, filtered and ordered by price.
    """
    try:
        form_factor = request.GET.get('form_factor')
        min_gpu_length = request.GET.get('min_gpu_length')
        max_gpu_length = request.GET.get('max_gpu_length')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        side_panel_type = request.GET.get('side_panel_type')
        
        query = """
            SELECT c.*, v.name as vendor_name
            FROM cases c
            JOIN vendors v ON c.vendor_id = v.id
            WHERE c.is_active = TRUE
        """
        params = []
        
        if form_factor:
            query += " AND %s = ANY(c.motherboard_form_factors)"
            params.append(form_factor)
        
        if min_gpu_length:
            query += " AND c.max_gpu_length_mm >= %s"
            params.append(int(min_gpu_length))
        
        if max_gpu_length:
            query += " AND c.max_gpu_length_mm <= %s"
            params.append(int(max_gpu_length))
        
        if min_price:
            query += " AND c.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND c.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND c.vendor_id = %s"
            params.append(int(vendor_id))
        
        if side_panel_type:
            query += " AND c.side_panel_type = %s"
            params.append(side_panel_type)
        
        query += " ORDER BY c.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            cases = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(cases)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# CPU COOLER ENDPOINTS
# ========================================

@api_view(['GET'])
def get_cpu_coolers(request):
    """
    Retrieve all active CPU coolers with optional filtering by socket type, price range, and vendor.
    
    Filters:
        - socket_type: Only include coolers supporting the specified CPU socket.
        - min_price, max_price: Restrict results to coolers within the given price range.
        - vendor_id: Only include coolers from the specified vendor.
    
    Returns:
        JSON response containing a list of CPU coolers with vendor names.
    """
    try:
        cooler_type = request.GET.get('cooler_type')
        socket_type = request.GET.get('socket_type')
        min_tdp = request.GET.get('min_tdp')
        max_tdp = request.GET.get('max_tdp')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        vendor_id = request.GET.get('vendor_id')
        
        query = """
            SELECT cc.*, v.name as vendor_name
            FROM cpu_coolers cc
            JOIN vendors v ON cc.vendor_id = v.id
            WHERE cc.is_active = TRUE
        """
        params = []
        
        # cooler_type removed in lean schema
        
        if socket_type:
            query += " AND %s = ANY(cc.socket_support)"
            params.append(socket_type)
        
        # tdp_rating removed in lean schema
        
        if min_price:
            query += " AND cc.price >= %s"
            params.append(float(min_price))
        
        if max_price:
            query += " AND cc.price <= %s"
            params.append(float(max_price))
        
        if vendor_id:
            query += " AND cc.vendor_id = %s"
            params.append(int(vendor_id))
        
        query += " ORDER BY cc.price"
        
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            cpu_coolers = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(cpu_coolers)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# BUILD MANAGEMENT
# ========================================

@api_view(['POST'])
def create_build(request):
    """Create a new build"""
    try:
        user_id = request.data.get('user_id')
        name = request.data.get('name')
        description = request.data.get('description', '')
        parts = request.data.get('parts', [])  # List of {part_type, part_id, quantity}
        
        if not user_id or not name:
            return Response({'error': 'user_id and name are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        with connection.cursor() as cursor:
            # Create build
            cursor.execute("""
                INSERT INTO builds (user_id, name, description)
                VALUES (%s, %s, %s)
                RETURNING id
            """, [user_id, name, description])
            
            build_id = cursor.fetchone()[0]
            
            # Add parts to build
            for part in parts:
                cursor.execute("""
                    INSERT INTO build_parts (build_id, part_type, part_id, quantity)
                    VALUES (%s, %s, %s, %s)
                """, [build_id, part['part_type'], part['part_id'], part.get('quantity', 1)])
            
            connection.commit()
            
            return Response({'build_id': build_id, 'message': 'Build created successfully'}, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        connection.rollback()
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_user_builds(request, user_id):
    """Get all builds for a user"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT b.*, 
                       COUNT(bp.id) as part_count,
                       b.total_price
                FROM builds b
                LEFT JOIN build_parts bp ON b.id = bp.build_id
                WHERE b.user_id = %s
                GROUP BY b.id
                ORDER BY b.created_at DESC
            """, [user_id])
            
            columns = [col[0] for col in cursor.description]
            builds = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(builds)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_build_details(request, build_id):
    """Get detailed build information with parts and compatibility"""
    try:
        with connection.cursor() as cursor:
            # Get build info
            cursor.execute("""
                SELECT b.*, u.username as user_name
                FROM builds b
                JOIN users u ON b.user_id = u.id
                WHERE b.id = %s
            """, [build_id])
            
            build_columns = [col[0] for col in cursor.description]
            build = dict(zip(build_columns, cursor.fetchone())) if cursor.fetchone() else None
            
            if not build:
                return Response({'error': 'Build not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Get build parts with component details
            cursor.execute("""
                SELECT bp.*, 
                       CASE 
                           WHEN bp.part_type = 'cpu' THEN c.name
                           WHEN bp.part_type = 'motherboard' THEN m.name
                           WHEN bp.part_type = 'ram' THEN r.name
                           WHEN bp.part_type = 'gpu' THEN g.name
                           WHEN bp.part_type = 'storage' THEN s.name
                           WHEN bp.part_type = 'psu' THEN p.name
                           WHEN bp.part_type = 'case' THEN cs.name
                           WHEN bp.part_type = 'cooler' THEN cc.name
                       END as component_name,
                       CASE 
                           WHEN bp.part_type = 'cpu' THEN c.price
                           WHEN bp.part_type = 'motherboard' THEN m.price
                           WHEN bp.part_type = 'ram' THEN r.price
                           WHEN bp.part_type = 'gpu' THEN g.price
                           WHEN bp.part_type = 'storage' THEN s.price
                           WHEN bp.part_type = 'psu' THEN p.price
                           WHEN bp.part_type = 'case' THEN cs.price
                           WHEN bp.part_type = 'cooler' THEN cc.price
                       END as component_price
                FROM build_parts bp
                LEFT JOIN cpus c ON bp.part_type = 'cpu' AND bp.part_id = c.id
                LEFT JOIN motherboards m ON bp.part_type = 'motherboard' AND bp.part_id = m.id
                LEFT JOIN ram_modules r ON bp.part_type = 'ram' AND bp.part_id = r.id
                LEFT JOIN gpus g ON bp.part_type = 'gpu' AND bp.part_id = g.id
                LEFT JOIN storage_devices s ON bp.part_type = 'storage' AND bp.part_id = s.id
                LEFT JOIN power_supplies p ON bp.part_type = 'psu' AND bp.part_id = p.id
                LEFT JOIN cases cs ON bp.part_type = 'case' AND bp.part_id = cs.id
                LEFT JOIN cpu_coolers cc ON bp.part_type = 'cooler' AND bp.part_id = cc.id
                WHERE bp.build_id = %s
                ORDER BY bp.part_type
            """, [build_id])
            
            parts_columns = [col[0] for col in cursor.description]
            parts = [dict(zip(parts_columns, row)) for row in cursor.fetchall()]
            
            # Check compatibility
            cursor.execute("SELECT check_build_compatibility(%s)", [build_id])
            compatibility_result = cursor.fetchone()[0]
            
            build['parts'] = parts
            build['compatibility'] = compatibility_result

        return Response(build)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# COMPATIBILITY ENDPOINTS
# ========================================

@api_view(['GET'])
def check_compatibility(request):
    """Check compatibility between specific components"""
    try:
        cpu_id = request.GET.get('cpu_id')
        motherboard_id = request.GET.get('motherboard_id')
        ram_id = request.GET.get('ram_id')
        gpu_id = request.GET.get('gpu_id')
        case_id = request.GET.get('case_id')
        psu_id = request.GET.get('psu_id')
        storage_id = request.GET.get('storage_id')
        cooler_id = request.GET.get('cooler_id')
        
        results = {}
        
        with connection.cursor() as cursor:
            if cpu_id and motherboard_id:
                cursor.execute("SELECT check_cpu_motherboard_compatibility(%s, %s)", [cpu_id, motherboard_id])
                results['cpu_motherboard'] = cursor.fetchone()[0]
            
            if motherboard_id and ram_id:
                cursor.execute("SELECT check_motherboard_ram_compatibility(%s, %s)", [motherboard_id, ram_id])
                results['motherboard_ram'] = cursor.fetchone()[0]
            
            if gpu_id and case_id:
                cursor.execute("SELECT check_gpu_case_compatibility(%s, %s)", [gpu_id, case_id])
                results['gpu_case'] = cursor.fetchone()[0]
            
            if case_id and motherboard_id:
                cursor.execute("SELECT check_case_motherboard_compatibility(%s, %s)", [case_id, motherboard_id])
                results['case_motherboard'] = cursor.fetchone()[0]
            
            if psu_id and (cpu_id or gpu_id):
                cursor.execute("SELECT check_psu_wattage_compatibility(%s, %s, %s)", [psu_id, cpu_id, gpu_id])
                results['psu_wattage'] = cursor.fetchone()[0]
            
            if storage_id and motherboard_id:
                cursor.execute("SELECT check_storage_motherboard_compatibility(%s, %s)", [storage_id, motherboard_id])
                results['storage_motherboard'] = cursor.fetchone()[0]
            
            if cooler_id and case_id:
                cursor.execute("SELECT check_cooler_case_compatibility(%s, %s)", [cooler_id, case_id])
                results['cooler_case'] = cursor.fetchone()[0]
            
            if cooler_id and cpu_id:
                cursor.execute("SELECT check_cooler_cpu_compatibility(%s, %s)", [cooler_id, cpu_id])
                results['cooler_cpu'] = cursor.fetchone()[0]

        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ========================================
# SEARCH ENDPOINTS
# ========================================

@api_view(['GET'])
def search_components(request):
    """
    Searches for components by name or model across CPUs, motherboards, and GPUs.
    
    Parameters:
        request: The HTTP request containing the search query string `q` and optional `type` parameter to filter by component type.
    
    Returns:
        Response: A JSON object with up to 10 matching results per component type, including basic details for each component. Returns HTTP 400 if the query is missing, or HTTP 500 on error.
    """
    try:
        query = request.GET.get('q', '')
        component_type = request.GET.get('type', 'all')  # all, cpu, motherboard, etc.
        
        if not query:
            return Response({'error': 'Search query is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        search_term = f"%{query}%"
        results = {}
        
        with connection.cursor() as cursor:
            if component_type in ['all', 'cpu']:
                cursor.execute("""
                    SELECT 'cpu' as type, id, name, model, price, socket_type
                    FROM cpus 
                    WHERE (name ILIKE %s OR model ILIKE %s) AND is_active = TRUE
                    ORDER BY price
                    LIMIT 10
                """, [search_term, search_term])
                results['cpus'] = [dict(zip(['type', 'id', 'name', 'model', 'price', 'socket_type'], row)) 
                                   for row in cursor.fetchall()]
            
            if component_type in ['all', 'motherboard']:
                cursor.execute("""
                    SELECT 'motherboard' as type, id, name, model, price, socket_type, form_factor
                    FROM motherboards 
                    WHERE (name ILIKE %s OR model ILIKE %s) AND is_active = TRUE
                    ORDER BY price
                    LIMIT 10
                """, [search_term, search_term])
                results['motherboards'] = [dict(zip(['type', 'id', 'name', 'model', 'price', 'socket_type', 'form_factor'], row)) 
                                           for row in cursor.fetchall()]
            
            if component_type in ['all', 'gpu']:
                cursor.execute("""
                    SELECT 'gpu' as type, id, name, model, price
                    FROM gpus 
                    WHERE (name ILIKE %s OR model ILIKE %s) AND is_active = TRUE
                    ORDER BY price
                    LIMIT 10
                """, [search_term, search_term])
                results['gpus'] = [dict(zip(['type', 'id', 'name', 'model', 'price'], row)) 
                                   for row in cursor.fetchall()]

        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
